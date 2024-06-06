# OUH AI Watchdog

## Table of Contents
- [Introduction](#introduction)
  - [Expected functionality](#expected-functionality)
- [Requirements](#requirements)
- [Configuration](#configuration)
- [Logging](#logging)
- [Usage](#usage)
  - [Manual running in a terminal for testing](#manual-running-in-a-terminal-for-testing)
  - [Running as a Windows service](#running-as-a-windows-service)
  - [Editing the service](#editing-the-service)
- [Troubleshooting](#troubleshooting)
  - [General troubleshooting](#general-troubleshooting)
  - [Service not starting](#service-not-starting)
  - [A folder is not being inferred even though its name starts with ready](#a-folder-is-not-being-inferred-even-though-its-name-starts-with-ready)

## Introduction
ouh_ai_watchdog is a watchdog service designed to monitor a directory for new files and automatically trigger AI inference processes. It ensures that the AI inference scripts are executed as new data becomes available, and it ensures only one inference process is running.

### Expected functionality
The service works continually and scans a directory for folders. It will scan folders for an aiconfig.txt in which it will find a NiceLevel number to use for ranking folders ready to be inferred. The service will then pick the oldest folder of the folders with the lowest NiceLevel number. The picked folder will be renamed to start with "active_" and sent to the AI inference script. The service will then go back to scanning the directory for new folders.

1. The service scans a directory for folders.
2. If there is a folder that starts with "active_", the service will not do anything until next scan.
3. If there is one, or more, "ready_" folders, the service will pick the oldest of them with the lowest NiceLevel number.
   1. The picked folder will be renamed to start with "active_" and sent to the AI inference script.
4. Start the scan again.

## Requirements
Before installing and running ouh_ai_watchdog, ensure that your system meets the following requirements:

- Python 3.6 or higher
- Required Python packages: `subprocess`, `dataclasses`, `logging`, `multiprocessing`, `time`, `datetime`, `pathlib`, `sys`, `yaml`, `argparse`, `typing`, `enum`
- A YAML configuration file following the provided template

## Configuration
To configure ouh_ai_watchdog, you will need to create a YAML configuration file that specifies various parameters such as the directory to monitor, logging settings, and the AI inference script to execute. An example configuration file is provided (`watchdog_config_example.yaml`). Copy this file to a desired location, rename it to `watchdog_config.yaml`, and update the settings to match your environment.

The configuration file contains the following options:

- `savepath_str`: The path where the configuration file will be saved.
- `logging_format`: The format of the log messages.
- `logging_level_str`: The logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL).
- `logging_dir_str`: Path to the logging directory.
- `logging_days_to_keep`: How many days of the logs to keep. The logs rotate at midnight.
- `scan_directory_str`: The directory to scan for new files.
- `scan_interval`: The number of seconds between each scan for new files.
- `ai_config_filename`: The name of the AI configuration file.
- `inference_script_path_str`: The path to the inference script.
- `max_restarts`: The maximum number of times the inference script can be restarted within a specified time window.
- `max_restart_window_sec`: The time window in seconds during which the maximum number of restarts is counted.
- `dry_run`: If set to True, the inference script will not be started. This is useful for testing the configuration without running the actual inference process.

For detailed configuration options, please refer to the comments within the example configuration file.

## Logging
In the configuration file, you can specify the logging level, the path to the file where the logs will be and how many days of logs to keep.

The Watchdog service creates two log files as the service consists of two processes:
- The main log (`watchdog_main.log`) which should be small as it only logs the management of the worker process.
- The worker log (`watchdog_worker.log`) which logs all the actual work of the service.

You can use any text editor to view the log file. A good log-viewer application is [Bare Tails](https://baremetalsoft.com/baretail/). It's small, requires no installation and have live updating of the logs.

### Logging levels
In normal usage loglevel `INFO` should be enough. It only shows highlights of problemfree executions and any errors.

If debugging of the live system is needed, loglevel `DEBUG` can be used for to gather much larger amounts of information. Do remember to set the level back to `INFO` after debugging is over, otherwise the log files will grow quite large.

### Log rotation
Every midnight the logs rotate and the old logs are moved to a file with a date in the name and a new logfile is started.
The number of old logs to keep can be set in the configuration. Logs older than that is deleted.

## Usage
The service can be run manually in a terminal for testing, or it can be run as a Windows service.

### Manual running in a terminal for testing
To run the ouh_ai_watchdog service manually, you can use the provided `run.bat` batch file. This file contains the necessary commands to start the service with the correct environment and configuration. Here are the steps to run the service:

1. Open a command prompt window.
2. Navigate to the directory where `run.bat` is located.
3. Execute the batch file by typing `run.bat` and pressing Enter.

The service will start and begin monitoring the specified directory for new files to process.

Make sure that the paths in `run.bat` are correctly set to match your environment before running the batch file.

### Running as a Windows service
The easiest way to run ouh_ai_watchdog as a Windows service is to use the [NSSM](https://nssm.cc/) utility. NSSM allows you to run any executable as a Windows service. Here are the steps to run the service:

1. Download the latest release of NSSM from the [NSSM website](https://nssm.cc/download).
2. Extract the downloaded ZIP file to a desired location.
3. Open a command prompt window.
4. Navigate to the directory where NSSM was extracted.
5. Execute the following command to install the service:

    `nssm install ouh_ai_watchdog`
6. In the NSSM window that appears, enter the following information:

    - Path: The full path to `conda.bat` (e.g. `C:\Users\ybs4hy\AppData\Local\miniconda3\condabin\conda.bat`)
    - Startup directory: The directory where `run.bat` is located.
    - Arguments: 'run -n PYTHON_ENVIRONMENT_NAME python OUH_AI_WATHCDOG_PYTHON_SCRIPT --config CONFIG_FILE_PATH
      - PYTHON_ENVIRONMENT_NAME: The name of the Python environment where ouh_ai_watchdog is installed.
      - OUH_AI_WATHCDOG_PYTHON_SCRIPT: The full path to `main.py` (e.g. `C:\Users\USER\Documents\ouh-ai-watchdog\main.py`)
      - CONFIG_FILE_PATH: The full path to the YAML configuration file (e.g. `C:\Users\USER\Documents\watchdog_config.yaml`)
    - Display name: AI Watchdog
    - Description: Service for managing queue of AI inference processes
    - Startup type: Automatic
    - Logon: Local system account
    - Click Install service

The service will now be installed and will start automatically. You can view the service in the Windows Services window.

### Editing the service
Editing the service can be done by using NSSM as well.

1. Open a command prompt window.
2. Navigate to the directory where NSSM was extracted.
3. Execute the following command to edit the service:

    `nssm edit ouh_ai_watchdog`
4. In the NSSM window that appears, edit the desired settings.
5. Click Update service.

The service will now be updated and will restart automatically.

## Troubleshooting

### General troubleshooting
- Ensure the configuration file is correctly configured.
- Ensure the logging file path is correctly configured.
- Ensure the scan directory path is correctly configured.
- Ensure the inference script path is correctly configured.
- Ensure all the above paths exist and are readable and writable by the service.

### Service not starting
Try running the service manually by following the steps in the [Manual running in a terminal for testing](#manual-running-in-a-terminal-for-testing) section. If the service starts successfully, then the problem is likely related to the NSSM configuration. Try reinstalling the service by following the steps in the [Running as a Windows service](#running-as-a-windows-service) section.
If it does not start succesfully then the problem is likely related to the configuration file. If there is not enough information to fix the error in the output, try setting the logging level to DEBUG in the configuration file and run the service again. This will provide more detailed information in the log file.
Don't forget to set the logging level back to the desired level after troubleshooting. Otherwise, the log file will grow very large.

### A folder is not being inferred even though its name starts with ready
If there is a file called error.txt in the folder, the folder will not be inferred. This is to prevent the service from trying to infer a folder that has some error during processing. If you want to re-infer a folder, delete the error.txt file and the folder will be inferred again.

