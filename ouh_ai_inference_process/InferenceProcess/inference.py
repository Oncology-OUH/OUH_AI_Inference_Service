import shutil
from collections import Counter
import copy
import datetime
import glob
import hashlib
import logging
import os
import re
import subprocess
import time
import traceback
from dataclasses import asdict
from pathlib import Path
import ast
from dataclasses import replace

import SimpleITK as sitk
import nibabel
import numpy as np
import pydicom
from pydicom import Dataset
from pydicom.uid import UID

from InferenceProcess.configuration import Model, Structure, model_cervix_brachy_mr, model_hn_dahanca_ct, model_prostate_mrl, model_hn_dcpt_ct, model_femalepelvis_mrl
from platipy.dicom.io.rtstruct_to_nifti import read_dicom_image
from rt_utils import RTStructBuilder

from nifti_ouh import File as NiftiFile


class InferenceProcess(object):
    """
    The InferenceProcess class represents the process of inferring medical images with nnU-Net v2.

    The following attributes are existent in the object:
    location (Path): The path to the directory containing the AI configuration file (`aiconfig.txt`) and the input DICOM files.
    log (logging.Logger): A logger instance for logging events during the inference process.
    config (dict): Configuration settings loaded from the `aiconfig.txt` file.
    model (nnUNetModel): An instance of the nnU-Net model configured for inference.
    compare_model_version_hash (function): A function to compare the current model version hash with the expected one.
    dicom_series_path (Path): The path to the directory containing the DICOM series.
    nifti_image_path (Path): The path where the inferred NIfTI image will be saved.
    nifti_mask_inference_tmp_path (Path): Temporary path for storing intermediate NIfTI mask outputs.
    nifti_mask_path (Path): The final path for the NIfTI mask after processing.
    rtstruct_output_path (Path): The path where the processed RTSTRUCT output will be saved.

    TODO: This class only supports nnU-Net v2 inference.
    Extending the functionality to other deep learning approaches might be necessary in the future
    """
    def __init__(self, location: Path):
        """
        Constructs all the necessary attributes for the InferenceProcess object.
        The folder found at the location needs to comply with the following:
        1. It needs to contain a aiconfig.txt file 
        2. It needs to contain (at least) a folder called dcminput. This folder contains all SOP instances from an image scan (e.g. CT, MR, PET, ...)

        :param location: The location of the directory containing the ai configuration file and the input DICOM files.
        :type location: Path
        """
        self.location = location
        self.check_folder_exists(self.location)  # sanity check

        self.log = logging.getLogger('InferenceProcess')
        self.config = self.ai_config_parser(Path(self.location, 'aiconfig.txt'))
        self.model = self.get_model()
        self.compare_model_version_hash()

        self.dicom_series_path = Path(self.location, 'dcminput')
        self.nifti_image_path = Path(self.location, 'niftiimage')
        # necessary because we potentially manipulate the numbers in the niftimask output from nnunet 
        # for re-arranging the dicom RTStruct organ order. 
        self.nifti_mask_inference_tmp_path =  Path(self.location, 'niftimask_tmp')
        self.nifti_mask_path = Path(self.location, 'niftimask') 
        self.rtstruct_output_path = Path(self.location, 'dcmoutput')

    def convert_dcm_to_nifti(self) -> None:
        """Converts a dicom series to nifti.
        Walks through a dicom directory and catches the first Image file to
        translate it and its series into a nifti image.

        :raises TypeError: If the input variables are not of type Path
        :raises OSError: If the input directory does not contain any DICOM files
        :raises TypeError: If the read in dicom image can't be identified by its modality from the lists in check_dicom_file_is_image then an error will be raise
        """
        dicom_files = os.listdir(self.dicom_series_path)
        # check if there even are any dicom files in the given directory
        if not any(".dcm" in file for file in dicom_files):
            raise Dcm2NiiConversionError("E3_02", "Input directory does not contain any DICOM files")

        for file in dicom_files:
            # For every file check if file is an actual dicomfile
            if file.endswith(".dcm"):
                # Load file header but only Modality and SOPClassUID.
                # That reduces load time and is all we need for this.
                with pydicom.dcmread(
                    os.path.join(self.dicom_series_path, file),
                    specific_tags=["Modality", "SOPClassUID", "StudyInstanceUID"],
                ) as ds:
                    if self.check_dicom_file_is_image(ds.SOPClassUID):
                        self.log.info(f"Starting conversion of seriesUID {file}")
                        try:
                            img: sitk.Image = read_dicom_image(self.dicom_series_path)

                            # The trailing zeroes in sitk.WriteImage are necessary
                            # for nnUNet so it knows the modality.
                            # TODO: Test case for multimodality nnUNet inference
                            sitk.WriteImage(
                                img,
                                Path(self.nifti_image_path, f"{ds.StudyInstanceUID}_0000.nii.gz"),
                            )
                        except (Exception, RuntimeError) as e:
                            self.log.error("Dicom to Nifti image conversion failed!")
                            self.log.error(traceback.format_exc())
                            raise Dcm2NiiConversionError("E3_02", "Could not write Dicom file to Nifti")
                        self.log.info(f"Finished Dicom to Nifti image conversion successfully.")
                        break # stop at the first dicom image because the rest is being read by read_dicom_image automatically
                    elif not self.check_dicom_file_is_image(ds.SOPClassUID):
                        continue
                    else:
                        self.log.error(f"Dicom to Nifti image conversion failed.")
                        self.log.error(f"A Dicom file could not be assessed correctly: {Path(self.dicom_series_path, file)}"
                        )
                        raise Dcm2NiiConversionError("E3_01", "Dicom file not found or could not be assessed")
    def run_nnunet_inference(self):
        """Execute a command into the commandline to start the nnunet inference for
        the given input scan with the given model configuration

        :raises TypeError: If input variables are not of the required type
        :raises subprocess.CalledProcessError: If the nnUNetv2_predict command returns a non-zero exit code
        """
        # Define the bash command
        cmd = "nnUNetv2_predict -i {input_folder} -o {output_folder} -d {dataset_id} -p {plan} -tr {trainer} -c {configuration} -chk {checkpoint} -f {folds}"

        config = asdict(self.model)
        # Replace the variables in the command with values from the configuration file
        self.log.info(f'Starting nnU-Net for Inference with the parameters: {self.model.nnunet}')

        cmd = cmd.format(
            input_folder=self.nifti_image_path,
            output_folder=self.nifti_mask_inference_tmp_path,
            dataset_id=config["id"],
            plan=config["nnunet"]["p"],
            trainer=config["nnunet"]["tr"],
            configuration=config["nnunet"]["c"],
            checkpoint=config["nnunet"]["chk"],
            folds=config["nnunet"]["f"],
        )

        # Add --save_probabilities to the command if save_probabilities is True
        if config["nnunet"].get("save_probabilities", False):
            cmd += " --save_probabilities"

        # Run the command
        try:
            start_time = time.time()
            subprocess.run(cmd, shell=True, check=True, text=True, stderr=subprocess.STDOUT)
            elapsed_time = time.time() - start_time
        except subprocess.CalledProcessError as e:
            print("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))
            self.log.error('Error occurred while running nnU-Net')
            self.log.error(traceback.format_exc())
            raise nnUNetError('E3_023', 'nnU-Net inference failed. Please check the inference.log')
        self.log.info(f'nnU-Net completed the inference in {elapsed_time} seconds.')

    def run_nnunet_postprocessing(self):
        """Execute a command into the commandline to start the nnunet postprocessing for
        the given input scan with the given model configuration. If no post-processing configuration is defined
        in the loaded nnunet config then skip this step.

        :raises TypeError: If input variables are not of the required type
        :raises subprocess.CalledProcessError: If the nnUNetv2_predict command returns a non-zero exit code
        """

        # Define the bash command
        cmd = "nnUNetv2_apply_postprocessing -i {input_folder} -o {output_folder} -pp_pkl_file {post_processing_pickle} -plans_json {post_processing_plan}"

        config = asdict(self.model)
        if not config["nnunet"]["post_processing_pickle"] or not config["nnunet"]["post_processing_plan"]:
            self.log.info('No post-processing parameter and information set. Skipping post-processing.')
            nifti_mask = glob.glob(str(self.nifti_mask_inference_tmp_path) + '/*.nii.gz')
            try:
                if len(nifti_mask) > 1:
                    raise OSError("There is more than one nifti mask after nnUNet Inference. Something went wrong.")
                else:
                    self.log.info(nifti_mask)
                    shutil.copy2(Path(nifti_mask[0]), self.nifti_mask_path)
                    return None
            except:
                self.log.error(f'Conversion from Niftimask to RTStruct failed')
                raise Nii2DcmConversionError('E3_19',
                                             f'Nifti mask for forwarding not found at {self.nifti_image_path}.')

        # Replace the variables in the command with values from the configuration file
        self.log.info(f'Starting nnU-Net for PostProcessing with the parameters: {self.model.nnunet}')

        cmd = cmd.format(
            input_folder=self.nifti_mask_inference_tmp_path,
            output_folder=self.nifti_mask_path,
            post_processing_pickle=config["nnunet"]["post_processing_pickle"],
            post_processing_plan=config["nnunet"]["post_processing_plan"]
        )

        # Run the command
        try:
            start_time = time.time()
            subprocess.run(cmd, shell=True, check=True, text=True, stderr=subprocess.STDOUT)
            elapsed_time = time.time() - start_time
        except subprocess.CalledProcessError as e:
            print("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))
            self.log.error('Error occurred while running nnU-Net')
            self.log.error(traceback.format_exc())
            raise nnUNetError('E3_023', 'nnU-Net postprocessing failed. Please check the inference.log')
        self.log.info(f'nnU-Net completed the postprocessing in {elapsed_time} seconds.')

    def convert_nifti_to_rtstruct(
        self):
        """Converts the nifti file given as input path
        into an RTStruct. The conversion is based on a Dicom series
        that is fed into through the dicom_series_path.

        WARNING: We do not check if the dicom_series_path matches
        with the nifti_series ID.

        :raises FileNotFoundError: If the dicom series or nifti file is not found
        :raises OSError: If there are multiple or no nifti masks after nnUNet Inference
        :raises Exception: If the conversion from Niftimask to RTStruct fails
        """
        self.log.info(f'Starting conversion from Niftimask to RTStruct')
        try:
            if not self.dicom_series_path.exists():
                raise FileNotFoundError(f"Dicom series not found at {self.dicom_series_path}")
        except:
            self.log.error(f'Conversion from Niftimask to RTStruct failed')
            raise Nii2DcmConversionError('E3_04', f'Dicom series for conversion not found at {self.dicom_series_path}.')
        try:
            if not self.nifti_image_path.exists():
                raise FileNotFoundError(f"Nifti file not found at {self.nifti_image_path}")
        except:
            self.log.error(f'Conversion from Niftimask to RTStruct failed')
            raise Nii2DcmConversionError('E3_05', f'Nifti mask for conversion not found at {self.nifti_image_path}.')


        nifti_mask = glob.glob(str(self.nifti_mask_path) + '/*.nii.gz')
        try:
            if len(nifti_mask) > 1:
                raise OSError("There is more than one nifti mask after nnUNet Inference. Something went wrong.")
        except:
            self.log.error(f'Conversion from Niftimask to RTStruct failed')
            raise Nii2DcmConversionError('E3_06', f'Multiple nifti masks found at {self.nifti_image_path}')
        try:
            if len(nifti_mask) == 0:
                raise OSError("There is no nifti mask after nnUNet Inference. Something went wrong.")
        except:
            self.log.error(f'Conversion from Niftimask to RTStruct failed')
            raise Nii2DcmConversionError('E3_07', f'No nifti mask found at {self.nifti_image_path}.')
        try:
            nifti_file = NiftiFile(Path(nifti_mask[0]))
            study_id = nifti_file.name

            output_filepath = Path(os.path.join(self.rtstruct_output_path, f"rtstruct_{study_id}.dcm"))

            nifti_file.load_header()
            nifti_file.load_data()

            if any('struct_' in key for key in self.config.keys()):
                self.log.info(f'Found structures to change in aiconfig.txt')
                sorted_index_dict = self.change_default_roi_configuration()
                mapping = {}
                for old_structure_order_keys, old_structure_order_values in asdict(self.model)["structures"].items():
                    self.log.debug(old_structure_order_values)
                    mapping[old_structure_order_values['value']] = int(sorted_index_dict[old_structure_order_keys].value)
                self.log.debug(f"Re-mapping for nifti mask {mapping}")
                #self.log.debug(f"sorted_index_dict values: {new_structure_order['value']}, {new_structure_order['display_name']}, asdict(model) values: {old_structure_order['value']}, {old_structure_order['display_name']}")
                nifti_file.map_values(30, mapping)
                sorted_index_dict = {key: asdict(value) for key, value in sorted_index_dict.items()}
                self.log.debug(sorted_index_dict)
                self.log.debug(asdict(self.model)['structures'])
            else:
                sorted_index_dict = asdict(self.model)["structures"] # no changes to struct defined in config. do nothing
                self.log.debug(sorted_index_dict)
                sorted_index_dict = dict(sorted(sorted_index_dict.items(), key=lambda item: int(item[1]['value'])))
                self.log.debug(sorted_index_dict)




            nifti_file.convert_masks_to_rtstruct(
                sorted_index_dict,
                self.dicom_series_path,
                output_filepath,
                series_description=self.model.description,
            )
            rtstruct_filepath = self.adjust_rtstruct_dicom_information(output_filepath)
            self.merge_structure_with_same_name(rtstruct_filepath)
        except Exception as e:
            self.log.error(f'Conversion from Niftimask to RTStruct failed')
            self.log.error(traceback.format_exc())
            raise Nii2DcmConversionError('E3_08', 'Conversion from Niftimask to RTStruct failed.')
        self.log.info(f'Conversion from Niftimask to RTStruct ran successfully')

    def add_model_description_structure(self):
        """
        This creates a cube structure in the existing
        RTStruct. This structure will contain the model-name, s.t.
        clinicians can easily see what model was used for the inference.
        The structure needs to have a minimum volume as it otherwise might not be displayed by all treatment planning
        systems.
        """
        # emptystructurewithmodelname is lowercase for allowing case insensitivity.
        # TODO test case for emptystructurewithmodelname set/not set in aiconfig.txt
        if self.config.get('emptystructurewithmodelname', [None])[0] == 'false':
            self.log.info("EmptyStructureWithModelName set to false in config. Not adding a structure with the model name to RTStruct.")
        elif self.config.get('emptystructurewithmodelname', ['true'])[0] == 'true':
            self.log.info("Adding empty structure with AI model name to RTStruct")
            rtstruct_file = os.listdir(self.rtstruct_output_path)
            try:
                if len(rtstruct_file) != 1:
                    raise ValueError(f'Expected one rtstruct file but found {len(rtstruct_file)}')
            except:
                raise Nii2DcmConversionError('E3_09',
                                             f'Multiple RTStructs found at {self.rtstruct_output_path}.')

            rtstruct_filepath = Path(self.rtstruct_output_path, rtstruct_file[0])
            rtstruct = RTStructBuilder.create_from(
                dicom_series_path=self.dicom_series_path,
                rt_struct_path=rtstruct_filepath
            )

            dicom_files = [file for file in os.listdir(self.dicom_series_path) if file.endswith('.dcm')]

            with pydicom.dcmread(os.path.join(self.dicom_series_path, dicom_files[0])) as ds:
                img_array = ds.pixel_array
                img_dimensions = img_array.shape # this is only 2D since it is just one dicom file

                empty_struct_mask = np.zeros((img_dimensions[0], img_dimensions[1], len(dicom_files)), dtype=bool)

            # we need to add a 20x20x20 voxel to the empty struct mask as some planning systems ignore entirely empty structures
            empty_struct_mask[0:20,0:20,0:20] = True
            try:
                rtstruct.add_roi(
                    mask=empty_struct_mask,  # must have same number of layers as dicom series
                    color=[255,255,255],
                    name=f"{self.model.description}. No. of slices {len(dicom_files)}"
                )
            except Exception as e:
                self.log.error(traceback.format_exc())
                raise Nii2DcmConversionError('E3_10', 'An error occured when adding an empty structure with the AI model name to the RTStruct')
            rtstruct.save(str(rtstruct_filepath))
            self.log.info("Finished adding empty structure successfully.")
        else:
            self.log.warning("EmptyStructureWithModelName set to false in config. Not adding a structure with the model name to RTStruct.")

    @staticmethod
    def check_dicom_file_is_image(SOPClassUID: pydicom.uid.UID) -> bool | None:
        """Looks at the given SOPClassUID and checks, based on that,
        if file containing the given SOPClassUID is part of an image UID or
        a non-image UID. Two lists are defined below.

        WARNING: Lists may not be complete.

        :param SOPClassUID: SOPClassUID fetched from a dicom file
        :type SOPClassUID: pydicom.uid.UID
        :return: True if Image, False if non-Image, None if no matching UID has been found
        :rtype: bool | None
        """
        # SOP Class UID of various DICOM file types
        # A (potentially ?) complete list can be found here
        # https://dicom.nema.org/dicom/2013/output/chtml/part04/sect_i.4.html
        # List of non-images
        RTSTRUCT_STORAGE = "1.2.840.10008.5.1.4.1.1.481.3"
        RTPLAN_STORAGE = "1.2.840.10008.5.1.4.1.1.481.5"
        RTDOSE_STORAGE = "1.2.840.10008.5.1.4.1.1.481.2"
        BASIC_STRUCTURED_DISPLAY_STORAGE = "1.2.840.10008.5.1.4.1.1.131"
        OPHTHALMIC_THICKNESS_MAP_STORAGE = "1.2.840.10008.5.1.4.1.1.81"
        CORNEAL_TOPOGRAPHY_MAP_STORAGE = "1.2.840.10008.5.1.4.1.1.82.1"
        RAW_DATA_STORAGE = "1.2.840.10008.5.1.4.1.1.66"
        VOLUME_RENDERING_STORAGE = "1.2.840.10008.5.1.4.1.1.13.1.3"

        # List of images
        CT_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.2"  # Computerized Tomography
        CR_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.1"  # Computed Radiography
        DX_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.1.1"  # Digital Radiography
        MR_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.4"  # Magnetic Resonance
        MG_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.1.2"  # Mammography
        # Optical Coherence Tomography
        OCT_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.77.1.5.4"
        PT_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.128"  # Positron Emission Tomography
        US_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.6.1"  # Ultrasound
        XA_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.12.1"  # Angiography

        if SOPClassUID in [
            RTSTRUCT_STORAGE,
            RTPLAN_STORAGE,
            RTDOSE_STORAGE,
            BASIC_STRUCTURED_DISPLAY_STORAGE,
            OPHTHALMIC_THICKNESS_MAP_STORAGE,
            CORNEAL_TOPOGRAPHY_MAP_STORAGE,
            RAW_DATA_STORAGE,
            VOLUME_RENDERING_STORAGE,
        ]:
            return False
        if SOPClassUID in [
            CT_IMAGE_STORAGE,
            MR_IMAGE_STORAGE,
            CR_IMAGE_STORAGE,
            DX_IMAGE_STORAGE,
            MG_IMAGE_STORAGE,
            US_IMAGE_STORAGE,
            XA_IMAGE_STORAGE,
            OCT_IMAGE_STORAGE,
            PT_IMAGE_STORAGE,
        ]:
            return True

        return None

    @staticmethod
    def check_folder_exists(folder_name: Path) -> bool:
        """
        Checks repeatedly for 5 seconds if a folder exists.
        If not then it returns false. If the folder is found terminate
        the method with True. This can also happen before the 5 seconds.
        This is done to avoid errors occurring from caching of old folder names.

        :param folder_name: Absolute path to the folder
        :type folde_name: Path
        :return: True if folder is found. False if not.
        :rtype: bool
        """
        start_time = time.time()
        while time.time() - start_time < 5:
            if os.path.exists(folder_name):
                return True
        return False

    def ai_config_parser(self, filepath: Path) -> dict[str, list[str]]:
        """
        Reads in the txt-configuration. The txt-configuration that this
        method reads is a stripped and simplified configuration file, which
        is the output of Carsten's parser for the configuration

        :param filepath: Absolute filepath to the location of the configuration
        :type filepath: Path
        :return: Returns a dictionary containing all the configuration elements
        :rtype: dict[str, list[str]]
        """
        # TODO: unit test lowercase used and correct
        config: dict[str, list[str]] = {}
        with open(filepath) as f:
            for line_content in f:
                line_content = line_content
                pattern_dict_key = r'^.* ?(?=:)'  # matches everything from the line start until the first :
                matches_dict_key = re.findall(pattern_dict_key, line_content)
                self.log.debug(f"RegEx AiConfig.txt matches for dict-keys: {matches_dict_key}")
                try:
                    if len(matches_dict_key) == 0:
                        raise ValueError("Did not find a key value in a line of the configuration file.")
                except:
                    raise ConfigFileError('E3_11',
                                                 'Could not find key value for a line in the configuration file.')
                try:
                    if len(matches_dict_key) > 2:
                        raise ValueError(f"Found more than one key value in a line of the configuration file but only expected one: {matches_dict_key}")
                except:
                    raise ConfigFileError('E3_12','Found more than one key value in a configuration file line.')
                matches_dict_key = matches_dict_key[0]

                pattern_dict_value = r'"([^"]*)"'  # matches anything that is enclosed by quotation marks
                matches_dict_value = re.findall(pattern_dict_value, line_content)
                self.log.debug(f"RegEx AiConfig.txt matches for dict-values: {matches_dict_value}")
                try:
                    if len(matches_dict_value) == 0:
                        raise ValueError("Did not find any matches for configuration values in the configuration file.")
                except:
                    raise ConfigFileError('E3_13','Could not find configuration value for key value in the configuration file.')
                try:
                    if len(matches_dict_value) > 1 and 'Struct_' not in matches_dict_key:
                        raise ValueError("Found multiple configuration values for key value in the configuration file.")
                except:
                    raise ConfigFileError('E3_14','Found more than one key value in a configuration file line.')

                config[matches_dict_key.lower()] = matches_dict_value
        self.log.debug(f"Parsed aiconfig.txt: {config}")
        return config

    def change_default_roi_configuration(self):
        """
        This method modifies the default Region of Interest (ROI) configuration based on user-defined parameters.
        The parameters include the name, color, order, and RT ROI interpreted type, which are fetched from a configuration file.
        The method prioritizes user-defined ROIs by always placing them before the non-user-defined ROIs. The user-defined ROIs can also be arranged in a specific order.

        The method works as follows:
        1. Fetches the structure configuration from the configuration file.
        2. Determines the maximum order value from the structure configuration.
        3. Iterates over the default configuration. If a default configuration item is found in the structure configuration, it updates the default configuration item with the structure configuration values.
        4. If a default configuration item is not found in the structure configuration, it increments the order value of the default configuration item by the maximum order value.
        5. Converts the ROI configuration to a dictionary and ensures the 'value' field is an integer.
        6. Sorts the ROI configuration items based on the 'value' field.
        7. Reassigns the 'value' field of each ROI configuration item based on its order in the sorted list.
        8. Returns the updated ROI configuration.
        """
        # these are the structures defined to be overwritten. values come from the aiconfig.txt
        structure_config: dict = {config_value[0]: config_value[1:] for config_key, config_value in self.config.items()
                                  if
                                  'struct_' in config_key}
        #max_order_value = max(structure_config.values(), key=lambda x: int(x[-1]))[-1]
        self.log.debug(f"Structures included in the configuration file: {structure_config}")
        # structure_config sorted based on order value (last value of value list)
        # default_config are the fallback values defined in the dataclass python configs
        default_config: dict[str,Structure] = copy.deepcopy(self.model.structures)
        self.log.debug(f'Default structure configuration {default_config}')
        self.log.debug(f'Maximum Structure Value {len(asdict(self.model)["structures"])}')
        for key_default, value_default in default_config.items():
            # this is to assure case insensitivity.
            # Not a fan...but you know...users are unpredictable.
            # display_value = value_default.display_name.lower()
            value_default.value += len(asdict(self.model)["structures"])
            if value_default.display_name in structure_config.keys():
                value_default.value = structure_config[value_default.display_name][-1]
                value_default.color = ast.literal_eval(structure_config[value_default.display_name][-2])
                value_default.display_name = structure_config[value_default.display_name][0]  # do that last otherwise you'll raise a KeyError
            # else:
            #     value_default.value += int(max_order_value)
        self.log.debug(f'Merged default structure configuration and user configuration into: {default_config}')
        # roi_config = {key: {**value, 'value': int(value['value'])} for key, value in
        #               default_config.items()}  # force value to be int with typecast
        # self.log.debug(default_config.items())


        # sorted_dict_list = sorted(default_config.items(), key=lambda x: x[1]['value'])
        sorted_dict_list = sorted(default_config.items(), key=lambda item: int(item[1].value))
        self.log.debug(sorted_dict_list)
        # sorted_index_dict = {k: {**v, v.value: i} for i, (k, v) in enumerate(sorted_dict_list, start=1)}
        for i, (name, structure) in enumerate(sorted_dict_list, start=1):
            structure.value = str(i)
        sorted_index_dict = dict(sorted_dict_list)
        self.log.debug(f'Updated structure overview: {sorted_index_dict}')
        return sorted_index_dict

    def adjust_rtstruct_dicom_information(self, filepath: Path, remove_file: bool = True) -> Path:
        self.log.info(f'Generating new SOPInstanceUID for AI generated RTStruct')
        sop_instance_org_root = "1.2.826.0.1.3680043.9.7225." # org root for OUH

        datetime_now = datetime.datetime.now()
        now_str = datetime_now.strftime("%Y%m%d%H%M%S%f")
        datetime_hash_obj = hashlib.sha1(now_str.encode())
        hex_dig = int(datetime_hash_obj.hexdigest(), 16) # base 16 is for hexadecimal
        self.log.info(f'Generated SOPInstanceUID is {sop_instance_org_root + str(hex_dig)[:30]}')

        with pydicom.dcmread(filepath) as ds:
            #ds.MediaStorageSOPInstanceUID = sop_instance_org_root + str(hex_dig)[:30] # that is throwing an error. only define in file_meta
            ds.file_meta.MediaStorageSOPInstanceUID = UID(sop_instance_org_root + str(hex_dig)[:30])
            ds.SOPInstanceUID = sop_instance_org_root + str(hex_dig)[:30]

            ds.Manufacturer = 'OUH'
            ds.InstitutionName = 'Radiofysisk Laboratorium'
            ds.ManufacturerModelName = f'OUH_AI_{ds.SeriesDescription}'
            ds.ROIGenerationDescription = ds.ManufacturerModelName

            for roi in ds.RTROIObservationsSequence:
                # Note that the order of organs and their ReferencedROINumber can change
                # if the aiconfig.txt contains struct_ modification
                # an example implementation could go somewhat like
                # if roi.ROINumber == your_roi_number:  # replace with your ROI number
                # RTROIObeservationsSequence is important for the Monaco TPS.

                # this for loop looks through the header and identifies
                # the ROI Number affiliated with the ROI Name.
                # Then given the ROI Name we look in the aiconfig.txt
                # what the RTROIInterpreted Type is
                for structure in ds.StructureSetROISequence:
                    if roi.ObservationNumber == structure.ROINumber:
                        for field in self.config:
                            if 'struct_' in field:
                                new_structure_name = self.config[field][1] # this is the new name of the struct AFTER renaming found in the config
                                if structure.ROIName == new_structure_name:
                                    new_rt_roi_interpreted_type = self.config[field][2] # this is the desired RTROIInterpretedType
                                    roi.RTROIInterpretedType = new_rt_roi_interpreted_type
                                    self.log.info('Changed %s RT ROI Interpreted Type to %s' % (new_structure_name, new_rt_roi_interpreted_type))

            try:
                new_filepath = filepath.with_name(f'rtstruct_{sop_instance_org_root + str(hex_dig)[:30]}.dcm')
            except AttributeError as e:
                self.log.debug(traceback.format_exc())
                raise Nii2DcmConversionError('E3_18', f'Renaming of RTStruct failed.')
            self.log.info(f'Writing file to {new_filepath}')
            ds.save_as(new_filepath)
        if remove_file:
            os.remove(filepath)
        return new_filepath

    def generate_new_rtstruct_filename(self) -> str:
        """
        Generates a new SOPInstanceUID for AI generated RTStruct.
        Useful when modifications have been made on the RTStruct and the RTStruct 
        needs to be re-saved.

        This method generates a new SOPInstanceUID by creating a SHA1 hash of the current datetime and concatenating it with a predefined root string. 
        The generated SOPInstanceUID is then logged and returned.

        :return: A new SOPInstanceUID for AI generated RTStruct.
        :rtype: str
        """
        self.log.info(f'Generating new SOPInstanceUID for AI generated RTStruct')
        sop_instance_org_root = "1.2.826.0.1.3680043.9.7225." # org root for OUH

        datetime_now = datetime.datetime.now()
        now_str = datetime_now.strftime("%Y%m%d%H%M%S%f")
        datetime_hash_obj = hashlib.sha1(now_str.encode())
        hex_dig = int(datetime_hash_obj.hexdigest(), 16) # base 16 is for hexadecimal
        self.log.info(f'Generated SOPInstanceUID is {sop_instance_org_root + str(hex_dig)[:30]}')
        return sop_instance_org_root + str(hex_dig)[:30]

    def remove_structure_from_rtstruct(self, ds: Dataset, roinumber_to_remove: int) -> Dataset:
        """
        Removes a specific structure from several sequences in the dataset.

        This method removes a structure identified by its ROI number from the StructureSetROISequence, ROIContourSequence, and RTROIObservationsSequence in the dataset. It does this by creating new lists that exclude the structure to be removed.

        :param ds: The dataset from which the structure should be removed.
        :type ds: pydicom Dataset
        :param roinumber_to_remove: The ROI number of the structure to be removed.
        :type roinumber_to_remove: int
        """
        # Remove the structure from StructureSetROISequence
        # TODO: figure out why this creates a bug where the structure that is a based on a deleted structure is not displayed
        # in some visualisers
        # TODO: this solution does not work in Monaco
        ds.StructureSetROISequence = [roi for roi in ds.StructureSetROISequence if roi.ROINumber != roinumber_to_remove]

        # Remove the structure from ROIContourSequence
        ds.ROIContourSequence = [contour for contour in ds.ROIContourSequence if contour.ReferencedROINumber != roinumber_to_remove]

        # Remove the structure from RTROIObservationsSequence
        ds.RTROIObservationsSequence = [obs for obs in ds.RTROIObservationsSequence if obs.ReferencedROINumber != roinumber_to_remove]

        return ds

    def merge_structure_with_same_name(self, rtstruct_filepath: Path | None, remove_file=True) -> None:
        """
        Merges structures with the same name in the RTStruct file.

        This method identifies structures with the same name in the RTStruct file and merges them into a single structure.
        It handles cases where the RTStruct file path is not explicitly provided, defaults to the last DICOM file in the
        rtstruct_output_path directory, and attempts to merge structures based on the naming convention defined in the
        aiconfig.txt file.

        WARNING: This function is currently not in use. It was intended to be used for cases at the MR-Linac where merging structures would be necessary.
        We do NOT recommend using this function. Instead the best practice is to have an nnU-Net that is able to delineate
        the OAR and targets as required for the clinical workflow instead of doing something like this function.

        :param rtstruct_filepath: The path to the RTStruct file. If None, the method uses the last DICOM file in the
                                         rtstruct_output_path directory.
        :type rtstruct_filepath: Path | None
        :param remove_file: Indicates whether to remove the original RTStruct file after merging. Defaults to True.
        :type remove_file: bool.

        Raises:
        FileNotFoundError: If the specified rtstruct_filepath does not exist.
        Nii2DcmConversionError: If renaming the RTStruct file fails due to an error in the conversion process.
        """
        self.log.debug('Beginning merging structures with same name.')
        if not rtstruct_filepath:
            self.log.debug('RTStruct filepath not defined. Using default rtstruct location.')
            rtstruct_files = Path(self.rtstruct_output_path.glob('*.dcm'))
            rtstruct_filepath = next(rtstruct_files).absolute()

        # Find out if there are duplicates in the new names column of the aiconfig.txt
        # If yes, then find out how many.
        new_generated_filename = self.generate_new_rtstruct_filename()
        structures = {self.config[field][0]: self.config[field][1] for field in self.config if 'struct_' in field}
        counter = Counter(list(structures.values()))
        duplicates = {item: count for item, count in counter.items() if count > 1}
        if len(duplicates) < 1:
            self.log.debug('Did not find any duplicate named structures. Not merging anything.')
            return None
        else:
            duplicate_overview = {}
            for old_struct_name, new_struct_name in structures.items():
                duplicate_overview.setdefault(new_struct_name, []).append(old_struct_name)
            self.log.debug('Found %i case(s) to be merged' % len(duplicates))
            for structure in duplicates:
                pass
                # TODO: This has only been tested for merging two structures together
                # Still need to look if this works if there are more than 2 structures that should get merged together.
                

                # TODO: activate remove_structure_from_rtstruct once Monaco bug is fixed
                with pydicom.dcmread(rtstruct_filepath) as ds:
                    for ROISeq in ds.StructureSetROISequence:
                        if ROISeq.ROIName == structure:
                            self.log.debug("Removing (%i, %s) from RTStruct" % (ROISeq.ROINumber, ROISeq.ROIName))
                            ds = self.remove_structure_from_rtstruct(ds, ROISeq.ROINumber)
                            
                            # Save the modified DICOM file
                            try:
                               new_filepath = rtstruct_filepath.with_name(f'rtstruct_{new_generated_filename}.dcm')
                            except AttributeError as e:
                               self.log.debug(traceback.format_exc())
                               raise Nii2DcmConversionError('E3_18', f'Renaming of RTStruct failed.')

                            self.log.info(f'Writing file to {new_filepath} after removing {structure}')
                            ds.save_as(new_filepath)
                            rtstruct_filepath = new_filepath
                            # self.log.debug('after remove')
                            # for ROISeq in ds.StructureSetROISequence:
                            #     self.log.debug(ROISeq.ROIName)
            
            # Create new RT Struct. Requires the DICOM series path for the RT Struct.
            # TODO: remove when remove_struct works in Monaco TPS
            rtstruct = RTStructBuilder.create_from(
                dicom_series_path=self.dicom_series_path,
                rt_struct_path=new_filepath)
            for structure in duplicates:
                self.log.info('Merging %s and %s into %s' % (duplicate_overview[structure][0], duplicate_overview[structure][1], structure))

                # merge nifti masks
                # for default_config_structure in 
                structure_values_to_merge = [default_config_structure_settings.value for 
                                            default_config_structure_name, default_config_structure_settings in self.model.structures.items() 
                                            if default_config_structure_settings.display_name in duplicate_overview[structure]]
                file_in_nifti_mask_inference_path = self.nifti_mask_path.glob('*.nii.gz')
                original_niftimask = next(file_in_nifti_mask_inference_path).absolute()
                loaded_niftimask = nibabel.load(original_niftimask)
                niftimask_fdata = loaded_niftimask.get_fdata()
                reduced_niftimask = np.where(np.isin(niftimask_fdata, structure_values_to_merge), niftimask_fdata, 0)


                # code to generate the segmentation mask and get the color it should have
                binary_segmentation_mask = reduced_niftimask.astype(bool).transpose((1, 0, 2)) # transpose is stolen from the nifti_ouh implementation. Apparently this is important.
                new_color = {self.config[field][1]: self.config[field][-2] for field in self.config if 'struct_' in field}

                # Add the 3D mask as an ROI.
                self.log.info('Adding merged ROI %s to RT-Struct' % structure)
                rtstruct.add_roi(
                    mask=binary_segmentation_mask,
                    color=ast.literal_eval(new_color[structure]),
                    name=f"{structure.replace('_AI', '_merged_AI')}",
                    description=f'Grouped structure of {duplicate_overview[structure][0]} and {duplicate_overview[structure][1]}'
                )

            # Save the resulting RT Struct
            # post_merge_filepath = rtstruct_filepath.with_name(f'TEST_rtstruct_{new_generated_filename}.dcm')
            new_filepath = rtstruct_filepath.with_name(f'rtstruct_{new_generated_filename}.dcm')
            self.log.debug('Saved RT-Struct with merge structure in %s' % new_filepath)
            rtstruct.save(str(new_filepath))

            with pydicom.dcmread(new_filepath) as ds:
                for ROISeq in ds.StructureSetROISequence:
                    self.log.debug(ROISeq.ROIName)
            if remove_file:
                os.remove(rtstruct_filepath)


    def compare_model_version_hash(self):
        """
        This method checks if the hash of the model matches the hash defined in the configuration file.

        The method works as follows:
        1. Retrieves the directory where the model hashes are stored from the environment variable 'ouh_inference_model_hash'.
        2. Reads the hash value from the binary file named after the model in the hash directory.
        3. Compares the hash value from the file with the hash value defined in the configuration file.
        4. If the hash values match, it logs a success message and continues execution.
        5. If the hash values do not match, it raises a ValueError.
        6. If the hash file is not found, it raises a FileNotFoundError.
        """
        self.log.info('Checking model version hash match.')
        try:
            hash_directory = os.environ.get("ouh_inference_model_hash")
            filename = self.config['modelname'][0]
            # self.log.info(Path(hash_directory, f'{filename}.bin'), "used for comparing the hash.")
            with open(Path(hash_directory, f'{filename}.bin'), "r") as file:
                file_contents = file.read()
                if file_contents == self.config['modelhash'][0]:
                    self.log.info('Model version hash match. Continuing...')
                else:
                    raise ValueError(
                        'Version hash found in config file did not match with the hash defined for the requested model. The desired model might run a wrong version.')
        except (FileNotFoundError, ValueError) as e:
            if isinstance(e, FileNotFoundError):
                self.log.error('Could not find a matching hash file for the given model.')
                raise ConfigFileError("E3_15", f"No matching hash file found in the hash directory. Did you define the environmental variable 'ouh_inference_model_hash' to the correct folder path?")
            if isinstance(e, ValueError):
                self.log.error('Version hash found in config file did not match with the hash defined for the requested model. The desired model might run a wrong version.')
                raise ConfigFileError('E3_16', 'Version hash found in config file did not match with the hash defined for the requested model. The desired model might run a wrong version.')


    def get_model(self) -> Model:
        """
        Gets the Model configuration by looking up the model name in the config
        :return:
        """
        models: dict = {
            'HN_DAHANCA_CT': model_hn_dahanca_ct,
            'Cervix_Brachy_MR': model_cervix_brachy_mr,
            'Prostate_MRL': model_prostate_mrl,
            'HN_DCPT_CT': model_hn_dcpt_ct,
            'FemalePelvis_MRL': model_femalepelvis_mrl,
        }
        try:
            model_name: str = self.config['modelname'][0].lower()  # contains the string from the config for the model defintion
            models_lower = {k.lower(): v for k, v in models.items()}
            model: Model = models_lower[model_name]  # checks in the models dict for the found string
        except KeyError:
            self.log.error('No corresponding model found for the given model name defined in the received configuration file.')
            self.log.debug(traceback.format_exc())
            raise ConfigFileError('E3_17', 'No corresponding model found for the given model name defined in the received configuration file.')
        return model


class Dcm2NiiConversionError(Exception):
    """Exception raised for conversion errors."""

    def __init__(self, errorcode, message):
        self.errorcode = errorcode
        self.message = message
        super().__init__(self.message)


class Nii2DcmConversionError(Exception):
    """Exception raised for conversion errors."""

    def __init__(self, errorcode, message):
        self.errorcode = errorcode
        self.message = message
        super().__init__(self.message)


class nnUNetError(Exception):
    """Exception raised for conversion errors."""

    def __init__(self, errorcode, message):
        self.errorcode = errorcode
        self.message = message
        super().__init__(self.message)

class ConfigFileError(Exception):
    """Exception raised for conversion errors."""

    def __init__(self, errorcode, message):
        self.errorcode = errorcode
        self.message = message
        super().__init__(self.message)