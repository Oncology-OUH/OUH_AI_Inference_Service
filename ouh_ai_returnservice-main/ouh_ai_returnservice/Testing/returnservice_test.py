import os
import logging
import time
import pytest
from datetime import datetime
import sys
from pydicom import dcmread
from pathlib import Path
import shutil
sys.path.append(r'C:\Home\Python\ouh_ai_returnservice')
from main import ReturnserviceConfig, AiDir, AiSharedDir

# TODO: test at alle try except virker som forventet
# TODO: implementer utests


def valid_config():
    """an example of a valid config
    To be valid, the following is required:
     - a Testing folder containing a testdir folder. Testing folder should be in
     the same directory as the main.py code
    iven that the savepath exists and that Testing/testdir subfolders exist)"""
    config = ReturnserviceConfig()
    config.savepath_str = ".\\returnservice_config_example.json"
    config.scan_directory_str = "Testing\\testdir"
    config.logpath_str = "Testing\\testdir"
    config.logging_format = "format"
    config.logging_level_str = "DEBUG"
    config.logging_level_pynetdicom_str = "INFO"
    config.ai_config_filename = "aiconfig.txt"
    config.error_file = "error.txt"
    config.ae_title = "aet"
    config.return_dicom_str = "ReturnDicomNode"
    config.return_directory_str = "ReturnDirectory"
    config.max_restarts = 5
    config.max_restart_window_sec = 360
    config.days_before_deletion = 30
    config.scan_interval_sec = 1
    config.logpath = Path(config.logpath_str)
    config.scan_directory = Path(config.scan_directory_str)
    config.savepath = Path(config.savepath_str)
    config.archive_directory_str = "Testing\\testdir\\archive"
    config.do_archive = True
    return config


def make_aidir():
    """make aidir class for testing"""
    folder = Path("Testing/testdir/testfolder")
    aidir = AiDir(path=folder, config=valid_config())
    return aidir


def make_shared_dir():
    log = logging.getLogger('testlog')
    config = valid_config()
    shared_dir = AiSharedDir(config, log)
    return shared_dir


def test_is_valid():  # TODO?
    config = valid_config()
    assert config.check_values() is True
    assert config.check_paths() is True
    assert config.is_valid() is True


class TestCheckValues:

    def test_check_values_scan_interval(self):
        """
        Testing scan_interval_sec
        Requirements: integer, >=1, <=60
        """
        config = valid_config()
        config.scan_interval_sec = 'test'
        assert config.check_values() is False
        config.scan_interval_sec = 0
        assert config.check_values() is False
        config.scan_interval_sec = -5
        assert config.check_values() is False
        config.scan_interval_sec = 70
        assert config.check_values() is False
        config.scan_interval_sec = 50
        assert config.check_values() is True

    def test_check_values_max_restarts(self):
        """
        testing max_restarts
        Requirements: integer, >=1
        """
        config = valid_config()
        config.max_restarts = 'test'
        assert config.check_values() is False
        config.max_restarts = 0
        assert config.check_values() is False
        config.max_restarts = 30
        assert config.check_values() is True

    def test_check_values_max_restart_window(self):
        """
            testing max_restart_window_sec
            Requirements: integer, >= 60
            """
        config = valid_config()
        config.max_restart_window_sec = 'test'
        assert config.check_values() is False
        config.max_restart_window_sec = 40
        assert config.check_values() is False
        config.max_restart_window_sec = 100
        assert config.check_values() is True

    def test_check_values_days_before_deletion(self):
        """
        testing days_before_deletion
        Requirements: integer, >=1, <=90
        """
        config = valid_config()
        config.days_before_deletion = 'test'
        assert config.check_values() is False
        config.days_before_deletion = -10
        assert config.check_values() is False
        config.days_before_deletion = 150
        assert config.check_values() is False
        config.days_before_deletion = 10
        assert config.check_values() is True

    def test_check_values_logging_format(self):
        """
        Testing logging_format
        Requirements: string
        """
        config = valid_config()
        config.logging_format = True
        assert config.check_values() is False
        config.logging_format = ""
        assert config.check_values() is True
        config.logging_format = "some string"
        assert config.check_values() is True

    def test_check_values_ai_config_filename(self):
        """
        Testing ai_config_filename
        Requirements: string, nonempty
        """
        config = valid_config()
        config.ai_config_filename = True
        assert config.check_values() is False
        config.ai_config_filename = ""
        assert config.check_values() is False
        config.ai_config_filename = "some string"
        assert config.check_values() is True

    def test_check_values_error_file(self):
        """
        Testing error_file
        Requirements: string, nonempty
        """
        config = valid_config()
        config.error_file = True
        assert config.check_values() is False
        config.error_file = ""
        assert config.check_values() is False
        config.error_file = "some string"
        assert config.check_values() is True

    def test_check_values_ae_title(self):
        """
        Testing ae_title
        Requirements: string, nonempty
        """
        config = valid_config()
        config.ae_title = True
        assert config.check_values() is False
        config.ae_title = ""
        assert config.check_values() is False
        config.ae_title = "some string"
        assert config.check_values() is True

    def test_check_values_return_dicom(self):
        """
        Testing return_dicom_str
        Requirements: string, nonempty
        """
        config = valid_config()
        config.return_dicom_str = True
        assert config.check_values() is False
        config.return_dicom_str = ""
        assert config.check_values() is False
        config.return_dicom_str = "some string"
        assert config.check_values() is True

    def test_check_values_return_directory(self):
        """
        Testing return_directory_str
        Requirements: string, nonempty
        """
        config = valid_config()
        config.return_directory_str = True
        assert config.check_values() is False
        config.return_directory_str = ""
        assert config.check_values() is False
        config.return_directory_str = "some string"
        assert config.check_values() is True

    def test_check_values_logging_level(self):
        """
        Testing logging_level_str
        Requirements: string, one of: 'DEBUG', 'INFO', 'WARNING', 'ERROR',
        'CRITICAL'
        """
        config = valid_config()
        config.logging_level_str = True
        assert config.check_values() is False
        config.logging_level_str = ""
        assert config.check_values() is False
        config.logging_level_str = "some string"
        assert config.check_values() is False
        config.logging_level_str = "WARNING"
        assert config.check_values() is True

    def test_check_values_do_archive(self):
        """
        Testing do_archive
        Requirements: boolean
        """
        config = valid_config()
        config.do_archive = "test"
        assert config.check_values() is False
        config.do_archive = True
        assert config.check_values() is True
        config.do_archive = False
        assert config.check_values() is True


def test_check_paths():
    """
    Testing paths: savepath, scan_directory, archive_directory
    Requirements: valid paths to existing directories
    """
    config = valid_config()
    config.savepath = Path("fake\\path")
    assert config.check_paths() is False
    config.savepath = Path("Testing")
    assert config.check_paths() is True

    config.scan_directory = Path("fake\\path")
    assert config.check_paths() is False
    config.scan_directory = "Testing"
    assert config.check_paths() is True
    config.scan_directory = Path("Testing")
    assert config.check_paths() is True

    config.archive_directory = Path("fake\\path")
    assert config.check_paths() is False
    config.archive_directory = "Testing"
    assert config.check_paths() is True
    config.archive_directory = Path("Testing")
    assert config.check_paths() is True


def test_parse_string_for_variable_name():
    """Test prober string parsing"""
    aidir = make_aidir()
    assert aidir.parse_string_for_variable_name('test_1: "test/val"')==('1', 'test')
    assert aidir.parse_string_for_variable_name('test_2: " t_est:val"')==('2', 'test')


def test_parse_string_for_value():
    """Test prober string parsing"""
    aidir = make_aidir()
    assert aidir.parse_string_for_value('test_1: "test/val"')=='test/val'
    assert aidir.parse_string_for_value('test_2: " t_est:val"')=='t_est:val'


def test_delete_sent_folder():
    """Tests that the function deletes the folder"""
    aidir = make_aidir()
    timestamp = time.time()  # use timestamp to make test more failsafe
    folder_path = Path(aidir.config.scan_directory_str,
                       "delete_folder_test_"+str(timestamp))
    os.mkdir(folder_path)  # create folder to be deleted
    aidir.path = folder_path
    assert folder_path.exists() is True  # check that created folder exists
    aidir.delete_sent_folder()  # use function to delete folder
    assert folder_path.exists() is False  # folder is now deleted


def test_renaming_to_handled_error():
    timestamp = time.time()  # use timestamp to make test more failsafe
    aidir = make_aidir()
    folder_path = Path(aidir.config.scan_directory_str,
                       "error_test_" + str(timestamp))
    # make test folder
    os.mkdir(folder_path)
    assert folder_path.exists()  # folder exists
    aidir = make_aidir()
    aidir.path = folder_path
    aidir.renaming_to_handled_error()  # rename test folder
    assert folder_path.exists() is False  # check success of renaming
    new_path = Path(aidir.config.scan_directory_str,
                    "handled_error_test_"+str(timestamp))
    assert new_path.exists() is True  # check success of renaming
    shutil.rmtree(new_path)  # cleanup
    ## 3x except


def test_delete_old_folder():
    """testing that folder is not deleted before specified time has passed
    In this case, half a second"""
    shareddir = make_shared_dir()
    shareddir.config.days_before_deletion = 0.0000057  # 1/2 second
    timestamp = time.time()  # use timestamp to make test failsafe
    folder_path = Path(shareddir.config.scan_directory_str,
                       "old_folder_test_" + str(timestamp))
    os.mkdir(folder_path)
    assert folder_path.exists() is True  # check that created folder exists
    shareddir.delete_old_folder(folder_path)
    # folder is not old enough to be deleted, so it still exists
    assert folder_path.exists() is True
    time.sleep(0.5) # wait half a second
    shareddir.delete_old_folder(folder_path)
    # folder is now old enough to be deleted
    assert folder_path.exists() is False


def test_validate_struct_folder():
    aidir = make_aidir()
    timestamp = time.time()  # use timestamp to make test more failsafe
    folder_path = Path(aidir.config.scan_directory_str,
                       "struct_folder_test_" + str(timestamp))
    # create test folder
    os.mkdir(folder_path)
    aidir.struct_folder_path = folder_path
    assert aidir.validate_struct_folder() is True  # test folder exists
    shutil.rmtree(folder_path)  # remove test folder
    assert aidir.validate_struct_folder() is False  # test folder does not exist


def test_copy_struct_to_dir():
    aidir = make_aidir()
    # path to test struct
    test_struct = Path(aidir.config.scan_directory_str,
                       "testfolder\\dcmoutput\\test_struct.dcm")
    return_dir = aidir.config.scan_directory_str
    #  test copying of test struct
    aidir.copy_file_to_dir(test_struct, return_dir)
    assert aidir.transmission_failed is False
    new_struct = Path(return_dir, "test_struct.dcm")
    assert new_struct.exists() is True  #  check for copied file
    os.remove(new_struct)  # cleanup
    # test that function can handle invalid path
    fake_dir = Path("invalid\\path")
    aidir.copy_file_to_dir(test_struct, fake_dir)
    assert aidir.transmission_failed is True


def test_create_error_struct():
    aidir = make_aidir()
    aidir.error_message = "test"
    # expected Path when running test
    struct_name = 'rtstruct_temp.dcm'
    struct_path = Path(aidir.path, struct_name)
    # check that struct does not exist (for safety)
    assert struct_path.exists() is False
    # check that function outputs expected Path
    assert aidir.create_error_struct() == struct_path
    # check that struct now exists
    assert struct_path.exists() is True
    # check that tags have been correctly altered:
    with dcmread(struct_path) as ds:
        date_time = datetime.now()
        assert ds.SeriesDate == date_time.strftime('%Y%m%d')
        assert ds.Manufacturer == 'OUH'
        assert ds.InstitutionName == 'Radiofysisk Laboratorium'
        assert ds.ManufacturerModelName == f'OUH_AI_{aidir.error_message}'
        assert ds.SeriesDescription == aidir.error_message
    # remove struct
    os.remove(struct_path)
    # check that struct was successfully removed
    assert struct_path.exists() is False
    return


def test_adjust_rtstruct_dicom_information():
    aidir = make_aidir()
    aidir.error_message = "test"
    struct_name = 'rtstruct_temp.dcm'
    struct_path = Path(aidir.path, struct_name)
    # check that struct does not exist yet (for safety)
    assert struct_path.exists() is False
    # create error struct for testing
    filepath = aidir.create_error_struct()
    # check that struct was created
    assert struct_path.exists() is True
    # adjust information
    new_path = aidir.adjust_rtstruct_dicom_information(filepath)
    # test that new version exists and old version is deleted
    assert new_path.exists() is True
    assert struct_path.exists() is False
    # remove new version
    os.remove(new_path)
    # check for successful removal
    assert new_path.exists() is False
    return


def test_get_all_returns():
    # Uses Testing/testdir/testfolder
    aidir = make_aidir()
    # check that no return addresses are stored
    assert aidir.return_dicom_node_dict is None
    assert aidir.return_directory_dict is None
    aidir.get_all_returns()
    # check that return addresses are now stored
    assert aidir.return_dicom_node_dict is not None
    assert aidir.return_directory_dict is not None



def test_set_error_message():
    # testing that error message gets set
    aiDir = make_aidir()
    # check that no error message is set
    assert aiDir.error_message is None
    aiDir.error_file_path = Path(aiDir.path,"error.txt")
    # set error message
    assert aiDir.set_error_message() is True
    # check that error message is as expected
    assert aiDir.error_message == "nnUNetConversionError"
    return


def test_load():
    # load and check validity of valid folder
    valid_folder = Path("Testing/testdir/inferred_testfolder_inf")
    aiDir = AiDir(path=valid_folder, config=valid_config())
    aiDir.load()
    assert aiDir.valid is True
    # load and check validity of invalid valid folder
    invalid_folder = Path("testdir/doesnotexist")
    aiDir = AiDir(path=invalid_folder, config=valid_config())
    aiDir.load()
    assert aiDir.valid is False


def test_send_struct():
    ### OBS!!! make sure to use a valid DICOM receiver when testing the
    # sending module

    test_DICOM_receiver_directory = r"C:\Home\Python\DICOM_receiver"
    test_dicom_node = {"ReturnDicomNodeIP": "127.0.0.1",
                       "ReturnDicomNodePort": 11112,
                       "ReturnDicomNodeAET": "test_receiver"}

    aidir = make_aidir()
    # initial check
    assert aidir.transmission_failed is False
    # path to test struct

    test_struct = Path(aidir.config.scan_directory_str,
                       "testfolder\\dcmoutput\\test_struct.dcm")

    #with dcmread(test_struct) as ds:
     #    sopuid = ds.SOPInstanceUID
    ds = dcmread(test_struct, specific_tags=[("SOPInstanceUID")])

    #  test sending of test struct
    aidir.send_struct(test_struct, test_dicom_node)
    # check that sending succeeded
    assert aidir.transmission_failed is False
    # check that struct was sent by looking for its SOPInstanceUID
    new_struct = Path(test_DICOM_receiver_directory, ds.SOPInstanceUID)
    assert new_struct.exists()
    #cleanup and test of cleanup
    os.remove(new_struct)
    assert new_struct.exists() is False
    # test that function can handle invalid path
    fake_dicom_node = {"ReturnDicomNodeIP": "1234",
    "ReturnDicomNodePort": 11112, "ReturnDicomNodeAET": "invalid_aet"}
    aidir.send_struct(test_struct, fake_dicom_node)
    assert aidir.transmission_failed is True

    return

def utest_handle_error():
    # first create test folder# TODO: dette er en god måde at lave testmapper på
    aidir = make_aidir()
    source_dir = aidir.path
    destination_dir = Path(aidir.config.scan_directory_str, "error_temp")
    shutil.copytree(source_dir, destination_dir)
    # check that folder now exists
    assert destination_dir.exists()

    ## self.renaming_to_handled_error()
    ## self.create_error_struct()
    ## self.adjust_rtstruct_dicom_information(error_struct_path)
    ## self.send_struct_to_all_returns(error_struct_path, error=True)
    return


def utest_send_struct_to_all_returns():
    ##self.file_copy_struct(struct_path, return_dir)
    ##self.send_struct(struct_path, return_address)
    ##self.renaming_to_handled_error()
    ##self.delete_sent_folder()
    return

def utest_scan_directory():
    return
def utest_returnservice_worker():
    return
def utest_setup_logging():
    return


def utest_initiate_sending_struct():
    ##self.handle_error()
    ##self.send_struct_to_all_returns(struct_path)
    return



