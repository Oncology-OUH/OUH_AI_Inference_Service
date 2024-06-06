from dataclasses import dataclass
from typing import List, Tuple
import os

@dataclass
class Structure:
    value: int
    names: List[str]
    display_name: str
    color: List[int]


@dataclass
class NNUnet:
    p: str
    tr: str
    c: str
    f: str
    save_probabilities: bool
    chk: str
    post_processing_pickle: str
    post_processing_plan: str

@dataclass
class Model:
    name: str
    id: str
    description: str
    structures: dict[str, Structure]
    nnunet: NNUnet

brainstem = Structure(
    value=1,
    names=['Brainstem'],
    display_name='Brainstem_AI',
    color=[34, 139, 34]
)
cavity_oral = Structure(
    value=2,
    names=['Cavity_Oral', 'OralCavity'],
    display_name='OralCavity_AI',
    color=[165, 161, 55]
)
esophagus = Structure(
    value=3,
    names=['Esophagus'],
    display_name='Esophagus_AI',
    color=[34, 139, 34]
)
glnd_parotid_l = Structure(
    value=4,
    names=['Glnd_Parotid_L', 'Parotid_L'],
    display_name='Parotid_L_AI',
    color=[192, 255, 0]
)
glnd_parotid_r = Structure(
    value=5,
    names=['Glnd_Parotid_R', 'Parotid_R'],
    display_name='Parotid_R_AI',
    color=[0, 255, 0]
)
glnd_submand_l = Structure(
    value=6,
    names=['Glnd_Submand_L', 'Submandibular_L'],
    display_name='Submandibular_L_AI',
    color=[192, 255, 0]
)
glnd_submand_r = Structure(
    value=7,
    names=['Glnd_Submand_R', 'Submandibular_L'],
    display_name='Submandibular_R_AI',
    color=[0, 255, 0]
)
glnd_thyroid = Structure(
    value=8,
    names=['Glnd_Thyroid', 'Thyroid'],
    display_name='Thyroid_AI',
    color=[0, 255, 0]
)
larynx = Structure(
    value=9,
    names=['Larynx', 'LarynxG', 'Larynx_G'],
    display_name='LarynxG_AI',
    color=[165, 161, 55]
)
larynx_sg = Structure(
    value=10,
    names=['Larynx_SG', 'LarynxSG'],
    display_name='LarynxSG_AI',
    color=[165, 80, 65]
)
lips = Structure(
    value=11,
    names=['Lips'],
    display_name='Lips_AI',
    color=[165, 161, 55]
)
mucosa_l = Structure(
    value=12,
    names=['Mucosa_L', 'BuccalMuc_L'],
    display_name='BuccalMuc_L_AI',
    color=[192, 255, 0]
)
mucosa_r = Structure(
    value=13,
    names=['Mucosa_R', 'BuccalMuc_R'],
    display_name='BuccalMuc_R_AI',
    color=[0, 255, 0]
)
pcm_low = Structure(
    value=14,
    names=['PCM_Low'],
    display_name='PCM_Low_AI',
    color=[70, 130, 180]
)
pcm_mid = Structure(
    value=15,
    names=['PCM_Mid'],
    display_name='PCM_Mid_AI',
    color=[0, 160, 160]
)
pcm_up = Structure(
    value=16,
    names=['PCM_Up'],
    display_name='PCM_Up_AI',
    color=[127, 255, 212]
)
spinal_cord = Structure(
    value=17,
    names=['SpinalCord', 'Spinal_Cord'],
    display_name='SpinalCord_AI',
    color=[34, 139, 34]
)

nnunet = NNUnet(
    p='nnUNetPlans',
    tr='nnUNetTrainerNoMirroring',
    c='3d_fullres',
    f="0 1 2 3 4",
    save_probabilities=False,
    chk='checkpoint_best.pth',
    post_processing_pickle=f"{os.environ['nnUNet_results']}/Dataset511_DAHANCA_HN_CT/nnUNetTrainerNoMirroring__nnUNetPlans__3d_fullres/crossval_results_folds_0_1_2_3_4/postprocessing.pkl",
    post_processing_plan=f"{os.environ['nnUNet_results']}/Dataset511_DAHANCA_HN_CT/nnUNetTrainerNoMirroring__nnUNetPlans__3d_fullres/plans.json"
)

model_hn_dahanca_ct = Model(
    name='HN_DAHANCA_CT',
    id='511',
    description='HN_DAHANCA_CT_AI v2',
    structures={
        'Cavity_Oral': cavity_oral,
        'Glnd_Submand_L': glnd_submand_l,
        'Glnd_Submand_R': glnd_submand_r,
        'PCM_Low': pcm_low,
        'PCM_Mid': pcm_mid,
        'PCM_Up': pcm_up,
        'Larynx': larynx,
        'Larynx_SG': larynx_sg,
        'Lips': lips,
        'Mucosa_L': mucosa_l,
        'Mucosa_R': mucosa_r,
        'Esophagus': esophagus,
        'Glnd_Parotid_L': glnd_parotid_l,
        'Glnd_Parotid_R': glnd_parotid_r,
        'SpinalCord': spinal_cord,
        'Glnd_Thyroid': glnd_thyroid,
        'Brainstem': brainstem
    },
    nnunet=nnunet
)
