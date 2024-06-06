%function userConfigs = readAllUserConfigFiles(configDir)
%
% Reads all user-defined AI configuration files from the specified directory.
%
% Input:
%   configDir: Path to the directory containing user-defined AI configuration files
%
% Output:
%   userConfigs: Cell array containing parsed AI configuration structures
%
% This function reads all user-defined AI configuration files with the extension
% '.txt' (excluding 'ReadMe.txt') from the specified directory 'configDir'. It
% utilizes the 'aiConfigFileParser' function to parse each file into a
% structured format. The resulting parsed configurations are stored in a cell
% array 'userConfigs'.
%
% Example Usage:
%   configDirectory = '/path/to/configs';
%   allUserConfigs = readAllUserConfigFiles(configDirectory);
%
% Author: CaB
% Date: 2023-11-18


function userConfigs=readAllUserConfigFiles(configDir)
% Check if the specified directory exists
if ~(isfolder(configDir))
  ME.message='Could not access the directory of the user defined Ai config files';
  ME.identifier='MATLAB:mainAiDecisionModule:CouldNotReadUserConfigFile';
  error(ME);
end
% Get all files in the directory
userFiles=dir(configDir);
% Filter files based on the extension and exclude 'ReadMe.txt'
indexUserConfigFiles=cellfun(@(x) endsWith(x,'.txt') && ~strcmpi(x,'ReadMe.txt'),{userFiles.name});
userFiles=userFiles(indexUserConfigFiles);
% Initialize cell array to store parsed configurations
userConfigs=cell(length(userFiles),1);
for iFiles=1:length(userFiles)
  % Full path to the current user config file
  filePath = fullfile(userFiles(iFiles).folder,userFiles(iFiles).name);
  % Parse the configuration file using aiConfigFileParser
  userConfigs{iFiles}=aiConfigFileParser(filePath);
end
end


