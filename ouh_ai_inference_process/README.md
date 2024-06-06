# InferenceProcess

Command line tool for starting an inference process. Mainly called by a service of our OUH AI Inference Serivce

## Purpose
Running nnU-Net Inference with the configurations given by a configuration file.
The tool takes consists of dcm2nii conversion --> nnU-Net inference --> nii2dcm conversion

## Install
To install the tool go into the directory where the `setup.py` file is located.
Run
```python
pip insall -r requirements.txt
pip install .
```

## Usage
Open a cmd tool and run
```bash
ouh_inference --folder [the folder you want to run inference on]
```