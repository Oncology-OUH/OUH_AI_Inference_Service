import json
import pickle
from unittest import TestCase
import tempfile
import shutil
import hashlib
import base64
import os

from pathlib import Path

import cv2
import torch
import nibabel as nib
import numpy as np

from HashService.hash_dir import hash_dir


class TestHashDir(TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_empty_directory(self):
        """
        Checks if an empty directory produces a
        hash.
        """
        # check if an empty directory gets hashed
        expected_hash = hashlib.md5().hexdigest()
        self.assertEqual(hash_dir(Path(self.test_dir)), expected_hash)

    def test_single_file(self):
        """
        Checks if it can read a single file
        and that it produces a different hash for
        a single dir with a file than for an empty dir.
        """
        with open(os.path.join(self.test_dir, 'file.txt'), 'w') as f:
            f.write('Hello world!')

        self.assertNotEqual(hash_dir(Path(self.test_dir)), hashlib.md5().digest())

    def test_identical_directories(self):
        other_dir = tempfile.mkdtemp()
        with open(os.path.join(other_dir, 'file.txt'), 'w') as f:
            f.write('Hello world!')
        with open(os.path.join(self.test_dir, 'file.txt'), 'w') as f:
            f.write('Hello world!')

        self.assertEqual(hash_dir(Path(self.test_dir)), hash_dir(Path(other_dir)))

    def test_various_file_types(self):
        """
        Checks if a directory with various files
        (i.e. json, pickle, png, torch model and nifti)
        can be read in and hashed.
        """
        # Create a JSON file
        with open(os.path.join(self.test_dir, 'file.json'), 'w') as f:
            json.dump({'key': 'value'}, f)

        # Create a pickle file
        with open(os.path.join(self.test_dir, 'file.pkl'), 'wb') as f:
            pickle.dump({'key': 'value'}, f)

        # Create a PNG image file
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.imwrite(os.path.join(self.test_dir, 'file.png'), img)

        # Create a PyTorch model file
        model = torch.nn.Linear(10, 10)
        torch.save(model.state_dict(), os.path.join(self.test_dir, 'file.pth'))

        # Create a NIfTI file
        data = np.zeros((10, 10, 10), dtype=np.int16)
        img = nib.Nifti1Image(data, np.eye(4))
        nib.save(img, os.path.join(self.test_dir, 'file.nii.gz'))

        # The directory should be hashable
        self.assertIsInstance(hash_dir(Path(self.test_dir)), str)