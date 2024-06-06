from __future__ import annotations

import json
import traceback
from dataclasses import dataclass
import logging
import logging.handlers
import multiprocessing as mp
import time
from pathlib import Path
import sys
import argparse
import os
import shutil
from pydicom import dcmread
from rt_utils import RTStructBuilder
import numpy as np
from datetime import datetime, timedelta
import hashlib
from pydicom.uid import UID

from pynetdicom import AE
from pynetdicom.presentation import StoragePresentationContexts

"""
Input: valid config file
Output: Folder is deleted or renamed. RTStruct is sent to directory and/or DICOM
receiver

Scans directory indicated in the config file for folders called "error_x" or 
"inferred_x".
Folders are expected to be formatted to at least include the following:

|__error_UID/
        |-- dcminput/
        |    |-- file1.dcm
        |    |-- file2.dcm
        |    |__ ...
        |
        |-- aiconfig.txt
        |__ error.txt

|__inferred_UID/
        |-- dcmoutput/
        |    |__ rtstruct.dcm
        |
        |__ aiconfig.txt

For folders called "error_x", an error message is extracted from the error.txt
file and sent in an empty RTStruct to any return directory or DICOM receiver 
indicated in the config file. The folder is then renamed to "handled_error_x".
For folders called "inferred_x", the RTStruct in dcmoutput is sent to any return 
directory or DICOM receiver indicated in the config file. If transmission is
successful, the "inferred_x" folder is deleted. Otherwise, it is renamed to
"handled_error_x".
"""

# TODO: how to handle error when renaming or deleting?

# pt id subfolder when copying to dir


@dataclass
class ReturnserviceConfig:
    """
    Parses the information in the config file
    """
    savepath_str: str
    scan_directory_str: str
    logpath_str: str
    logging_format: str
    logging_level_str: str
    logging_level_pynetdicom_str: str
    ai_config_filename: str
    error_file: str
    ae_title: str
    return_dicom_str: str
    return_directory_str: str
    max_restarts: int
    max_restart_window_sec: int
    days_before_deletion: int
    scan_interval_sec: int
    archive_directory_str: str
    do_archive: bool

    def __init__(self, savepath: str = None):
        self.savepath = savepath
        self.scan_directory = Path()
        self.do_archive = True
        self.archive_directory_str = ""

    def is_valid(self) -> bool:
        """
        Tests the validity of the return service config file

        :return bool: True if all conditions are fulfilled, False otherwise.
        """
        if not self.check_paths():
            return False
        if not self.check_values():
            return False
        return True

    def check_values(self) -> bool:
        """
        Tests the validity of the values given in the return service config
        file

        :return bool: True if all conditions are fulfilled, False otherwise.
        """
        if not isinstance(self.scan_interval_sec, int):
            return False
        if not isinstance(self.max_restarts, int):
            return False
        if not isinstance(self.max_restart_window_sec, int):
            return False
        if not isinstance(self.days_before_deletion, int):
            return False
        if not isinstance(self.logging_format, str):
            return False
        if not isinstance(self.ai_config_filename, str):
            return False
        if not isinstance(self.error_file, str):
            return False
        if not isinstance(self.ae_title, str):
            return False
        if not isinstance(self.return_dicom_str, str):
            return False
        if not isinstance(self.return_directory_str, str):
            return False
        if len(self.ai_config_filename) < 1 or len(self.error_file) < 1 or \
                len(self.ae_title) < 1:
            return False
        if len(self.return_dicom_str) < 1 or len(self.return_directory_str) < 1:
            return False
        if not 1 <= self.scan_interval_sec <= 60:
            return False
        if not 1 <= self.days_before_deletion <= 90:
            return False
        if self.max_restarts < 1:
            return False
        if self.max_restart_window_sec < 60:
            return False
        if self.logging_level_str not in ['DEBUG', 'INFO', 'WARNING', 'ERROR',
                                          'CRITICAL']:
            return False
        if self.logging_level_pynetdicom_str not in ['DEBUG', 'INFO', 'WARNING',
                                                     'ERROR', 'CRITICAL']:
            return False
        if not isinstance(self.do_archive, bool):
            return False
        return True

    def check_paths(self) -> bool:
        """
        Tests the validity of the pathways given in the return service
        config file

        :return bool: True if both pathways exist, False otherwise.

        :raises FileNotFoundError: if either the config file (savepath) or the
        directory to be scanned (scan_directory) cannot be checked
        :raises PermissionError: If not permitted to check for the existence of
        either the config file or the scan directory
        """
        try:
            if not self.savepath.exists() or not self.scan_directory.exists():
                return False

            # More elaborate test for archive is needed, as it is optional
            if self.do_archive: # Defaults to true, but can be configured false
                # If not set in config, the Path will be valid, but will not be where we want to archive
                if self.archive_directory_str == "":
                    return False

                # If set, we need to check if it exists
                if not self.archive_directory.exists():
                    return False

        except (FileNotFoundError, PermissionError):
            return False
        return True

    @property
    def savepath(self):
        return Path(self.savepath_str)

    @savepath.setter
    def savepath(self, value):
        self.savepath_str = str(value)

    @property
    def logpath(self) -> Path:
        return Path(self.logpath_str)

    @logpath.setter
    def logpath(self, value: Path) -> None:
        self.logpath_str = str(value)

    @property
    def logging_level(self) -> int:
        return getattr(logging, self.logging_level_str)

    @logging_level.setter
    def logging_level(self, value: int) -> None:
        self.logging_level_str = logging.getLevelName(value)

    @property
    def logging_level_pynetdicom(self) -> int:
        return getattr(logging, self.logging_level_pynetdicom_str)

    @logging_level_pynetdicom.setter
    def logging_level_pynetdicom(self, value: int) -> None:
        self.logging_level_pynetdicom_str = logging.getLevelName(value)

    @property
    def max_restart_window(self) -> timedelta:
        return timedelta(seconds=self.max_restart_window_sec)

    @max_restart_window.setter
    def max_restart_window(self, value: timedelta) -> None:
        self.max_restart_window_sec = int(value.seconds)

    @property
    def scan_directory(self):
        return Path(self.scan_directory_str)

    @scan_directory.setter
    def scan_directory(self, value):
        self.scan_directory_str = str(value)

    @property
    def archive_directory(self):
        return Path(self.archive_directory_str)

    @archive_directory.setter
    def archive_directory(self, value):
        self.archive_directory_str = str(value)

    def load(self):
        with self.savepath.open('r') as f:
            self.__dict__ = json.load(f)


@dataclass
class AiDir:
    """
    Represents a directory containing folders and files as specified at the
    beginning of this file.

    Attributes:
        path (Path): Required. The file system path to the directory.
        config (ReturnserviceConfig): Required. The configuration settings for
        return service.
        valid (bool): Indicates whether the directory is valid for processing.
        ai_config_path (Path): The path to the AI configuration file. Defined in
        config
        struct_folder_path (Path): File path to folder containing RTStruct.
        Defined in config
        dcm_scan_path (Path): File path to folder containing the DICOM scan.
        Defined in config
        error_file_path (Path): File path to error.txt file. Defined in config
        ae_title (String): The AET used when sending an RTStruct to a DICOM
        receiver. Defined in config
        return_dicom_str (String):  String used for parsing the ai config file
        to find the IP address, port, and AE title of a DICOM receiver. Defined
        in config
        return_directory_str (String):  String used for parsing the ai config
        file to find a return directory. Defined in config
        return_dicom_node_dict (Dict): Dictionary of IP addresses, ports and
        AETs of DICOM receivers
        return_directory_dict (Dict): Dictionary of return addresses
    """
    path: Path
    config: ReturnserviceConfig
    valid: bool = False
    transmission_failed: bool = False
    ai_config_path: Path = None
    struct_folder_path: Path = None
    dcm_scan_path: Path = None
    error_file_path: Path = None
    ae_title: str = None
    return_dicom_str: str = None
    return_directory_str: str = None
    return_dicom_node_dict: dict = None
    return_directory_dict: dict = None
    error_message: str = None

    def __post_init__(self):
        self.ai_config_path = Path(self.path, self.config.ai_config_filename)
        self.log = logging.getLogger(__class__.__name__)
        self.struct_folder_path = Path(self.path, 'dcmoutput')
        self.dcm_scan_path = Path(self.path, 'dcminput')
        self.error_file_path = Path(self.path, self.config.error_file)
        self.ae_title = self.config.ae_title
        self.return_directory_str = self.config.return_directory_str
        self.return_dicom_str = self.config.return_dicom_str

    def load(self):
        """
        Validates the pathway for the current folder and checks whether the AI
        config file exists. Also checks if AI config contains at least one
        return address.

        Output:
             None directly. Self.valid is set to True if requirements are met,
             and False otherwise
        """
        if self.path.exists() is False:
            self.log.error(f'Path does not exist: {self.path}')
            self.valid = False
            return
        if self.ai_config_path.exists() is False:
            self.log.error(f'AI config file does not exist: '
                           f'{self.ai_config_path}')
            self.renaming_to_handled_error()
            self.valid = False
            return
        self.get_all_returns()
        if not (self.return_dicom_node_dict or self.return_directory_dict):
            self.log.error(f'No return address found in '
                           f'{self.ai_config_path}')
            self.renaming_to_handled_error()
            self.valid = False
            return
        self.valid = True

    def validate_struct_folder(self):
        """
        Checks whether the folder containing the RTStruct exists

        :return bool: True if folder exists, False otherwise
            """
        if self.struct_folder_path.exists() is False:
            self.log.error(f'Path does not exist: {self.struct_folder_path}')
            return False
        return True

    def initiate_sending_struct(self):
        """
        Validates that the struct folder exists and that the number of structs
        in it is 1. (To be exact, it counts the number of .dcm files)
        If not, the error is saved as an error message and the error flow
        is initiated
        """

        if self.validate_struct_folder():
            struct_list = []
            for file in os.listdir(self.struct_folder_path):
                # check the files which end with the .dcm extension
                if file.endswith(".dcm"):
                    struct_list.append(file)
        else:
            self.log.error(f'No RTStruct folder found:'
                           f'{self.struct_folder_path}')
            self.error_message = "ERROR 4.01 No RTStruct generated from " \
                                 "inference"
            self.handle_error()
            return
        if struct_list.__len__() == 1:
            struct = struct_list[0]
            struct_path = Path(self.struct_folder_path, struct)

            # Archive first!
            if self.config.do_archive and self.config.archive_directory.exists():
                self.archive_struct(struct_path)


            self.send_struct_to_all_returns(struct_path)
            return
        elif struct_list.__len__() == 0:
            self.log.error(f'No RTStruct file found in '
                           f'{self.struct_folder_path}. Expected one RTStruct.')
            self.error_message = "ERROR 4.01 No RTStruct found after inference"
            self.handle_error()
            return
        else:
            self.log.error(f'Too many structs/files in '
                           f'{self.struct_folder_path}. Expected one RTStruct.')
            self.error_message = "ERROR 4.02 Too many RTStructs found after " \
                                 "inference"
            self.handle_error()
            return

    def archive_struct(self, struct_path: Path):
        """
        Archives the RTStruct and aiconfig.txt to the archive directory
        """
        try:
            patient_id = dcmread(struct_path).PatientID
            if patient_id is None or patient_id == "": # If no patient ID is found, set to "Unknown"
                patient_id = "Unknown"
            struct_archive_directory_base_name = f'{datetime.now().strftime("%Y%m%d")}_' + patient_id

            # test if path exsist and if not create it.
            # If it does, append a number to the end, repeat until a unique path is found
            i = 1
            struct_archive_path = Path(self.config.archive_directory, struct_archive_directory_base_name + f'_{i:02d}')
            while struct_archive_path.exists():
                struct_archive_path = Path(self.config.archive_directory, struct_archive_directory_base_name + f'_{i:02d}')
                i += 1

            struct_archive_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(struct_path, struct_archive_path)
            shutil.copy2(self.ai_config_path, struct_archive_path)

            self.log.info(f'Archived RTStruct and aiconfig to {struct_archive_path}')

        except Exception as e:
            self.log.error(f'Failed to archive RTStruct to '
                           f'{self.config.archive_directory}. {e}')

    def send_struct_to_all_returns(self, struct_path, error=False):
        """
        Iterates through return addresses and sends the RTStruct to them.
        Checks for a sendScan bool and sends the scan images if the bool is True
        When sending dcm files through file copy, a folder with the patient ID
         as its name is created at the return address.
        If the function is called as part of an inferred folder flow, it
        evaluates whether the RTStruct was successfully sent to all addresses.
        If not, the folder is renamed to "handled_error_UID".

        :param Path struct_path: File path to the RTStruct that should be sent
        :param bool error: Set to True if function is run as part of error flow,
        and False otherwise
        """
        for return_dir_dict in self.return_directory_dict.values():
            ds = dcmread(struct_path)
            patient_id = ds.PatientID
            return_directory_v1 = return_dir_dict[self.return_directory_str]
            return_directory = Path(return_directory_v1, patient_id)
            if not return_directory.exists():
                # Make a directory for DCM file(s) named after the patient ID,
                # if it does not already exist
                try:
                    os.mkdir(return_directory)
                except FileNotFoundError:
                    self.log.error("FileNotFoundError: could not create folder "
                                   f"for DCM file(s) in {return_directory_v1}")
                    self.transmission_failed = True
                    continue  # if making the directory fails, skip to the
                    # next return address
            self.copy_file_to_dir(struct_path, return_directory)
            try:  # find sendscan bool value from return directory dictionary.
                # if this fails, the bool may not exist, and the program
                # defaults to false
                sendScan_dir = \
                    return_dir_dict[self.return_directory_str+'SendScan']
                sendScan_dir = json.loads(sendScan_dir.lower())
            except:
                sendScan_dir = False
            if sendScan_dir:
                # copy scan to return directory if sendscan bool is set to true
                # in ai config file
                self.copy_scan_to_dir(return_directory)
        for return_dicom_node in self.return_dicom_node_dict.values():
            self.send_struct(struct_path, return_dicom_node)
            # TODO: skal struct sendes først eller sidst
            try:
                sendScan = return_dicom_node[self.return_dicom_str+'SendScan']
                sendScan = json.loads(sendScan.lower())
            except:
                sendScan = False
            if sendScan:
                # send scan to DICOM node, if SendScan bool is set to True in ai
                # config file
                self.send_scan(return_dicom_node)
        if not error:
            # If function is run as part of successful inferred flow,
            # delete folder if all transmissions were successful.
            # Return if part of error flow
            if self.transmission_failed:
                # If at least one transmission failed, rename folder instead of
                # deletion
                self.renaming_to_handled_error()
                return
            else:
                self.delete_sent_folder()
        return

    def get_all_returns(self):
        """
        Iterates through the AI config file and creates a dictionary of return
        IP addresses, ports, and AETS as well as a list of return directories

        :raises KeyError: if trying to access a non-existing dictionary. The
        missing dictionary is then created
        """
        return_dicom_node_dict = {}
        return_directory_dict = {}
        with open(self.ai_config_path) as file:
            for line in file:
                if line.startswith(self.return_dicom_str):
                    number, value = self.parse_string_for_variable_name(line)
                    try:
                        return_dicom_node_dict[number][value] = \
                            self.parse_string_for_value(line)
                    except KeyError:  # create nested dict if it does not exist
                        return_dicom_node_dict[number] = dict()
                        return_dicom_node_dict[number][value] = \
                            self.parse_string_for_value(line)
                elif line.startswith(self.return_directory_str):
                    number, value = self.parse_string_for_variable_name(line)
                    try:
                        return_directory_dict[number][value] = \
                            self.parse_string_for_value(line)
                    except KeyError:  # create nested dict if it does not exist
                        return_directory_dict[number] = dict()
                        return_directory_dict[number][value] = \
                            self.parse_string_for_value(line)
        self.return_dicom_node_dict = return_dicom_node_dict
        self.return_directory_dict = return_directory_dict
        return

    def parse_string_for_variable_name(self, input_string):
        """
        Returns the variable name (i.e. ipaddress, port, aet) and its
        number
        Example of expected input format: 'ReturnDicomNodeIP_1:{ip_address}"\n'
        Example of output: ReturnDicomNodeIP, 1

        :param String input_string: a string of text parsed from the AI config
        file.

        :return String number: a number parsed from the input string
        :return String value: a value parsed from the input string
        """
        line_name = input_string.strip()
        line_name = line_name.split(':')[0]
        number = line_name.split('_')[-1]
        value = line_name.split('_')[0]
        return number, value

    def parse_string_for_value(self, input_string):
        """
        Returns the value of the string, i.e the information/string after
        the first ':', without quotations

        :param String input_string: a string of text parsed from the AI config
        file

        :return String value (String): a value parsed from the input string
        """
        value = input_string.split(':', 1)[1]  # keep everything after first ':'
        value = value.replace('"', '')
        value = value.strip()
        return value

    def copy_file_to_dir(self, file_path, return_dir, scan=False):
        """
        Copies a file to the return directory. If this fails, the bool
        self.transmission_failed is set to True

        :param Path file_path: The file path of the file to be copied
        :param String return_dir: The path of the return directory
        :param bool scan: False by default. If set to true, less logging
        output is given

        :raises FileNotFoundError: If the file and/or return directory could not
         be found
        :raises Exception e: If copying the file fails for other reasons
        """
        return_dir_censored = self.censor_pt_id(return_dir)
        try:
            self.log.debug(
                f'Copying {file_path.name} to {return_dir_censored}')
            new_struct_path = Path(return_dir, file_path.name)
            shutil.copy2(file_path, new_struct_path)
            if not scan:  # To avoid too much feedback to the log, a successful
                # copy is only reported for the rtstruct and not for every image
                # in a scan
                self.log.info(f'Successfully copied RTStruct to '
                              f'{return_dir_censored}')
            return
        except FileNotFoundError:  # invalid path
            self.log.error(
                f'FileNotFoundError. Possibly invalid return directory. '
                f'Failed to copy {file_path.name} to {return_dir_censored}')
        except Exception as e:
            self.log.error(
                f'Failed to copy {file_path.name} to {return_dir_censored}. {e}')
        self.transmission_failed = True
        return

    def censor_pt_id(self, return_dir):
        # censor the last half of the folder name (which is the patient ID) for
        # the log, so as to not have full patient ID in the log
        return_dir_namev1 = str(return_dir)
        return_dir_name = return_dir_namev1[0:(len(return_dir_namev1)) - len(
            str(return_dir.name)) // 2]
        return_dir_name += "*" * (len(return_dir_namev1) - len(return_dir_name))
        return return_dir_name

    def copy_scan_to_dir(self, return_dir):
        """
           Copies scan images used for inference service to return directory.
           If a transmission is unsuccessful, the bool self.transmission_failed
           is set to True

           :param String return_dir: The pathway of the return directory
           :raises IOError: if unable to load in the files to be copied
               """
        return_dir_censored = self.censor_pt_id(return_dir)
        try:
            dicom_files = [file for file in os.listdir(self.dcm_scan_path)
                           if file.endswith('.dcm')]
        except IOError as e:
            self.log.error(f"Error when attempting to load in dcm files from "
                           f"{self.dcm_scan_path.parts[-2]}\\"  # patient folder 
                           f"{self.dcm_scan_path.parts[-1]}. "  # pt scan folder
                           f"Cannot copy scan to {return_dir_censored}. {e}")
            self.transmission_failed = True
            return
        for dcm in dicom_files:
            dcm = Path(self.dcm_scan_path, dcm)
            self.copy_file_to_dir(dcm, return_dir, scan=True)
        self.log.info(f'Finished copying scan to {return_dir_censored}')
        return

    def send_struct(self, struct_path, return_address):
        """
        Sends RTstruct to return address through the DICOM protocol. If a
        transmission is unsuccessful, the bool self.transmission_failed is set
        to True

        :param Path struct_path: The file path of the RTStruct to be copied
        :param Dict return_address: A dictionary containing the IP address,
        port, and AET of the DICOM receiver

        :raises Exception e: if failed to associate with the return address
        :raises IOError: if unable to load in the RTStruct that should be sent
        """

        # To avoid information overload from pynetdicom during DICOM
        # transmission, it has a seperate logging level
        logger = logging.getLogger('pynetdicom')
        logger.setLevel(self.config.logging_level_pynetdicom_str)

        try:
            # Initialise the Application Entity
            ae = AE()
            ae.ae_title = self.ae_title
            # Add a requested presentation context
            ae.requested_contexts = StoragePresentationContexts
            # Associate with address
            ip_address = return_address[self.return_dicom_str+'IP']
            port = int(return_address[self.return_dicom_str+'Port'])
            aet = return_address[self.return_dicom_str+'AET']
            assoc = ae.associate(ip_address, port, ae_title=aet)
            self.log.debug(f'Sending {struct_path.name} to '
                           f'{ip_address}:{port}:{aet}')
        except Exception as e:
            self.log.error(f'Failed to associate with return address to send '
                           f'RTStruct. {e}')
            self.transmission_failed = True
            return
        if assoc.is_established:
            try:
                rtstruct = dcmread(struct_path, force=True)
            except IOError as e:
                self.log.error(f"Failed to import {struct_path} to send to "
                               f"{ip_address}:{port}:{aet}. {e}")
                assoc.release()
                self.transmission_failed = True
                return
            else:
                # Use the C-STORE service to send the dataset
                # returns the response status as a pydicom Dataset
                status = assoc.send_c_store(rtstruct)
                # Check the status of the storage request
                if status:
                    # If the storage request succeeded this will be 0x0000
                    self.log.debug('C-STORE request status: 0x{0:04x}'.format(
                        status.Status))
                    self.log.info(
                        f'Successfully sent RTStruct to '
                        f'{ip_address}:{port}:{aet}')
                    assoc.release()
                    return
                else:
                    self.log.error(
                        f'Failed to send RTStruct to '
                        f'{ip_address}:{port}:{aet}. Connection timed out, '
                        f'was aborted or received invalid response')
                    assoc.release()
                    self.transmission_failed = True
                    return
        else:
            self.log.error(f'Could not send RTStruct to '
                           f'{ip_address}:{port}:{aet}. '
                           f'Association rejected, aborted or never connected')
            self.transmission_failed = True
            return

    def send_scan(self, return_address):  # TODO: hvorfor forsvinder mr. .dcm?
        """
           Sends scan used for inference service to return address through the
           DICOM protocol. If a transmission is unsuccessful, the bool
           self.transmission_failed is set to True

           :param Dict return_address: A dictionary containing the IP address,
           port, and AET of the DICOM receiver

           :raises KeyError: if failing to extract ip address, port or aet
           :raises Exception e1: if failed to associate with the return address
           :raises Exception e2: if failing to send a dcm file
           :raises IOError: if unable to load in the scan that should be sent
           :raises ConnectionError: if errors with connection are encountered
           during transmission
               """

        # To avoid information overload from pynetdicom during DICOM
        # transmission, it has a seperate logging level
        logger = logging.getLogger('pynetdicom')
        logger.setLevel(self.config.logging_level_pynetdicom_str)

        try:
            # Initialise the Application Entity
            ae = AE()
            ae.ae_title = self.ae_title
            # Add a requested presentation context
            ae.requested_contexts = StoragePresentationContexts
            # Associate with address
            ip_address = return_address['ReturnDicomNodeIP']
            port = int(return_address['ReturnDicomNodePort'])
            aet = return_address['ReturnDicomNodeAET']
            assoc = ae.associate(ip_address, port, ae_title=aet)
        except KeyError:
            self.log.error(f'Failed to associate with return address to send '
                           f'scan. The return address may be incomplete. '
                           f'It should contain ip address, port, and ae title')
            self.transmission_failed = True
            return
        except Exception as e1:
            self.log.error(f'Failed to associate with return address to send'
                           f' scan. {e1}')
            self.transmission_failed = True
            return
        if assoc.is_established:
            try:
                dicom_files = [file for file in os.listdir(self.dcm_scan_path)
                               if file.endswith('.dcm')]
            except IOError as e:
                self.log.error(f"Error when attempting to load in dcm files "
                               f"from {self.dcm_scan_path.parts[-2]}\\"  # pt folder 
                               f"{self.dcm_scan_path.parts[-1]}. "  # pt scan folder
                               f"Cannot send scan to {ip_address}:{port}:{aet}."
                               f" {e}")
                assoc.release()
                self.transmission_failed = True
                return
            else:
                self.log.info(
                    f'Sending scan to {ip_address}:{port}:{aet}')
                for dcm in dicom_files:
                    # Use the C-STORE service to send the dataset
                    # returns the response status as a pydicom Dataset
                    dcm_path = Path(self.dcm_scan_path, dcm)
                    dcm_ds = dcmread(str(dcm_path))
                    try:
                        status = assoc.send_c_store(dcm_ds)
                        if not status:
                            self.log.error(
                                f'Failed to send {str(dcm)}')
                            self.transmission_failed = True
                    except ConnectionError:
                        # This exception does not seem to capture the error if
                        # it occurs. The code does not break when it happens,
                        # however, so this is a minor issue
                        self.log.error(
                            f'ConnectionError: Failed to send {str(dcm)}')
                        self.transmission_failed = True
                    except Exception as e2:
                        self.log.error(f'Failed to send {str(dcm)}. {e2}')
                        self.transmission_failed = True
                # Release the association
                self.log.info(f'Finished sending scan to '
                              f'{ip_address}:{port}:{aet}')
                assoc.release()
                return
        else:
            self.log.error(f'Could not send scan to '
                           f'{ip_address}:{port}:{aet}. '
                           f'Association rejected, aborted or never connected')
            self.transmission_failed = True
            return

    def delete_sent_folder(self):
        """
        Deletes inferred folder when RTStruct has been successfully sent

        :raises PermissionError: if not permitted to delete folder, e.g. because
        it is in use
        :raises Exception e: if unable to delete folder for other reasons
        """
        try:
            shutil.rmtree(self.path)
            self.log.info(f"Deleted {self.path.name} after successful "
                          f"transmission")
        except PermissionError:
            self.log.error(f"PermissionError. Unable to delete folder named "
                           f"{self.path.name}")
        except Exception as e:
            self.log.error(f"Unable to delete folder named {self.path.name}. "
                           f"{e}")
        return

    def set_error_message(self):
        """
        Finds error message in error file in folder and stores the error message
        in self.error_message.
        If unsuccessful, the folder is renamed.

        :return bool: True if an error message was successfully found, False
            otherwise
        """
        if self.error_file_path.exists():
            try:
                with open(str(self.error_file_path)) as file:
                    self.error_message = file.readlines()[0]
                return True
            except IndexError:
                pass
        self.log.error(f"Error file and/or error message does not exist: "
                       f"{self.error_file_path}")
        self.renaming_to_handled_error()
        return False

    def handle_error(self):
        """
        Initiates error flow to make and send empty struct with error message as
        name, given that the folder containing the DICOM scan exists. If not,
        the folder is renamed to indicate error
        """
        if not self.dcm_scan_path.exists():
            self.log.error(f'Path does not exist: {self.dcm_scan_path}')
            self.renaming_to_handled_error()
            return
        else:
            error_struct_path = self.create_error_struct()
            if error_struct_path:
                error_struct_path = \
                    self.adjust_rtstruct_dicom_information(error_struct_path)
                self.send_struct_to_all_returns(error_struct_path, error=True)
            self.renaming_to_handled_error()
            return

    def create_error_struct(self):
        """
        Creates empty RTStruct with error message stored as name and series
         description. SeriesDate and SeriesTime are updated to current
          DateTime, and the following tags are altered to reflect the origin of
          the new RTStruct: Manufacturer, InstitutionName, ManufacturerModelName

        :return Path error_struct_path: File path to an empty RTStruct whose
        name includes an error message

        :raises exception e0: if unable to build the empty RTStruct
        :raises exception e1: if unable to add empty structure to the RTStruct
        :raises exception e2: if unable to alter DICOM tags
        :raises exception e3: if unable to save the empty RTStruct
        """
        error_struct_path = Path(self.path, 'rtstruct_temp.dcm')
        try:
            rtstruct = RTStructBuilder.create_new(
                dicom_series_path=str(self.dcm_scan_path))
        except Exception as e0:
            self.log.error(f"Unable to make empty RTStruct based on input path:"
                           f" {self.dcm_scan_path}. {e0}")
            return
        dicom_files = [file for file in os.listdir(self.dcm_scan_path) if
                       file.endswith('.dcm')]

        empty_struct_mask = np.zeros((1, 1, len(dicom_files)), dtype=bool)
        # we need to add a tiny dot to the empty struct mask as some planning
        # systems ignore entirely empty structures
        empty_struct_mask[0, 0, 0] = True
        try:
            rtstruct.add_roi(
                mask=empty_struct_mask,
                # must have same number of layers as dicom series
                color=[255, 0, 0],
                name=self.error_message
            )
        except Exception as e1:
            self.log.error(f'An error occured when adding an empty'
                           f' structure with the model name to the'
                           f' error RTStruct {error_struct_path}. {e1}')
            return
        try:
            date_time = datetime.now()
            rtstruct.ds.SeriesDate = date_time.strftime('%Y%m%d')
            rtstruct.ds.SeriesTime = date_time.strftime('%H%M%S')
            rtstruct.ds.Manufacturer = 'OUH'
            rtstruct.ds.InstitutionName = 'Radiofysisk Laboratorium'
            rtstruct.ds.ManufacturerModelName = f'OUH_AI_{self.error_message}'
            rtstruct.set_series_description(self.error_message)
        except Exception as e2:
            self.log.error(f'An error occured when setting information'
                           f' in the error RTStruct {error_struct_path}. {e2}')
        try:
            rtstruct.save(str(error_struct_path))
            self.log.debug(f'Saved empty RTStruct for error reporting: '
                           f'{error_struct_path}')
            return error_struct_path
        except Exception as e3:
            self.log.error(f'Unable to save empty RTStruct for error reporting.'
                           f' {e3}')
            return

    def adjust_rtstruct_dicom_information(self, filepath: Path):
        """
        Assigns new SOPInstanceUID to the RTStruct such that it conforms to OUH
        UID-naming conventions. This is saved as a new RTStruct, and the old
        RTStruct is deleted. The RTStruct is used for error reporting

        :param Path filepath: path to the RTStruct whose information should be
            adjusted

        :return Path new_filepath: Path to the new RTStruct with new
        SOPInstanceUID which includes the OUH prefix.
        """
        self.log.debug(f'Generating SOPInstanceUID')
        sop_instance_org_root = "1.2.826.0.1.3680043.9.7225."
        # org root for OUH

        datetime_now = datetime.now()
        now_str = datetime_now.strftime("%Y%m%d%H%M%S%f")
        datetime_hash_obj = hashlib.sha1(now_str.encode())
        hex_dig = int(datetime_hash_obj.hexdigest(),
                      16)  # base 16 is for hexadecimal

        with dcmread(filepath) as ds:
            ds.file_meta.MediaStorageSOPInstanceUID = UID(
                sop_instance_org_root + str(hex_dig)[:30])
            ds.SOPInstanceUID = sop_instance_org_root + str(hex_dig)[:30]
            new_filepath = filepath.with_name(
                f'rtstruct_{sop_instance_org_root + str(hex_dig)[:30]}.dcm')
            ds.save_as(new_filepath)
            self.log.info("Created empty RTStruct for error reporting")
        os.remove(filepath)
        return new_filepath

    def renaming_to_handled_error(self):
        """
        Renames current folder by giving it the prefix 'handled_error_'

        :raises PermissionError: If not permitted to rename folder, e.g. if it
        is in use
        :raises WindowsError: If unable to rename folder as name already exists
        :raises Exception e: If unable to rename folder for other reasons
        """
        if self.path.stem.startswith("handled_error"):  # avoid renaming twice
            self.log.debug("Attempted renaming twice")
            return
        elif self.path.stem.startswith("inferred"):
            self.log.info(f'Renaming {self.path.name} to 'f'handled_error_'
                          f'{self.path.name.replace("inferred_", "")}')
            new_path = Path(self.path.parent, f'handled_error_'
                            f'{self.path.name.replace("inferred_", "")}')
        else:
            self.log.info(f'Renaming {self.path.name} to handled_error_'
                          f'{self.path.name.replace("error_", "")}')
            new_path = Path(self.path.parent,
                            f'handled_error_'
                            f'{self.path.name.replace("error_", "")}')
        try:
            self.path.rename(new_path)
            self.path = new_path
        except PermissionError:
            self.log.error(f"PermissionError. Unable to rename folder: "
                           f"{self.path.name}")
        except WindowsError:
            self.log.error(f"WinError. Unable to rename folder {self.path.name}"
                           f" to {new_path.name}, as it already exists")
        except Exception as e:
            self.log.error(f"Unable to rename folder: {self.path.name}. {e}")
        return


class AiSharedDir:
    """
    A class representing the directory to be scanned for folders of interest

    :param config ReturnserviceConfig: an instance of the ReturnserviceConfig
    class
    :param Logger log: logging file for logging output
    """

    def __init__(self, config: ReturnserviceConfig, log: logging.Logger):
        self.log = log
        self.config = config
        # Events
        self.stop_event = mp.Event()

    def scan_directory(self) -> None | AiDir:
        """
        Scans the directory specified in the config file and iterates
        through any items found.
        If a valid directory with the prefix 'inferred_' is found, it is handled
        by the inferred flow (i.e. an RTStruct is transmitted to one or more
        return addresses, and the folder is deleted)
        If a valid directory with the prefix 'error_' is found, it is handled
        by the error flow (i.e. an empty RTStruct is created and transmitted to
        one or more return addresses, and the folder is renamed to
        'handled_error_')
        If a directory with the prefix 'handled_error_' is found, it is deleted,
        if it is found to be older than 30 days (configurable)
        """
        for f in self.config.scan_directory.iterdir():
            if f.is_dir():
                if f.name.lower().startswith('inferred_'):
                    self.log.info(f'Found inferred folder {f.name}. Sending...')
                    d = AiDir(path=f, config=self.config)
                    d.load()
                    if d.valid:
                        # Start the inferred flow
                        d.initiate_sending_struct()
                if f.name.lower().startswith('error_'):
                    self.log.info(f'Found error folder {f.name}. Handling...')
                    d = AiDir(f, config=self.config)
                    d.load()
                    if d.valid:
                        if d.set_error_message():
                            # start the error flow
                            d.handle_error()
                if f.name.lower().startswith('handled_error'):
                    self.delete_old_folder(f)
        return

    def delete_old_folder(self, f):
        """
        Determines the age of a folder, and deletes the folder if it is older
        than 30 days (configurable)

        :param Path f: folder to be deleted

        :raises PermissionError: if unable to get permission to delete folder,
        e.g. if it is in use
        :raises Exception e: if unable to delete folder for other reasons
        """
        mtime = os.stat(f).st_mtime
        seconds_old = time.time() - mtime
        days_old = seconds_old / 60 / 60 / 24
        if days_old > self.config.days_before_deletion:
            try:
                shutil.rmtree(f)
                self.log.info(
                    f"Deleted {f.name} after "
                    f"{self.config.days_before_deletion} days")
            except PermissionError:
                self.log.error(
                    f"PermissionError. Unable to delete folder named "
                    f"{f.name}")
            except Exception as e:
                self.log.error(
                    f"Unable to delete folder named {f.name}. {e}")
        return


def returnservice_worker(config: ReturnserviceConfig, my_stop_event: mp.Event,
                         my_busy_event: mp.Event) -> None:
    """
    The worker function for the returnservice process that scans directories
    and processes them. This function runs in a separate process and
    continuously monitors a directory for new 'inferred_', 'error_' and
     'handled_error' directories to process.

    :param config ReturnserviceConfig: The configuration object containing
    settings for the returnservice.
    :param Event my_stop_event: An event to signal the process to stop running.
    :param Event my_busy_event: An event to signal the main process that the
    worker is busy.

    :raises KeyboardInterrupt: when the worker is stopped by the user
    :raises Exception e: when the worker stops due to error
    """
    setup_logging(config, 'Worker')
    log = logging.getLogger('Return service Worker')
    log.info('Starting return service worker')
    last_loop = time.time() - config.scan_interval_sec  # Kick off right away
    try:
        while not my_stop_event.is_set():
            if time.time() - last_loop >= config.scan_interval_sec:
                my_busy_event.set()  # Comunicate to the main process that we
                # are busy
                last_loop = time.time()
                log.debug('Scanning directory')
                d = AiSharedDir(config, log)
                d.scan_directory()
            time.sleep(0.5)
    except KeyboardInterrupt:
        my_busy_event.clear()
        log.info('KeyboardInterrupt: stopping')
        return None
    except Exception as e:
        my_busy_event.clear()
        log.error(f'Error in worker: {e}')
        log.error(traceback.format_exc())
    log.info('Done')


def setup_logging(config: ReturnserviceConfig, module) -> None:
    """
    Sets up logging based on information in the Returnservice config file.
    The log is named using the format: returnservice_module_log
    The log is rotated each midnight. This means, that logging after each
     rotation is done in a new log of the same naming format, while the
     previous log is renamed with a suffix of the format 'yyyy-mm-dd',
     indicating when it was created. A maximum of 30 logs are kept for each
     module

    :param config ReturnserviceConfig: an instance of the ReturnserviceConfig
    class
    :param String module: the name of the module from which the log is
    instantiated

    Output: none directly. Creates a log file of the format
        returnservice_module_log, if it does not exist
    """
    log_name = 'returnservice_' + module + '_log'
    log_file = Path(config.logpath, log_name)
    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format,
        handlers=[
            logging.StreamHandler(),
            logging.handlers.TimedRotatingFileHandler(
                filename=log_file, when='midnight', interval=1,
                backupCount=config.days_before_deletion)
        ]
    )

    return


if __name__ == '__main__':
    """
    Handles initial parsing of config file and starts the worker
    
    The program should be run as follows:
    
    python main.py --config file_path_for_config_file.json
    
    Input: config file as specified above
    Output: None directly. Runs the program
    
    :raises KeyBoardInterrupt: if the program is interrupted by the user
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True,
                        help='Path to config file')
    args = parser.parse_args()

    configpath = None
    if args.config:
        configpath = Path(args.config.strip())

    if not configpath.exists():
        sys.exit(
            f'Config-file not found. Path given: {configpath} '
            f'{str(configpath.exists())}')

    returnservice_config = ReturnserviceConfig(configpath)
    returnservice_config.load()

    if not returnservice_config.is_valid():
        sys.exit(f'Config is not valid: {returnservice_config}')

    setup_logging(returnservice_config, 'Main')
    log = logging.getLogger('Main')
    if returnservice_config.scan_directory.exists() is False:
        log.error(
            f'Could not find scan directory: '
            f'{returnservice_config.scan_directory}')
        exit(1)
    log.info(f'Return service started.')
    log.info(f'Config: {returnservice_config}')
    log.debug(f'Setting up worker')

    stop_event = mp.Event()
    busy_event = mp.Event()
    restarts = []

    worker = mp.Process(target=returnservice_worker, args=(
        returnservice_config, stop_event, busy_event))
    worker.start()
    try:
        while True:
            if worker is None or not worker.is_alive():
                current_time = datetime.now()
                # Clean up, keep only recent restarts
                restarts = [restart_time for restart_time in restarts if
                            current_time - restart_time <
                            returnservice_config.max_restart_window]
                if len(restarts) >= returnservice_config.max_restarts:
                    log.error(
                        'Maximum worker restarts reached within time window. '
                        'Shutting down.')
                    break
                if worker is not None:
                    log.error(
                        'Worker has stopped unexpectedly. '
                        'Attempting to restart.')
                    worker.join()  # Ensure the old process resources are
                    # cleaned up
                restarts.append(current_time)
                # Calculate the backoff time, 2,4,8,16,32,60 seconds.
                backoff_time = min(2 ** len(restarts), 60)  # Exponential
                # backoff capped at 60 seconds
                log.info(
                    f'Waiting for {backoff_time} seconds before restarting '
                    f'worker.')
                time.sleep(backoff_time)
                log.info('Starting new worker task.')
                worker = mp.Process(target=returnservice_worker,
                                    args=(returnservice_config, stop_event,
                                          busy_event))
                worker.start()

        time.sleep(1)
    except KeyboardInterrupt:
        log.info('KeyboardInterrupt: stopping')
        if busy_event.is_set():  # If the worker is busy, wait for it to finish
            log.info('Waiting for worker to finish')
            busy_event.wait(timeout=500)
        stop_event.set()
        if worker is not None:
            worker.join()
        exit(0)
    finally:
        stop_event.set()
        if worker is not None:
            worker.join()
