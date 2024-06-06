import subprocess
from dataclasses import dataclass
import logging, logging.handlers
import multiprocessing as mp
import time
from datetime import timedelta, datetime
from pathlib import Path
import sys
import yaml
import argparse
from typing import Optional
from enum import Enum


@dataclass
class WatchdogConfig:
    """
    Represents the configuration settings for the watchdog.
    """
    savepath_str: str

    logging_format: str
    logging_level_str: str
    logging_dir_str: str
    logging_days_to_keep: int
    scan_directory_str: str
    scan_interval: int
    ai_config_filename: str
    inference_script_path_str: str
    max_restarts: int
    max_restart_window_sec: int
    dry_run: bool

    def is_valid(self) -> bool:
        """
        Indicates whether the configuration file is valid.
        :return: bool
        """
        if not self.test_paths():
            return False
        if not self.test_values():
            return False
        return True

    def is_invalid(self):
        """
        Indicates whether the configuration file is invalid.
        :return: bool
        """
        return not self.is_valid()

    def test_values(self) -> bool:
        """
        Tests whether the values in the configuration file are valid.
        :return: bool
        """
        if not isinstance(self.scan_interval, int):
            return False
        if not isinstance(self.max_restarts, int):
            return False
        if not isinstance(self.max_restart_window_sec, int):
            return False
        if not isinstance(self.logging_format, str):
            return False
        if not isinstance(self.logging_days_to_keep, int):
            return False
        if not isinstance(self.ai_config_filename, str):
            return False
        if self.ai_config_filename and len(self.ai_config_filename) < 1:
            return False
        if not 1 <= self.scan_interval < 60:
            return False
        if self.max_restarts < 1:
            return False
        if self.max_restart_window_sec < 60:
            return False
        if self.logging_level_str not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            return False
        if not isinstance(self.dry_run, bool):
            return False

        return True

    def test_paths(self) -> bool:
        """
        Tests whether the paths in the configuration file are valid.
        :return: bool
        """
        try:
            if not self.savepath.exists() or not self.scan_directory.exists() or not self.inference_script_path.exists() or not self.logging_dir.exists():
                return False
            if not self.savepath.is_file() or not self.scan_directory.is_dir() or not self.inference_script_path.is_file() or not self.logging_dir.is_dir():
                return False
        except (FileNotFoundError, PermissionError):
            return False
        return True

    @staticmethod
    def read_yaml_data(filepath: Path) -> Optional[dict]:
        """
        Reads a YAML file and returns the data as a dictionary.
        If the YAML file contains invalid syntax, logs an error and returns None.

        Args:
            filepath (Path): The path to the YAML file.

        Returns:
            Optional[dict]: The data from the YAML file or None if an error occurs.
        """
        try:
            with filepath.open('r') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            logging.error(f"Error reading YAML file at {filepath}: {e}")
            return None

    @classmethod
    def from_dict(cls, data: dict) -> 'WatchdogConfig':
        """
        Creates a WatchdogConfig instance from a dictionary.

        Args:
            data (dict): The data to create a WatchdogConfig instance from.

        Returns:
            WatchdogConfig: The created WatchdogConfig instance.
        """
        return cls(**data)

    @classmethod
    def load_from_yaml(cls, filepath: Path) -> 'WatchdogConfig':
        """
        Loads a WatchdogConfig instance from a YAML file.
        :param filepath: Path to the YAML file.
        :return: WatchdogConfig
        """
        data = cls.read_yaml_data(filepath)
        return cls.from_dict(data)

    def save_to_yaml(self, filepath: Optional[Path] = None) -> None:
        """
        Saves the WatchdogConfig instance to a YAML file.
        :param filepath: Path to the YAML file.
        :return: None
        """
        if not filepath:
            filepath = self.savepath
        with filepath.open('w') as f:
            yaml.dump(self.__dict__, f)

    @property
    def logging_dir(self) -> Path:
        """
        The path to the logging file.
        :return: Path
        """
        return Path(self.logging_dir_str)

    @logging_dir.setter
    def logging_dir(self, value: Path) -> None:
        """
        Sets the path to the logging file.
        :param value: Path to the logging file.
        :return: None
        """
        self.logging_dir_str = str(value)

    @property
    def logging_level(self) -> int:
        """
        The logging level.
        :return: Logging level
        """
        return getattr(logging, self.logging_level_str)

    @logging_level.setter
    def logging_level(self, value: int) -> None:
        """
        Sets the logging level.
        :param value: Logging level
        :return: None
        """
        self.logging_level_str = logging.getLevelName(value)

    @property
    def max_restart_window(self) -> timedelta:
        """
        The maximum restart window.
        :return: timedelta
        """
        return timedelta(seconds=self.max_restart_window_sec)

    @max_restart_window.setter
    def max_restart_window(self, value: timedelta) -> None:
        """
        Sets the maximum restart window.
        :param value: Time delta
        :return: None
        """
        self.max_restart_window_sec = int(value.seconds)

    @property
    def savepath(self) -> Path:
        """
        The path to the configuration file.
        :return: Path
        """
        return Path(self.savepath_str)

    @savepath.setter
    def savepath(self, value: Path) -> None:
        """
        Sets the path to the configuration file.
        :param value: Path to the configuration file.
        :return: None
        """
        self.savepath_str = str(value)

    @property
    def inference_script_path(self) -> Path:
        """
        The path to the inference script.
        :return: Path
        """
        return Path(self.inference_script_path_str)

    @inference_script_path.setter
    def inference_script_path(self, value: Path) -> None:
        """
        Sets the path to the inference script.
        :param value: Path to the inference script.
        :return: None
        """
        self.inference_script_path_str = str(value)

    @property
    def scan_directory(self) -> Path:
        """
        The path to the directory to scan for AI directories.
        :return: Path
        """
        return Path(self.scan_directory_str)

    @scan_directory.setter
    def scan_directory(self, value: Path) -> None:
        """
        Sets the path to the directory to scan for AI directories.
        :param value: Path to the directory to scan for AI directories.
        :return: None
        """
        self.scan_directory_str = str(value)


class AiDirState(Enum):
    """
    Represents the state of an AI directory.
    """
    ACTIVE = 'active'
    READY = 'ready'
    ERROR = 'error'
    RECEIVING = 'receiving'
    HANDLED = 'handled'
    INFERRED = 'inferred'
    UNKNOWN = 'unknown'


@dataclass
class AiDir:
    """
    Represents a directory containing files and configurations for inference.

    Attributes:
        path (Path): Required. The file system path to the directory.
        config (WatchdogConfig): Required. The configuration settings for the watchdog.
        nicelevel (int): The priority level for processing the directory.
        last_modified (str): The last modification time of the directory.
        valid (bool): Indicates whether the directory is valid for processing.
        ai_config_path (Path): The path to the AI configuration file.
        error (str): The error message if the directory is invalid.
        write_error_to_file (bool): Indicates whether to write the error message to a file.
        state (AiDirState): The state of the directory.
    """
    path: Path
    config: WatchdogConfig

    nicelevel: int = None
    last_modified = None
    valid: bool = False
    ai_config_path: Path = None
    error: str = None
    write_error_to_file: bool = True
    error_file_path: Path = None
    state: AiDirState = None

    def __post_init__(self) -> None:
        """
        Post-initialization processing to set up additional attributes and logging.
        """
        self.ai_config_path = Path(self.path, self.config.ai_config_filename)

        self.error_file_path = Path(self.path, 'error.txt')

        if self.error_file_path.exists():
            self.state = AiDirState.ERROR  # Can happen if the folder could not be renamed
        elif self.path.name.lower().startswith('active_'):
            self.state = AiDirState.ACTIVE
        elif self.path.name.lower().startswith('ready_'):
            self.state = AiDirState.READY
        elif self.path.name.lower().startswith('error_'):
            self.state = AiDirState.ERROR
        elif self.path.name.lower().startswith('receiving_'):
            self.state = AiDirState.RECEIVING
        elif self.path.name.lower().startswith('handled_'):
            self.state = AiDirState.HANDLED
        elif self.path.name.lower().startswith('inferred_'):
            self.state = AiDirState.INFERRED
        else:
            self.state = AiDirState.UNKNOWN

        self.log = logging.getLogger(__class__.__name__)

        self.pre_validate()

    def activate(self) -> bool:
        """
        Activates the AI directory by renaming it with an 'active_' prefix.

        Returns:
            bool: True if the activation was successful, False otherwise.
        """
        new_path = Path(self.path.parent, f'active_{self.path.name.replace("ready_", "")}')
        self.log.debug(f'Renaming {self.path} to active_{new_path}')
        return self.rename(new_path)

    def rename(self, new_name: Path) -> bool:
        """
        Renames the AI directory.

        Args:
            new_name (str): The new name for the directory.

        Returns:
            bool: True if the rename was successful, False otherwise.
        """
        try:
            self.path.rename(new_name)
        except (PermissionError, OSError, FileExistsError) as ex:
            self.log.error(f'Could not rename directory: {ex}')
            self.error = f'E2_01 Could not rename directory'
            self.state = AiDirState.ERROR
            return False

        self.path = new_name
        self.error_file_path = Path(self.path, 'error.txt')
        self.ai_config_path = Path(self.path, self.config.ai_config_filename)
        return True

    def is_valid(self) -> bool:
        """
        Indicates whether the AI directory is valid for processing.
        :return: bool
        """
        return self.valid

    def is_active(self) -> bool:
        """
        Indicates whether the AI directory is active.
        :return: bool
        """
        return self.state == AiDirState.ACTIVE

    def is_ready(self) -> bool:
        """
        Indicates whether the AI directory is ready.
        :return: bool
        """
        return self.state == AiDirState.READY

    def is_error(self) -> bool:
        """
        Indicates whether the AI directory is in an error state.
        :return: bool
        """
        return self.state == AiDirState.ERROR

    def pre_validate(self) -> None:
        """
        Validates the AI directory before loading it.
        :return: None
        """
        if self.path.exists() is False:
            self.error = f'Path does not exist: {self.path}'
            self.log.error(self.error)
            self.valid = False
            self.write_error_to_file = False
            return

        if self.state == AiDirState.ERROR:
            self.valid = False
            return

        if self.state == AiDirState.UNKNOWN:
            self.valid = False
            self.write_error_to_file = False
            return

        if self.state == AiDirState.RECEIVING:
            self.valid = False
            self.write_error_to_file = False
            return

        if self.ai_config_path.exists() is False:
            self.error = f'E2_02 AI config file does not exist.'
            self.log.error(self.error)
            self.valid = False
            self.write_error_to_file = True
            return
        
        self.valid = True

    def load(self) -> None:
        """
        Loads the AI directory configuration and validates its.
        :return: None
        """

        if self.valid is False:
            return

        try:
            with open(self.ai_config_path) as file:
                for line in file:
                    if line.strip().lower().startswith('nicelevel'):
                        self.nicelevel = int(line.split('"')[1])
        except ValueError:
            self.log.error(f'Could not parse nicelevel')

        if self.nicelevel is None:
            self.nicelevel = 10
            self.log.error('Could not find nicelevel in config file. Using default value of 10.')

        self.last_modified = time.ctime(self.path.stat().st_mtime)

        self.valid = True

    def handle_error(self) -> None:
        """
        Handles an error by writing it to a file if configured to do so, and renames the directory to 'error_'.
        :return: None
        """
        if self.write_error_to_file:
            self.error_file_path.write_text(self.error)

        self.log.info(f'Renaming {self.path} to error_{self.path.name}')
        new_path = Path(self.path.parent, f'error_{self.path.name.replace("ready_", "")}')
        if self.rename(new_path) is False:
            # Force write error to file so the folder will be picked as an error folder next rounds
            self.error_file_path.write_text(self.error)


class AiSharedDir:
    """
    Represents a directory containing files and configurations for inference.
    """
    config: WatchdogConfig
    log: logging.Logger

    path: Path = None

    receiving_dirs: list[AiDir] = []
    ready_dirs: list[AiDir] = []
    active_dirs: list[AiDir] = []
    error_dirs: list[AiDir] = []
    handled_dirs: list[AiDir] = []
    inferred_dirs: list[AiDir] = []
    unknown_dirs: list[AiDir] = []

    ready_to_infer: AiDir = None

    def __init__(self, config: WatchdogConfig, logg: logging.Logger):
        """
        Initializes the AiSharedDir instance.
        :param config: WatchdogConfig: The configuration settings for the watchdog.
        :param logg: Logger
        """
        self.config = config
        self.log = logg

        self.receiving_dirs = []
        self.ready_dirs = []
        self.active_dirs = []
        self.error_dirs = []
        self.handled_dirs = []
        self.inferred_dirs = []
        self.unknown_dirs = []

        self.path = self.config.scan_directory

    def scan(self) -> None:
        """
        Scans the directory for AI directories and sorts them into lists based on their state.
        """
        for f in self.path.iterdir():
            if f.is_dir():
                d = AiDir(f, config=self.config)
                if d.state == AiDirState.RECEIVING:
                    self.log.debug(f'Found receiving folder: {d.path}')
                    self.receiving_dirs.append(d)
                elif d.state == AiDirState.READY:
                    self.log.debug(f'Found ready folder: {d.path}')
                    self.ready_dirs.append(d)
                elif d.state == AiDirState.ACTIVE:
                    self.log.debug(f'Found active folder: {d.path}')
                    self.active_dirs.append(d)
                elif d.state == AiDirState.ERROR:
                    self.log.debug(f'Found error folder: {d.path}')
                    self.error_dirs.append(d)
                elif d.state == AiDirState.HANDLED:
                    self.log.debug(f'Found handled folder: {d.path}')
                    self.handled_dirs.append(d)
                elif d.state == AiDirState.INFERRED:
                    self.log.debug(f'Found inferred folder: {d.path}')
                    self.inferred_dirs.append(d)
                elif d.state == AiDirState.UNKNOWN:
                    self.log.debug(f'Found unknown folder: {d.path}')
                    self.unknown_dirs.append(d)

    def load_ready(self) -> None:
        """
        Loads the ready directories and validates them.
        """
        self.log.debug(f'Loading ready directories')
        really_ready = []
        for d in self.ready_dirs:
            d.load()
            if d.is_valid() and d.is_ready():
                self.log.debug(f'Found valid ready directory: {d.path}')
                really_ready.append(d)
            else:
                self.log.error(f'Invalid ready directory: {d.path}')
                d.handle_error()
                self.error_dirs.append(d)
        self.ready_dirs = really_ready

        if self.has_ready():
            self.ready_to_infer = sorted(self.ready_dirs, key=lambda x: (x.nicelevel, x.last_modified))[0]

    def has_ready_to_infer(self) -> bool:
        """
        Indicates whether there is a directory ready to be inferred.
        :return: bool
        """
        return self.ready_to_infer is not None

    def has_active(self) -> bool:
        """
        Indicates whether there is an active directory.
        :return: bool
        """
        return len(self.active_dirs) > 0

    def has_no_active(self) -> bool:
        """
        Indicates whether there are no active directories.
        :return: bool
        """
        return len(self.active_dirs) == 0

    def has_ready(self) -> bool:
        """
        Indicates whether there are ready directories.
        :return: bool
        """
        return len(self.ready_dirs) > 0


def watchdog_worker(config: WatchdogConfig, my_stop_event: mp.Event, my_busy_event: mp.Event) -> None:
    """
    The worker function for the watchdog process that scans directories and processes them.

    This function runs in a separate process and continuously monitors a directory for new
    'ready_' directories to process. When a 'ready_' directory is found, it is renamed to
    'active_' and an inference script is run on it.

    Arguments:
        :param config: The configuration object containing settings for the watchdog.
        :param my_stop_event: An event to signal the process to stop running.
        :param my_busy_event: An event to signal the main process that the worker is busy.
    """
    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format,
        handlers=[
            logging.handlers.TimedRotatingFileHandler(
                filename=Path(config.logging_dir, 'watchdog_worker.log'), when='midnight', interval=1,
                backupCount=config.logging_days_to_keep),
            logging.StreamHandler()
        ]
    )
    log = logging.getLogger('Watchdog Worker')
    log.info('Starting watchdog worker')
    last_loop = time.time() - config.scan_interval  # Kick off right away
    try:
        while not my_stop_event.is_set():
            if time.time() - last_loop >= config.scan_interval:
                my_busy_event.set()  # Comunicate to the main process that we are busy
                last_loop = time.time()
                log.debug('Scanning directory')

                d = AiSharedDir(config, log)
                d.scan()

                if d.has_active():
                    log.debug('Active folder found. Nothing to do.')
                    continue

                if d.has_no_active():
                    if d.has_ready():
                        d.load_ready()  # Load the ready directories to get their nicelevel, and handle errors
                        if d.has_ready_to_infer():
                            log.info(f'Processing: {d.ready_to_infer.path}')
                            if d.ready_to_infer.activate():  # Activate the directory
                                python_executable = sys.executable  # This is the path to the python executable that is running this script
                                command = [python_executable, str(config.inference_script_path), '--folder',
                                           str(d.ready_to_infer.path)]
                                if config.dry_run:
                                    log.info(f'Dry run: {command}')
                                else:
                                    log.debug(f'Running command: {command}')
                                    subprocess.Popen(command, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
                            else:
                                log.error(f'Could not activate directory: {d.ready_to_infer.path}')
                                d.ready_to_infer.handle_error()
                my_busy_event.clear()  # Comunicate to the main process that we are done
            time.sleep(0.5)


    except KeyboardInterrupt:
        my_busy_event.clear()
        log.info('KeyboardInterrupt: stopping')
        return None
    except Exception as ex:
        my_busy_event.clear()
        log.error(f'Error in runner: {ex}')
    log.info('Done')


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, required=True, help='Path to config file')
    args = parser.parse_args()

    configpath = None
    if args.config:
        configpath = Path(args.config.strip())

    try:
        watchdog_config = WatchdogConfig.load_from_yaml(configpath)
    except (FileNotFoundError, PermissionError) as e:
        sys.exit(f'Could not read config file: {e}')

    if watchdog_config is None:
        sys.exit(f'Config file not valid YAML: {configpath}')

    if watchdog_config.is_invalid():
        sys.exit(f'Config is not valid: {watchdog_config}')

    logging.basicConfig(
        level=watchdog_config.logging_level,
        format=watchdog_config.logging_format,
        handlers=[
            logging.handlers.TimedRotatingFileHandler(
                filename=Path(watchdog_config.logging_dir, 'watchdog_main.log'), when='midnight', interval=1,
                backupCount=watchdog_config.logging_days_to_keep),
            logging.StreamHandler()
        ]
    )
    log = logging.getLogger('Watchdog')

    log.info(f'Watchdog started.')
    log.info(f'Config: {watchdog_config}')

    log.debug(f'Setting up worker')

    stop_event = mp.Event()
    busy_event = mp.Event()
    restarts = []
    worker_task = mp.Process(target=watchdog_worker, args=(watchdog_config, stop_event, busy_event))
    worker_task.start()

    try:
        while True:
            if worker_task is None or not worker_task.is_alive():

                current_time = datetime.now()

                # Clean up, keep only recent restarts
                restarts = [restart_time for restart_time in restarts if
                            current_time - restart_time < watchdog_config.max_restart_window]

                if len(restarts) >= watchdog_config.max_restarts:
                    log.error('Maximum worker restarts reached within time window. Shutting down.')
                    break

                if worker_task is not None:
                    log.error('Worker has stopped unexpectedly. Attempting to restart.')
                    worker_task.join()  # Ensure the old process resources are cleaned up

                restarts.append(current_time)

                # Calculate the backoff time, 2,4,8,16,32,60 seconds.
                backoff_time = min(2 ** len(restarts), 60)  # Exponential backoff capped at 60 seconds
                log.info(f'Waiting for {backoff_time} seconds before restarting worker.')
                time.sleep(backoff_time)

                log.info('Starting new worker task.')
                worker_task = mp.Process(target=watchdog_worker, args=(watchdog_config, stop_event, busy_event))
                worker_task.start()

            time.sleep(1)

    except KeyboardInterrupt:
        log.info('KeyboardInterrupt: stopping')
        if busy_event.is_set():  # If the worker is busy, wait for it to finish
            log.info('Waiting for worker to finish')
            busy_event.wait(timeout=500)
        stop_event.set()
        if worker_task is not None:
            worker_task.join()
        exit(0)
    finally:
        stop_event.set()
        if worker_task is not None:
            worker_task.join()
