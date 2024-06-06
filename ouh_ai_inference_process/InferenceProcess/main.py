import argparse
import logging
import os
import sys
from pathlib import Path
import signal
from datetime import datetime

from InferenceProcess import InferenceProcess, Dcm2NiiConversionError
from InferenceProcess.inference import Nii2DcmConversionError, nnUNetError, ConfigFileError


def main():
    parser = argparse.ArgumentParser(description='OUH Inference CLI-tool. Full AI Inference pipeline processing Dicom images and returning an RTStruct.')
    parser.add_argument('-f', '--folder',
                        help="Defines the folder that should be used for inference. The folder needs to contain a configuration file including the model name that should be used for inference (i.e. Prostate_MRL, Cervix_Brachy_MR, DAHANCA_HN_CT)",
                        required=True)
    args = parser.parse_args()

    

    # Get the current date
    current_date = datetime.now()

    # Format the date as YYYY_MM_DD
    formatted_date = current_date.strftime('%Y_%m_%d')
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)-8s %(name)-12s: %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(args.folder, "inference.log"), 'w', 'utf-8'),
            logging.FileHandler(os.path.join(args.folder, f"inference_{formatted_date}.log"), 'a+', 'utf-8'),
            logging.StreamHandler()
        ]
    )
    log = logging.getLogger('InferenceProcess')
    log.info('Inference Service starting!')

    # We are expecting a folder that is called active_{DateTimestamp}_{UID}.
    if not Path(args.folder).exists():
        raise FileNotFoundError(f"Folder {args.folder} not found.")

    # There are four folders used for the inference. 'dcminput' *should*
    # already exist. The other three we need to create.
    inference_folders = ['dcminput', 'niftiimage', 'niftimask_tmp', 'niftimask', 'dcmoutput']
    if not Path(args.folder, 'dcminput').exists():
        raise FileNotFoundError(f"Folder {Path(args.folder, 'dcminput')} not found.")
    for folder_name in inference_folders[1:]:
        folder_path = os.path.join(args.folder, folder_name)
        os.makedirs(folder_path, exist_ok=True)

    # Define a signal handler function to handle the termination signal from the parent process
    def handle_termination_signal(signum, frame):
        log.info('Received termination signal from parent process. Terminating nnU-Net inference.')
        # You can add any necessary cleanup code here before terminating the process
        sys.exit(0)

    # Register the signal handler function for the termination signal
    signal.signal(signal.SIGTERM, handle_termination_signal)

    try:
        inference = InferenceProcess(location=Path(args.folder))
        inference.convert_dcm_to_nifti()
        inference.run_nnunet_inference()
        inference.run_nnunet_postprocessing()
        inference.convert_nifti_to_rtstruct()
        inference.add_model_description_structure()
    except (Dcm2NiiConversionError, Nii2DcmConversionError, nnUNetError, ConfigFileError) as e:
        with open(Path(args.folder, "error.txt"), "w") as file:
            file.write(f"{e.errorcode}: {type(e).__name__}. {e.message}")
        raise

    log.info('Inference Service finished!')


if __name__ == '__main__':
    sys.exit(main())
