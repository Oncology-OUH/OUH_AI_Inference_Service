%function writeToLog(informationString, configDecisionModule)
%
% Writes information to a log file for the decision module.
%
% Input:
%   informationString: String containing the information to be logged.
%   configDecisionModule: Configuration structure for the decision module.
%                         Requires a field 'pathToLogFilesDir' specifying the
%                         directory where log files are stored.
%
% Output:
%   None.
%
% This function appends the specified information string to a log file
% specific to the decision module. The log file is named based on the current
% date, and it is located in the directory specified by the
% 'pathToLogFilesDir' field in the configuration structure.
%
% Example:
%   informationString = 'Processing completed successfully.';
%   configDecisionModule.pathToLogFilesDir = '/path/to/logs/';
%   writeToLog(informationString, configDecisionModule);
%
% Author: CaB
% Date: 2023-11-15



function writeToLog(informationString,configDecisionModule)
stringDate=char(datetime('today','Format','yyyy_MM_dd'));
logfileName=fullfile(configDecisionModule.pathToLogFilesDir,[stringDate,'_logFileDecisionModule.txt']);
fileID = fopen(logfileName,'a');
stringDate=char(datetime('now','Format','yyyy_MM_dd:HH:mm:ss'));
fprintf(fileID,'%s\r\n',[stringDate,': ',informationString]);
fclose(fileID);
end



