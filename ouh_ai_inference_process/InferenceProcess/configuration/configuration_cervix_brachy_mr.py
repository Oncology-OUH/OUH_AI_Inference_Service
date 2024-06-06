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


gtv = Structure(
    value=1,
    names=['GTV'],
    display_name='GTV_AI',
    color=[153, 51, 0]
)

hr_ctv = Structure(
    value=2,
    names=['HR-CTV'],
    display_name='HR-CTV_AI',
    color=[165, 161, 55]
)

bladder = Structure(
    value=3,
    names=['Bladder'],
    display_name='Bladder_AI',
    color=[127, 255, 212]
)

rectum = Structure(
    value=4,
    names=['Rectum'],
    display_name='Rectum_AI',
    color=[192, 255, 0]
)

sigmoid = Structure(
    value=5,
    names=['Sigmoid'],
    display_name='Sigmoid_AI',
    color=[0, 255, 0]
)

bowel = Structure(
    value=6,
    names=['Bowel'],
    display_name='Bowel_AI',
    color=[192, 0, 0]
)

nnunet = NNUnet(
    p='nnUNetPlans',
    tr='nnUNetTrainerDARot60deg',
    c='3d_fullres',
    f="0 1 2 3 4",
    save_probabilities=False,
    chk='checkpoint_final.pth',
    post_processing_pickle=f"{os.environ['nnUNet_results']}/Dataset510_Cervix_Brachy_MR/nnUNetTrainerDARot60deg__nnUNetPlans__3d_fullres/crossval_results_folds_0_1_2_3_4/postprocessing.pkl",
    post_processing_plan=f"{os.environ['nnUNet_results']}/Dataset510_Cervix_Brachy_MR/nnUNetTrainerDARot60deg__nnUNetPlans__3d_fullres/plans.json"
)

model_cervix_brachy_mr = Model(
    name='Cervix_Brachy_MR',
    id='510',
    description='Cervix_Brachy_AI v2',
    structures={
        'GTV': gtv,
        'HR-CTV': hr_ctv,
        'Bladder': bladder,
        'Rectum': rectum,
        'Sigmoid': sigmoid,
        'Bowel': bowel
    },
    nnunet=nnunet
)
