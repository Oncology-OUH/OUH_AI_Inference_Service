import logging
import os
from pathlib import Path
from hash_dir import hash_dir

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)-8s %(name)-12s: %(message)s',
        handlers=[
            logging.FileHandler("hash_serivce.log", 'w', 'utf-8'),
            logging.StreamHandler()
        ]
    )
    log = logging.getLogger('HashService')

    model_directories: dict = {
        'Prostate_MRL': Path(os.environ['nnUNet_results'], 'Dataset509_Prostate_MRL'),
        'Cervix_Brachy_MR': Path(os.environ['nnUNet_results'], 'Dataset510_Cervix_Brachy_MR'),
        'HN_DAHANCA_CT': Path(os.environ['nnUNet_results'],'Dataset511_DAHANCA_HN_CT'),
        'FemalePelvis_MRL': Path(os.environ['nnUNet_results'], 'Dataset513_FemalePelvis_MRL'),
        'MalePelvis_MRL': Path(os.environ['nnUNet_results'], 'Dataset514_MalePelvis_MRL'),
    }

    for model_name, model_path in model_directories.items():
        log.info(f'Hashing {model_name}')
        with open(f"{os.environ['ouh_inference_model_hash']}/{model_name}.bin", 'w') as file:
            file.write(hash_dir(model_path))
