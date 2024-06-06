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


anal_canal = Structure(
    value=1,
    names=['Anal_Canal', 'AnalCanal'],
    display_name='AnalCanal_AI',
    color=[153, 51, 0]
)

bladder = Structure(
    value=2,
    names=['Bladder'],
    display_name='Bladder_AI',
    color=[165, 161, 55]
)

bowel = Structure(
    value=3,
    names=['Bowel'],
    display_name='Bowel_AI',
    color=[127, 255, 212]
)

fem_head_l = Structure(
    value=4,
    names=['Femoral_Head_L', 'FemoralHeadL', 'FemoralHead_L', 'FemoralHead_R'],
    display_name='FemoralHead_L_AI',
    color=[192, 255, 0]
)

fem_head_r = Structure(
    value=5,
    names=['Femoral_Head_R', 'FemoralHeadR'],
    display_name='FemoralHead_R_AI',
    color=[0, 255, 0]
)

rectum = Structure(
    value=6,
    names=['Rectum'],
    display_name='Rectum_AI',
    color=[34, 139, 34]
)

sigmoid = Structure(
    value=7,
    names=['Sigmoid'],
    display_name='Sigmoid_AI',
    color=[51, 204, 51]
)

nnunet = NNUnet(
    p='nnUNetPlans',
    tr='nnUNetTrainerNoMirroring',
    c='3d_fullres',
    f="0 1 2 3 4",
    save_probabilities=False,
    chk='checkpoint_final.pth',
    post_processing_pickle=f"{os.environ['nnUNet_results']}/Dataset513_FemalePelvis_MRL/nnUNetTrainerNoMirroring__nnUNetPlans__3d_fullres/crossval_results_folds_0_1_2_3_4/postprocessing.pkl",
    post_processing_plan=f"{os.environ['nnUNet_results']}/Dataset513_FemalePelvis_MRL/nnUNetTrainerNoMirroring__nnUNetPlans__3d_fullres/plans.json"
)

model_femalepelvis_mrl = Model(
    name='FemalePelvis_MRL',
    id='513',
    description='FemalePelvis_MRL_AI v2',
    structures={
        'Bladder': bladder,
        'Rectum': rectum,
        'Anal_Canal': anal_canal,
        'Bowel': bowel,
        'Sigmoid': sigmoid,
        'Femoral_Head_L': fem_head_l,
        'Femoral_Head_R': fem_head_r
    },
    nnunet=nnunet
)
