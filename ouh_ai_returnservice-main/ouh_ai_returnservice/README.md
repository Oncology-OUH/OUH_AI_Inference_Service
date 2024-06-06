# ouh_ai_returnservice

## Purpose

ouh_ai_returnservice scans a directory for folders that have been through the AI inference process and sends the resulting RTStruct where specified in an AI config file in said folder. It also reports any critical errors back to the user by sending an empty RTStruct with an error code as its name. 

## To run the code

In order to run the code, the path to the config file described under Input needs to be indicated. 
Note that C:\path\to\config.json is a placeholder for the actual path in the following

### In Pycharm

Click on Select Run/Debug Configuration-> Edit Configurations... and then add --config C:\path\to\config under Parameters

### In the terminal

Python main.py --config C:\path\to\config.json

## Input

A valid config file of .json format containing the following:

- `savepath_str`: The save path of the config file to be used as input (string) 
- `scan_directory_str`: The path to the shared directory where the program looks for folders to process (string) 
- `logging_format_str`: Logging format of the logger (string) 
- `logging_level_str`: Logging level of the logger. Must be either "DEBUG", "INFO", "WARNING", "ERROR", or "CRITICAL" (string) 
- `logging_level_pynetdicom_str`: Logging level when transferring data through the DICOM protocol (string)
- `logpath_str`: The save path of the logging files (string) 
- `ai_config_filename`: The name of the AI config file (string) 
- `error_file`: The name of the error file that has been created if an error has been encountered (string) 
- `ae_title`: The AE title for sending DICOM data to a DICOM receiver (string) 
- `return_dicom_str`: Parsing string for identifying return DICOM node (string) 
- `return_directory_str`: Parsing string for identifying return directory (string) 
- `scan_interval_sec`: The scan interval in seconds, i.e. how often the service should scan the directory for folders of interest (integer) 
- `max_restarts`: The maximal number of restarts allowed within a time window before the program is terminated (integer) 
- `max_restart_window_sec`: The time window within which the program may attempt restarts (integer) 
- `days_before_deletion`: The number of days the log files and "handled_error_" folders are kept before deletion (integer) 
- `archive_directory_str`: The path to the archive directory.
- `do_archive`: Boolean indicating whether to archive the rtstruct.


Folders are expected to be formatted to at least include the following:

```
|__error_UID/
    |-- dcminput/
    |    |-- file1.dcm
    |    |-- file2.dcm
    |    |__ ...
    |
    |-- aiconfig.txt
    |__ error.txt

|__inferred_UID/
    |-- dcmoutput/
    |    |__ rtstruct.dcm
    |
    |__ aiconfig.txt
```

## Output

A folder is deleted or renamed. An RTStruct is sent to one or more directories and/or DICOM receivers.

### Archiving

As we would like to archive all rtsruct files along with the aiconfig.txt used to generate them, we have implemented an archiving feature. If the do_archive flag is set to true, the service will archive the rtstruct and aiconfig.txt files in the archive directory. The archive directory is specified in the config file.

### Logging

Two logs are generated for logging output. One for the worker process and one for the main process. A new log is created each day, and a maximum of 30 logs (configurable) are kept for each process.
In the configuration file, you can specify the logging level, the path to the file where the logs will be and how many days of logs to keep.

The return service creates two log files:
- The main log (`returnservice_Main.log`) which logs the management of the worker process.
- The worker log (`returnservice_Worker.log`) which logs all the actual work of the service.

You can use any text editor to view the log file.

### Logging levels

For normal usage, the logging level `INFO` is recommended for the main logging. The library pynetdicom gives a lot of logging output at the "INFO" level, and it is therefore recommended to use the "WARNING" level instead for this (i.e. 'logging_level_pynetdicom_str') when not debugging in order to make the log more readable (string).

### Log rotation

Every midnight, the logs rotate and the old logs are renamed with a date reflecting when the log was created, and a new log is created.

## Functionality

The return service scans the shared directory for three types of folders;  

- Those that have been inferred and thus have the prefix "inferred_" in the name 
- Those that have encountered an error and thus have the prefix "error_" in the name  
- Those that have been through error handling and thus have the prefix "handled_error_" in the name 

The functionality can be divided into two main flows: inferred flow and error flow. Both flows start with a validating check, to ensure that the folder contains two necessary key elements:  
- The AI config file  
- At least one return address within the AI config file 

If either is missing, the folder is renamed to "handled_error_" and an error is reported in the log. 

### Inferred flow

When the service has identified a folder with the prefix "inferred_", the inferred flow is initiated with an additional check for the following: 
- A folder called dcmoutput 
- A single RTStruct within the dcmoutput folder 

If either is missing, or more than one RTStruct is identified, the error flow is initiated. Otherwise, the RTStruct is sent to any return address (this can be a directory as well as a DICOM node) indicated in the AI config file, and the folder is then deleted. If the bool "SendScan" is set to true in the AI config file, the scan used for inference is also forwarded. If an error occurs when sending the RTStruct and/or scan, the folder is renamed to "handled_error" instead of deletion, and the error is reported in the log file. 

### Error flow

When the service has identified a folder with the prefix "error_", the error flow is initiated. The error flow starts with an additional check for the following: 
- A folder called dcminput 
- DCM files inside the dcminput folder 
- An error file 
- An error message within the error file 

If either is missing, the folder is renamed to "handled_error", and the error is reported in the log file. Otherwise, the error message is extracted from the error file and stored in an empty RTStruct, which is then sent to any return address indicated in the AI config file. The folder is then renamed to "handled_error_". 

When the service has identified a folder with the prefix "handled_error_", it checks how old the folder is. If the folder is older than 30 days (configurable), it is deleted. 

 