%function status = writeConfigToAISystem(configInfo, dirPath, configFileName)
%
% Writes AI system configuration information to a file.
%
% Input:
%   configInfo: Structure containing AI configuration information.
%   dirPath: Directory path where the configuration file should be saved.
%   configFileName: Name of the configuration file.
%
% Output:
%   status: Success indicator (1 if successful, 0 if an error occurred).
%
% This function takes AI system configuration information stored in the
% 'configInfo' structure and writes it to a file in the specified directory.
%
% Example:
%   configInfo.ModelName = 'MyModel';
%   configInfo.ModelHash = 'a1b2c3';
%   configInfo.SendDirectory = '/path/to/send';
%   dirPath = '/path/to/config';
%   configFileName = 'config.txt';
%   status = writeConfigToAISystem(configInfo, dirPath, configFileName);
%
% Author: CaB
% Date: 2023-11-15

function status=writeConfigToAISystem(configInfo,dirPath,configFileName)
status=1;
try
  fieldValues=fieldnames( configInfo.configAI);
  fieldValues=setdiff(fieldValues,'SendDirectory');
  fileID=fopen(fullfile(dirPath,configFileName),'w');
  for iFieldName=1:length(fieldValues)
    textLine=[fieldValues{iFieldName},':',configInfo.configAI.(fieldValues{iFieldName})];
    fprintf(fileID,'%s\r\n',textLine);
  end
  fclose(fileID);
catch
  status=0;
end

end