import logging

import pytest
from pathlib import Path
from unittest.mock import Mock

from main import WatchdogConfig, AiSharedDir
from main import AiDir, AiDirState

WATCHDOGCONFIGCONTENT = """savepath_str: '$SAVEPATH$' # Path to save the config file 
logging_format: '[%(asctime)s] %(levelname)-8s %(name)-12s: %(message)s' # Format of the log messages
logging_level_str: '$LOGLEVEL$' # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
logging_dir_str: '$LOGDIR$' # Path to the logging directory
logging_days_to_keep: $LOGDAYS$ # How many days of the logs to keep
scan_directory_str: '$SHAREDDIR$' # Directory to scan for new files
scan_interval: $SCANINTERVAL$ # Seconds between scans
ai_config_filename: '$AICONFIGFILENAME$' # Name of the AI config file
inference_script_path_str: '$INFERENCESCRIPT$' # Path to the inference script
max_restarts: $MAXRESTARTS$ # How many times the inference script can be restarted within a window of max_restart_window_sec seconds
max_restart_window_sec: $MAXRESTARTWINDOW$ # Window in which max_restarts restarts are allowed
dry_run: $DRYRUN$ # If True, the inference script will not be started"""

AICONFIGCONTENT = r'''ModelName:"MyBestProstateModel"
ModelHash:"drhfjkhsdjkfhkjh"
$NICELEVELKEY$:"$NICELEVEL$"
InferenceMaxRunTime:"65"
ReturnDicomNodeIP_1:"10.161.6.246"
ReturnDicomNodePort_1:"104"
ReturnDicomNodeAET_1:"DestinationAET"
ReturnDirectory_1:"\\Rsyd.net\Appl$\_Shared\OUH\Radfys_drift\Klinisk_og_QA_data\BrachyPatientQA\test"
ReturnDicomNodeIP_2:"hostname2"
ReturnDicomNodePort_2:"104"
ReturnDicomNodeAET_2:"DestinationAET2"
ReturnDirectory_2:"L:\AfdR\Radfstrb\ArcCHECK"
EmptyStructWithModelName:"true"
Struct_1:"InterStructName1" "Bladder_AI" "Organ" "[255,0,0]" "2"
Struct_2:"InterStructName2" "Lung_AI" "Organ" "[0,255,0]" "1"
'''


@pytest.fixture(scope='session')
def log_dir_path(tmp_path_factory):
    p = Path(tmp_path_factory.mktemp('logs'))
    p.mkdir(exist_ok=True)
    return p


@pytest.fixture(scope='session')
def shared_dir_path(tmp_path_factory):
    p = Path(tmp_path_factory.mktemp('shared_dir'))
    p.mkdir(exist_ok=True)
    return p


@pytest.fixture(scope='session')
def inference_script_path(tmp_path_factory):
    p = Path(tmp_path_factory.mktemp('scripts'), 'inference_script.py')
    p.touch(exist_ok=True)
    return p


@pytest.fixture(scope='session')
def config_file_path(tmp_path_factory, log_dir_path, shared_dir_path, inference_script_path):
    p = Path(tmp_path_factory.mktemp('config'), 'watchdog_config.yaml')
    p.touch(exist_ok=True)
    return p


@pytest.fixture(scope='session')
def valid_config_file_path(tmp_path_factory, log_dir_path, shared_dir_path, inference_script_path, config_file_path):
    t = WATCHDOGCONFIGCONTENT
    t = t.replace('$SAVEPATH$', str(config_file_path))
    t = t.replace('$LOGLEVEL$', 'DEBUG')
    t = t.replace('$LOGDIR$', str(log_dir_path))
    t = t.replace('$LOGDAYS$', '31')
    t = t.replace('$SHAREDDIR$', str(shared_dir_path))
    t = t.replace('$SCANINTERVAL$', '5')
    t = t.replace('$AICONFIGFILENAME$', 'aiconfig.txt')
    t = t.replace('$INFERENCESCRIPT$', str(inference_script_path))
    t = t.replace('$MAXRESTARTS$', '5')
    t = t.replace('$MAXRESTARTWINDOW$', '360')
    t = t.replace('$DRYRUN$', 'True')
    config_file_path.write_text(t)
    return config_file_path


@pytest.fixture(scope='session')
def valid_active_aidir_path(tmp_path_factory, shared_dir_path):
    # Create AiDir
    p = Path(shared_dir_path, 'active_UID_VALID_1')
    p.mkdir(exist_ok=True)

    # Create aiconfig.txt
    Path(p, 'aiconfig.txt').write_text(
        AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', '1'))
    return p


@pytest.fixture(scope='session')
def valid_ready_aidir_path(tmp_path_factory, shared_dir_path):
    # Create AiDir
    p = Path(shared_dir_path, 'ready_UID_VALID_2')
    p.mkdir(exist_ok=True)

    # Create aiconfig.txt
    Path(p, 'aiconfig.txt').write_text(
        AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', '1'))
    return p


@pytest.fixture(scope='session')
def valid_error_aidir_path(tmp_path_factory, shared_dir_path):
    # Create AiDir
    p = Path(shared_dir_path, 'error_UID_VALID_3')
    p.mkdir(exist_ok=True)

    # Create aiconfig.txt
    Path(p, 'aiconfig.txt').write_text(
        AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', '1'))
    return p


@pytest.fixture(scope='session')
def valid_error_aidir_path_errorfile_exists(tmp_path_factory, shared_dir_path):
    # Create AiDir
    p = Path(shared_dir_path, 'error_UID_VALID_4')
    p.mkdir(exist_ok=True)

    # Create aiconfig.txt
    Path(p, 'aiconfig.txt').write_text(
        AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', '1'))
    Path(p, 'error.txt').write_text('Error')
    return p


@pytest.fixture(scope='session')
def valid_receiving_aidir_path(tmp_path_factory, shared_dir_path):
    # Create AiDir
    p = Path(shared_dir_path, 'receiving_UID_VALID_5')
    p.mkdir(exist_ok=True)

    # Create aiconfig.txt
    Path(p, 'aiconfig.txt').write_text(
        AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', '1'))
    return p


@pytest.fixture(scope='session')
def valid_handled_aidir_path(tmp_path_factory, shared_dir_path):
    # Create AiDir
    p = Path(shared_dir_path, 'handled_UID_VALID_6')
    p.mkdir(exist_ok=True)

    # Create aiconfig.txt
    Path(p, 'aiconfig.txt').write_text(
        AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', '1'))
    return p


@pytest.fixture(scope='session')
def valid_inferred_aidir_path(tmp_path_factory, shared_dir_path):
    # Create AiDir
    p = Path(shared_dir_path, 'inferred_UID_VALID_7')
    p.mkdir(exist_ok=True)

    # Create aiconfig.txt
    Path(p, 'aiconfig.txt').write_text(
        AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', '1'))
    return p


@pytest.fixture(scope='session')
def invalid_aidir_without_aiconfig_path(tmp_path_factory, shared_dir_path):
    # Create AiDir
    p = Path(shared_dir_path, 'active_UID_INVALID_8')
    p.mkdir(exist_ok=True)
    return p


@pytest.fixture(scope='session')
def invalid_active_aidir_path_invalid_nicenesslevel(tmp_path_factory, shared_dir_path):
    # Create AiDir
    p = Path(shared_dir_path, 'active_UID_VALID_1')
    p.mkdir(exist_ok=True)

    # Create aiconfig.txt
    Path(p, 'aiconfig.txt').write_text(
        AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', 'NOTVALID'))
    return p


@pytest.fixture(scope='session')
def invalid_active_aidir_path_invalid_nicenesslevelkey(tmp_path_factory, shared_dir_path):
    # Create AiDir
    p = Path(shared_dir_path, 'active_UID_VALID_1')
    p.mkdir(exist_ok=True)

    # Create aiconfig.txt
    Path(p, 'aiconfig.txt').write_text(
        AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NOTVALID').replace('$NICELEVEL$', '1'))
    return p


@pytest.fixture(scope='session')
def full_test_folder(tmp_path_factory) -> Path:
    """
    Creates a folder structure with all the files needed for a full test
    :param tmp_path_factory:
    :return: Path to the root folder
    """
    root = Path(tmp_path_factory.mktemp('full_test_folder'))
    root.mkdir(exist_ok=True)

    # Create admin folder
    admin = Path(root, 'admin')
    admin.mkdir(exist_ok=True)

    # Create shared folder
    shared = Path(root, 'shared')
    shared.mkdir(exist_ok=True)

    config_file_path = Path(admin, 'watchdog_config.yaml')
    log_dir_path = Path(admin)
    inference_script_path = Path(admin, 'inference_script.py')

    # Create watchdog config in admin folder
    t = WATCHDOGCONFIGCONTENT.replace('$SAVEPATH$', str(config_file_path))
    t = t.replace('$LOGLEVEL$', 'DEBUG')
    t = t.replace('$LOGDIR$', str(log_dir_path))
    t = t.replace('$LOGDAYS$', '31')
    t = t.replace('$SHAREDDIR$', str(shared))
    t = t.replace('$SCANINTERVAL$', '5')
    t = t.replace('$AICONFIGFILENAME$', 'aiconfig.txt')
    t = t.replace('$INFERENCESCRIPT$', str(inference_script_path))
    t = t.replace('$MAXRESTARTS$', '5')
    t = t.replace('$MAXRESTARTWINDOW$', '360')
    t = t.replace('$DRYRUN$', 'True')
    config_file_path.write_text(t)

    # Create inference script in admin folder
    inference_script_path.write_text('print("Hello world")')

    # Create an active aidir in shared folder
    active_aidir = Path(shared, 'active_UID_VALID_1')
    active_aidir.mkdir(exist_ok=True)
    # create aiconfig in active aidir
    Path(active_aidir, 'aiconfig.txt').write_text(AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', '2'))

    # Create a ready aidir in shared folder
    ready_aidir = Path(shared, 'ready_UID_VALID_2')
    ready_aidir.mkdir(exist_ok=True)
    # create aiconfig in ready aidir
    Path(ready_aidir, 'aiconfig.txt').write_text(AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', '1'))

    # Create a ready aidir in shared folder with nicenesslevel 2
    ready_aidir = Path(shared, 'ready_UID_VALID_3')
    ready_aidir.mkdir(exist_ok=True)
    # create aiconfig in ready aidir
    Path(ready_aidir, 'aiconfig.txt').write_text(AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', '1'))

    # Create a ready aidir in shared folder with nicenesslevel 1
    ready_aidir = Path(shared, 'ready_UID_VALID_4')
    ready_aidir.mkdir(exist_ok=True)
    # create aiconfig in ready aidir
    Path(ready_aidir, 'aiconfig.txt').write_text(AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', '1'))

    # Create an error aidir in shared folder
    error_aidir = Path(shared, 'error_UID_VALID_5')
    error_aidir.mkdir(exist_ok=True)
    # create aiconfig in error aidir
    Path(error_aidir, 'aiconfig.txt').write_text(AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', '1'))

    # Create a receiving aidir in shared folder
    receiving_aidir = Path(shared, 'receiving_UID_VALID_6')
    receiving_aidir.mkdir(exist_ok=True)

    # Create a handled aidir in shared folder
    handled_aidir = Path(shared, 'handled_UID_VALID_7')
    handled_aidir.mkdir(exist_ok=True)
    # create aiconfig in handled aidir
    Path(handled_aidir, 'aiconfig.txt').write_text(AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', '1'))

    # Create an inferred aidir in shared folder
    inferred_aidir = Path(shared, 'inferred_UID_VALID_8')
    inferred_aidir.mkdir(exist_ok=True)
    # create aiconfig in inferred aidir
    Path(inferred_aidir, 'aiconfig.txt').write_text(AICONFIGCONTENT.replace('$NICELEVELKEY$', 'NiceLevel').replace('$NICELEVEL$', '1'))

    # Create a ready aidir without aiconfig that should be recognized as invalid
    invalid_aidir = Path(shared, 'ready_UID_INVALID_9')
    invalid_aidir.mkdir(exist_ok=True)

    return root


def test_valid_config(valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    assert watchdog_config.is_valid() is True


def test_invalid_config_paths(valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    watchdog_config.savepath = Path('NOTEXISTING')
    assert watchdog_config.is_valid() is False
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    watchdog_config.logging_dir = Path('NOTEXISTING')
    assert watchdog_config.is_valid() is False
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    watchdog_config.scan_directory = Path('NOTEXISTING')
    assert watchdog_config.is_valid() is False
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    watchdog_config.inference_script_path = Path('NOTEXISTING')
    assert watchdog_config.is_valid() is False


def test_invalid_config_logging_levels(valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    watchdog_config.logging_level = 'NOTEXISTING'
    assert watchdog_config.is_valid() is False
    watchdog_config.logging_level = 17
    assert watchdog_config.is_valid() is False


def test_invalid_config_logging_days(valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    watchdog_config.logging_days_to_keep = 'NOTEXISTING'
    assert watchdog_config.is_valid() is False


def test_invalid_config_scan_intervals(valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    watchdog_config.scan_interval = 'NOTEXISTING'
    assert watchdog_config.is_valid() is False


def test_invalid_config_max_restarts(valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    watchdog_config.max_restarts = 'NOTEXISTING'
    assert watchdog_config.is_valid() is False


def test_invalid_config_max_restart_window(valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    watchdog_config.max_restart_window_sec = 'NOTEXISTING'
    assert watchdog_config.is_valid() is False
    watchdog_config.max_restart_window_sec = 10
    assert watchdog_config.is_valid() is False


def test_invalid_config_dry_run(valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    watchdog_config.dry_run = 'NOTEXISTING'
    assert watchdog_config.is_valid() is False


def test_valid_active_aidir(valid_active_aidir_path, valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    aidir = AiDir(valid_active_aidir_path, watchdog_config)
    aidir.load()
    assert aidir.valid is True


def test_invalid_aidir_without_aiconfig(invalid_aidir_without_aiconfig_path, valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    aidir = AiDir(invalid_aidir_without_aiconfig_path, watchdog_config)
    assert aidir.valid is False, 'Should be invalid here already'
    aidir.load()
    assert aidir.valid is False, 'Should still be invalid'
    aidir.handle_error()
    assert aidir.path.name.startswith('error_') is True, 'Should have been moved to error folder'
    assert aidir.error_file_path.exists() is True, 'Should have an error file'


def test_invalid_active_aidir_invalid_nicenesslevel(invalid_active_aidir_path_invalid_nicenesslevel,
                                                    valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    aidir = AiDir(invalid_active_aidir_path_invalid_nicenesslevel, watchdog_config)
    aidir.load()
    assert aidir.valid, 'The nicenesslevel is invalid, but the aidir should still be valid'
    assert aidir.nicelevel == 10, 'Default to 10 if not found'


def test_invalid_active_aidir_invalid_nicenesslevelkey(invalid_active_aidir_path_invalid_nicenesslevelkey,
                                                       valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    aidir = AiDir(invalid_active_aidir_path_invalid_nicenesslevelkey, watchdog_config)
    aidir.load()
    assert aidir.valid, 'The nicenesslevelkey is invalid, but the aidir should still be valid'
    assert aidir.nicelevel == 10, 'Default to 10 if not found'


def test_valid_active_aidir_state(valid_active_aidir_path, valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    aidir = AiDir(valid_active_aidir_path, watchdog_config)
    assert aidir.state == AiDirState.ACTIVE


def test_valid_ready_aidir_state(valid_ready_aidir_path, valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    aidir = AiDir(valid_ready_aidir_path, watchdog_config)
    assert aidir.state == AiDirState.READY


def test_valid_error_aidir_state(valid_error_aidir_path, valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    aidir = AiDir(valid_error_aidir_path, watchdog_config)
    assert aidir.state == AiDirState.ERROR


def test_valid_receiving_aidir_state(valid_receiving_aidir_path, valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    aidir = AiDir(valid_receiving_aidir_path, watchdog_config)
    assert aidir.state == AiDirState.RECEIVING


def test_valid_handled_aidir_state(valid_handled_aidir_path, valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    aidir = AiDir(valid_handled_aidir_path, watchdog_config)
    assert aidir.state == AiDirState.HANDLED


def test_valid_inferred_aidir_state(valid_inferred_aidir_path, valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    aidir = AiDir(valid_inferred_aidir_path, watchdog_config)
    assert aidir.state == AiDirState.INFERRED


def test_valid_error_aidir_state_errorfile_exists(valid_error_aidir_path_errorfile_exists, valid_config_file_path):
    watchdog_config = WatchdogConfig.load_from_yaml(valid_config_file_path)
    aidir = AiDir(valid_error_aidir_path_errorfile_exists, watchdog_config)
    assert aidir.state == AiDirState.ERROR


def test_AiSharedDir(full_test_folder) -> None:
    """
    Test the AiSharedDir class scanning a directory of aidirs, detecting the different folders in their correct state
    :param full_test_folder: Path to the test folder
    :return: None
    """
    watchdog_config = WatchdogConfig.load_from_yaml(Path(full_test_folder, 'admin', 'watchdog_config.yaml'))
    assert watchdog_config.is_valid(), 'Watchdog config should be valid'

    mock_logger = Mock(spec=logging.Logger)
    shared_dir = AiSharedDir(watchdog_config, mock_logger)
    shared_dir.scan()

    assert shared_dir.has_active(), 'Shared dir should have an active aidir'

    assert shared_dir.has_ready(), 'Shared dir should have at least one ready aidir'
    assert len(shared_dir.ready_dirs) == 4, 'Shared dir should have 4 ready aidirs'
    assert len(shared_dir.active_dirs) == 1, 'Shared dir should have 1 active aidirs'
    assert len(shared_dir.error_dirs) == 1, 'Shared dir should have 1 error aidirs'
    assert len(shared_dir.inferred_dirs) == 1, 'Shared dir should have 1 inferred aidirs'
    assert len(shared_dir.handled_dirs) == 1, 'Shared dir should have 1 handled aidirs'
    assert len(shared_dir.receiving_dirs) == 1, 'Shared dir should have 1 receiving aidirs'

    # rename the active aidir to inferred_UID_VALID_1
    active_aidir = Path(full_test_folder, 'shared', 'active_UID_VALID_1')
    assert active_aidir.exists(), 'Active aidir should exist'
    active_aidir.rename(Path(full_test_folder, 'shared', 'inferred_UID_VALID_1'))

    # New loop, fresh AiSharedDir
    shared_dir = AiSharedDir(watchdog_config, mock_logger)
    shared_dir.scan()

    assert shared_dir.has_active() is False, 'Shared dir should NOT have an active aidir'
    assert len(shared_dir.inferred_dirs) == 2, 'Shared dir should now have 2 inferred aidirs'

    shared_dir.load_ready()
    assert len(shared_dir.ready_dirs) == 3, 'Shared dir should now have 3 ready aidirs, as one is invalid'

    assert shared_dir.has_ready_to_infer(), 'Shared dir should have a ready to infer aidir'
    assert shared_dir.ready_to_infer.path.name == 'ready_UID_VALID_2', 'Shared dir should have a ready to infer aidir with name ready_UID_VALID_2'

    # rename the ready to infer aidir to inferred_UID_VALID_2
    shared_dir.ready_to_infer.path.rename(Path(full_test_folder, 'shared', 'inferred_UID_VALID_2'))

    # New loop, fresh AiSharedDir
    shared_dir = AiSharedDir(watchdog_config, mock_logger)
    shared_dir.scan()

    assert shared_dir.has_active() is False, 'Shared dir should NOT have an active aidir'
    assert len(shared_dir.inferred_dirs) == 3, 'Shared dir should now have 3 inferred aidirs'

    shared_dir.load_ready()
    assert len(shared_dir.ready_dirs) == 2, 'Shared dir should now have 2 ready aidirs, as one is invalid'
