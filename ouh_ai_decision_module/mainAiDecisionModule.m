%function mainAiDecisionModule()
%
% Summary:
%   This script serves as the main entry point for the AI decision module. It
%   integrates various functions for querying a Mungo database, reading AI
%   configuration files, checking trigger conditions for DICOM series, and copying
%   files to the AI system.
%   The function is aimed to be used as an Matlab extension to MIM
%   software.
%
% Input:
%   None directly. All the communication between MIM and Matlab is
%   documented in the function getAllDicomDataForSeries. Furthermore,
%   database queries to the MIM database are used. The function
%   mimDataBaseQuery handles these queries.
%
% Output:
%   None directly. Copying data to the AI system if they meet the
%   constrains determined within the user config files
%
% Details:
%   The function need a local config file named configAiDecisionModule.txt.
%   When the program is called from within MIM, the first step is that MIM
%   launches Matlab (behind the scenes) and then executes the current
%   program within that Matlab instance. Thus, the working directory for
%   the current file is likely a directory within the Matlab installation
%   files, such as e.g. C:\Program\Files\MATLAB\R2022b\bin\win64. Thus, the
%   local config file configAiDecisionModule.txt should be placed in that
%   directory. The specific working directory and username can be obtained
%   by running from MIM a small Matlab script such as:
%
%   workingDir=pwd;
%   save('SomeFullPath\workingDir.mat','workingDir');
%   username=getenv('username');
%   save('SomeFullPath\username.mat','username');
%
%   the saved variables can then be read by Matlab afterwards.
%
%   An example config file could be as follows: 
%
%   #Location of the config files that describe the rules for the individual models
%     pathToUserConfigFiles:"C:\MIM_scripting_matlab\UserAiConfigFiles"
%   #Information about the Mungo database and where mungosh is installed
%     ip:"127.0.0.1"
%     port: "34543"
%     dataBaseName: "metabase_v2"
%     fileNameForMongosh: "C:\MIM_scripting_matlab\mongosh-2.0.2-win32-x64\bin\mongosh"
%   #Postion of log files for the AI decision module
%     pathToLogFilesDir:"C:\MIM_scripting_matlab\LogFilesAIDecisionModule"
%     daysToKeepLogFiles:"30"
%   #The patient folder number in which the AI system stored the patient data
%     mimPatientListNumber : "10"
%
%
% Author: CaB
% Date: 2023-11-16

function mainAiDecisionModule()
%The working directory when executed from MIM is likely C:\Program
%Files\MATLAB\R2022b\bin\win64, thus the local config file for the current
%program (not the user config files) needs to be placed within the above
%stated directory
%Information about the working directoy can be obtained using the next few
%lines of code (need to be uncommented)
%workingDir=pwd;
%save('c:\MIM_scripting_matlab\workingDir.mat','workingDir')
%uisng these two lines run the program from Matlab as an Extension an the
%afterward load the workingDir.mat file into Matlab

%\\os210378\AI_Inference folder to put data

%just a bit of testing that needs to be romeved

%username=getenv('username');
%save('C:\MIM_scripting_matlab\username.mat','username');

% Read the local configuration file
configDecisionModule=readConfigFile('./configAiDecisionModule.txt');

try
  % Write a log entry indicating the start of the AI decision module
  writeToLog('AI decision module started',configDecisionModule);
  % Read user-defined AI configuration files
  userConfig=readAllUserConfigFiles(configDecisionModule.pathToUserConfigFiles);
  % Retrieve DICOM header information for all series
  dicomHeaderInfo=getAllDicomDataForSeries;
  
  %The following two lines are left for debug purpose. If the program is
  %called from MIM, the dicomHeaderInfo can be saved on disk. Then, the
  %program can be called from within Matlab, in which the above
  %getAllDicomDataForSeries can be commented out, and the saved variable
  %can be loaded. This makes it possible to debug as normally using all
  %Matlab debug functionalities.
  %save('C:\MIM_scripting_matlab\dicomHeaderInfo.mat',"dicomHeaderInfo");
  %load('C:\MIM_scripting_matlab\dicomHeaderInfo.mat','dicomHeaderInfo');

  % Process DICOM header information for each series
  for jDicomHeaderSeries=1:length(dicomHeaderInfo)
    if ~isempty(dicomHeaderInfo{jDicomHeaderSeries})
      informationString='Working on';
      % Extract patient ID if available
      if isfield(dicomHeaderInfo{jDicomHeaderSeries}{1},'Dicom_0010_0020')
        ptid=dicomHeaderInfo{jDicomHeaderSeries}{1}.Dicom_0010_0020;
        ptidhalf=ptid(1:floor(length(ptid)/2));
        informationString=[informationString, ' Patientid starting with: ',ptidhalf]; %#ok<AGROW>
      end
      % Extract series ID if available
      if isfield(dicomHeaderInfo{jDicomHeaderSeries}{1},'Dicom_0020_000E')
        informationString=[informationString, ' Series id: ',dicomHeaderInfo{jDicomHeaderSeries}{1}.Dicom_0020_000E]; %#ok<AGROW>
      end
      % Log the information about the current series
      writeToLog(informationString,configDecisionModule);
      % Iterate through user configurations and check trigger conditions
      for iUserFiles=1:length(userConfig)

        [indexImagesToCopy,consecutive,imagePosAvailable]=checkTriggerForSeries(dicomHeaderInfo{jDicomHeaderSeries},userConfig{iUserFiles});
        % Log messages based on trigger conditions
        if ~isnan(imagePosAvailable) && ~imagePosAvailable
          writeToLog('Image position not found in Dicom files. Data will not be forwarded to AI segmentation.',configDecisionModule);
        end
        if ~isnan(consecutive) && ~consecutive
          writeToLog('The available data does not seem to have a consecutive distance. The data will not be forwarded to AI segmentation.',configDecisionModule);
        end
        % Copy files to AI system if conditions are met
        if ~isnan(imagePosAvailable) && imagePosAvailable && ~isnan(consecutive) && consecutive && sum(indexImagesToCopy)>0
          copyFilesToAISystem(indexImagesToCopy,dicomHeaderInfo{jDicomHeaderSeries},configDecisionModule,userConfig{iUserFiles});
        end
      end
    end
  end
  % Delete old log files
  deleteTooOldLogFiles(configDecisionModule);
  % Log the end of the AI decision module
  writeToLog('AI decision module ended',configDecisionModule);
catch mse
  errorString=['Error in AI decision module: ',mse.getReport()];
  writeToLog(errorString,configDecisionModule);
end
end
%%
function configVar=readConfigFile(filePath)
try
  listOfRequestedConfigEntries={'pathToUserConfigFiles','ip','port','dataBaseName','fileNameForMongosh'...
    'pathToLogFilesDir','daysToKeepLogFiles','mimPatientListName'};
  I={};
  fid=fopen(filePath);
  while ~feof( fid )
    textLine = fgetl(fid);
    %Remove the part after #
    indexNumberSign = strfind(textLine,'#');
    if ~isempty(indexNumberSign)
      textLine=textLine(1:indexNumberSign(1)-1);
    end
    %Remove tab and strip traling and leading spaces
    textLine = regexprep(textLine, '\t', ' ');
    textLine = strip(textLine,'both');
    if ~isempty(textLine)
      I{end+1}=textLine; %#ok<AGROW>
    end
  end
  fclose(fid);
  for i =1:length(I)
    indexColon=strfind(I{i},':');
    indexColon=indexColon(1);
    key=strtrim(I{i}(1:(indexColon-1)));
    value=I{i}(indexColon+1:end);
    value=strtrim(value);
    if strcmp(value(1),'"') && strcmp(value(end),'"')
      value=value(2:(end-1));
    end
    if  ~isnan(str2double(value))
      value=str2double(value);
    end
    configVar.(key)=value;
  end
catch
  ME.message='Reading the config file for the AI decision module was unsuccessful';
  ME.identifier='MATLAB:mainAiDecisionModule:CouldNotReadLocalConfigFile';
  error(ME);
end
configInputLacking=false;
for i=1:length(listOfRequestedConfigEntries)
  if ~isfield(configVar,listOfRequestedConfigEntries{i})
    configInputLacking=true;
  end
end
if configInputLacking
  ME.message='Some entries in the local config file is missing';
  ME.identifier='MATLAB:mainAiDecisionModule:CouldNotReadLocalConfigFile';
  error(ME);
end
end
%%
function deleteTooOldLogFiles(configDecisionModule)
pathToLogDir=configDecisionModule.pathToLogFilesDir;
daysToKeepLogFiles=configDecisionModule.daysToKeepLogFiles;
if ~isfolder(pathToLogDir)
  ME.message='The logfile dir specified in the local config file can not be accessed';
  ME.identifier='MATLAB:mainAiDecisionModule:CouldNotReadLocalConfigFile';
  error(ME);
end
logFiles=dir(pathToLogDir);
indexLogFiles= cellfun(@(x) endsWith(x,'.txt'),{logFiles.name});
logFiles=logFiles(indexLogFiles);
indexOldLogFiles=cellfun(@(x) days(datetime('now')-datetime(x,'ConvertFrom','datenum'))>daysToKeepLogFiles,{logFiles.datenum});
logFiles=logFiles(indexOldLogFiles);
for iOldFiles=1:length(logFiles)
  try
    delete(fullfile(logFiles(iOldFiles).folder,logFiles(iOldFiles).name));
  catch
  end
end

end
