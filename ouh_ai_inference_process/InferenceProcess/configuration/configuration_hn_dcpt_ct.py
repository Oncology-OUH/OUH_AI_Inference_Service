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

cochlea_lr = Structure(
    value=1,
    names=['Cochlea_LR'],
    display_name='Cochlea_LR_AI',
    color=[255, 0, 0] # Example color red
)

lens_lr = Structure(
    value=2,
    names=['Lens_LR'],
    display_name='Lens_LR_AI',
    color=[0, 255, 0] # Example color green
)

eyesback_lr = Structure(
    value=3,
    names=['EyesBack_LR'],
    display_name='EyesBack_LR_AI',
    color=[0, 0, 255] # Example color green
)

eyesfront_lr = Structure(
    value=4,
    names=['EyesFront_LR'],
    display_name='EyesFront_LR_AI',
    color=[255, 255, 0] # Example color green
)

lacrimal_lr = Structure(
    value=5,
    names=['Lacrimal_LR'],
    display_name='Lacrimal_LR_AI',
    color=[0, 255, 255] # Example color green
)

parotid_lr = Structure(
    value=6,
    names=['Parotid_LR'],
    display_name='Parotid_LR_AI',
    color=[255, 0, 255] # Example color green
)

buccalMuc_lr = Structure(
    value=7,
    names=['BuccalMuc_LR'],
    display_name='BuccalMuc_LR_AI',
    color=[128, 0, 0] # Example color green
)

submandibular_lr = Structure(
    value=8,
    names=['Submandibular_LR'],
    display_name='Submandibular_LR_AI',
    color=[0, 128, 0] # Example color green
)

carotid_lr = Structure(
    value=9,
    names=['Carotid_LR'],
    display_name='Carotid_LR_AI',
    color=[0, 0, 128] # Example color green
)

thyroid = Structure(
    value=10,
    names=['Thyroid'],
    display_name='Thyroid_AI',
    color=[128, 128, 0] # Example color green
)

spinalCord = Structure(
    value=11,
    names=['SpinalCord'],
    display_name='SpinalCord_AI',
    color=[0, 128, 128] # Example color green
)

pcm_up = Structure(
    value=12,
    names=['PCM_Up'],
    display_name='PCM_Up_AI',
    color=[128, 0, 128] # Example color green
)

pcm_mid = Structure(
    value=13,
    names=['PCM_Mid'],
    display_name='PCM_Mid_AI',
    color=[192, 0, 0] # Example color green
)

pcm_low = Structure(
    value=14,
    names=['PCM_Low'],
    display_name='PCM_Low_AI',
    color=[0, 192, 0] # Example color green
)

oralCavity = Structure(
    value=15,
    names=['OralCavity'],
    display_name='OralCavity_AI',
    color=[0, 0, 192] # Example color green
)

mandible = Structure(
    value=16,
    names=['Mandible'],
    display_name='Mandible_AI',
    color=[192, 192, 0] # Example color green
)

lips = Structure(
    value=17,
    names=['Lips'],
    display_name='Lips_AI',
    color=[0, 192, 192] # Example color green
)

larynxSG = Structure(
    value=18,
    names=['LarynxSG'],
    display_name='LarynxSG_AI',
    color=[192, 0, 192] # Example color green
)

larynxG = Structure(
    value=19,
    names=['LarynxG'],
    display_name='LarynxG_AI',
    color=[192, 192, 192] # Example color green
)

esophagus = Structure(
    value=20,
    names=['Esophagus'],
    display_name='Esophagus_AI',
    color=[100, 100, 100] # Example color green
)

brain = Structure(
    value=21,
    names=['Brain'],
    display_name='Brain_AI',
    color=[200, 255, 50] # Example color green
)


nnunet = NNUnet(
    p='nnUNetPlans',
    tr='nnUNetTrainer',
    c='3d_fullres',
    f="0 1 2 3 4",
    save_probabilities=False,
    chk='checkpoint_final.pth',
    post_processing_pickle=None,
    post_processing_plan=None
)

model_hn_dcpt_ct = Model(
    name='HN_DCPT_CT',
    id='515',
    description='HN_DCPT_CT_AI v2',
    structures={
    'Cochlea_LR': cochlea_lr,
    'Lens_LR': lens_lr,
    'EyesBack_LR': eyesback_lr,
    'EyesFront_LR': eyesfront_lr,
    'Lacrimal_LR': lacrimal_lr,
    'Parotid_LR': parotid_lr,
    'BuccalMuc_LR': buccalMuc_lr,
    'Submandibular_LR': submandibular_lr,
    'Carotid_LR': carotid_lr,
    'Thyroid': thyroid,
    'SpinalCord': spinalCord,
    'PCM_Up': pcm_up,
    'PCM_Mid': pcm_mid,
    'PCM_Low': pcm_low,
    'OralCavity': oralCavity,
    'Mandible': mandible,
    'Lips': lips,
    'LarynxSG': larynxSG,
    'LarynxG': larynxG,
    'Esophagus': esophagus,
    'Brain': brain
    },
    nnunet=nnunet
)
