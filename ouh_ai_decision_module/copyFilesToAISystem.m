% function copyFilesToAISystem(indexImagesToCopy, dicomHeaderInfo, configDecisionModule, userConfig)
%
% Inputs:
%   - indexImagesToCopy: Indices of the images to be copied.
%   - dicomHeaderInfo: Information extracted from DICOM headers.
%   - configDecisionModule: Configuration information for the decision module.
%   - userConfig: User-specific configuration information.
%
% The function copies DICOM files and related information to the AI system for segmentation.
%
% Outputs:
%   - None. Data is copied to the AI system for further processing.
%
% Functionality:
%   - Checks if patient IDs and image instance UIDs are present in the DICOM header.
%   - Queries the Mungo database to locate the corresponding folders for the given patient and images.
%   - Copies DICOM files to a temporary folder and renames it based on the series UID.
%   - Moves the temporary folder to the final destination after successful copying.
%   - Logs information and returns if any issues are encountered during the process.
%
% Example:
%   copyFilesToAISystem(indexImagesToCopy, dicomHeaderInfo, configDecisionModule, userConfig);
%
% Author: CaB
% Date: 2023-11-15


function copyFilesToAISystem(indexImagesToCopy,dicomHeaderInfo,configDecisionModule,userConfig)
dicomHeaderInfo=dicomHeaderInfo(indexImagesToCopy);

indexPtIdExist=cellfun(@(x) isfield(x,'Dicom_0010_0020'), dicomHeaderInfo);
if sum(indexPtIdExist)~=length(indexPtIdExist)
  informationString='Patient id not present in all the images. Thus, it is not possible to locate the images in the database. The data will not be forwarded to AI segmentation.';
  writeToLog(informationString,configDecisionModule);
  return;
end
ptId=cellfun(@(x) x.Dicom_0010_0020, dicomHeaderInfo,UniformOutput=false);
ptId=unique(ptId);
if length(ptId)~=1
  informationString='There seems to be a mixture of patient-ids within the images. The data will not be forwarded to AI segmentation.';
  writeToLog(informationString,configDecisionModule);
  return;
end
indexInstanceUIDExist=cellfun(@(x) isfield(x,'Dicom_0008_0018'), dicomHeaderInfo);
if sum(indexInstanceUIDExist)~=length(indexInstanceUIDExist)
  informationString='Image instance UID is not defined in all images. The data will not be forwarded to AI segmentation.';
  writeToLog(informationString,configDecisionModule);
  return;
end
instanceUIDs=cellfun(@(x) x.Dicom_0008_0018, dicomHeaderInfo,UniformOutput=false);
query='';
mungoString =mimDataBaseQuery(query, 'collectionName','patientLists');
patientListInfo=parseMungoOutput(mungoString);
indexPtList=cellfun(@(x) strcmpi(x.name,configDecisionModule.mimPatientListName),patientListInfo);
mimPatientListNumber=patientListInfo{indexPtList}.n_id;

%Get the folder name and instance UID info for the selected patient and within the patientList defined by the name in the configDecisionModule.mimPatientListName
query=['{"100020":"',ptId{1},'","mimdata.patientLists":', num2str(mimPatientListNumber),'},{"mimdata.folders":1,"mimdata.sopInstanceUids": 1}'];
queryRes=mimDataBaseQuery(query,ip=configDecisionModule.ip,port=configDecisionModule.port, dataBaseName=configDecisionModule.dataBaseName,fileNameForMongosh=configDecisionModule.fileNameForMongosh);
%The following two lines are left for debug purpose. If the program is
%called from MIM, the queryRes can be saved on disk. Then, the
%program can be called from within Matlab, in which the above
%mimDataBaseQuery can be commented out, and the saved variable
%can be loaded. This makes it possible to debug as normally using all
%Matlab debug functionalities.
%save('C:\MIM_scripting_matlab\queryRes.mat',"queryRes");
%save('C:\MIM_scripting_matlab\dicomHeaderInfo_copyFilesToAISystem.mat', "dicomHeaderInfo");
% load('C:\MIM_scripting_matlab\queryRes.mat',"queryRes");
queryRes=parseMungoOutput(queryRes);
folderNames=cell(size(instanceUIDs));
for iFolderInDataBase=1:length(queryRes)
  if isfield(queryRes{iFolderInDataBase},"mimdata")
    if isfield(queryRes{iFolderInDataBase}.mimdata,'folders') && isfield(queryRes{iFolderInDataBase}.mimdata,'sopInstanceUids')
      [~,ia,~]=intersect(instanceUIDs,queryRes{iFolderInDataBase}.mimdata.sopInstanceUids);
      tempFolderName=queryRes{iFolderInDataBase}.mimdata.folders{1};
      % The MIM database provides file path separators with a double
      % backslash. Thus, a double backspace (UNC path) is four backslashes.
      % The following regexp changes: double backslash (which does not have
      % a backslash in front or after) to single backspace, and four
      % backslashes are changed to two. In the regexp for the four
      % backslashes, where are eight backslashes since they all need to be
      % escaped
      tempFolderName=regexprep(tempFolderName,'([^\\])\\\\([^\\])','$1\\$2');
      tempFolderName=regexprep(tempFolderName,'^\\\\\\\\(.+)','\\\\$1');
      folderNames(ia)={tempFolderName};
    end
  end
end
indexMissingFolders=cellfun(@(x) isempty(x),folderNames);
if sum(indexMissingFolders)>0
  informationString='Could not locate the folder for all the images in the MIM database. The data will not be forwarded to AI segmentation';
  writeToLog(informationString,configDecisionModule);
  return;
end
%Now copy all the files. First, the images will be copied to the temporary
%folder name, which will be renamed to the "correct" folder name after the
%copying. This method is used to avoid the receiving function starting to
%work on the data before all the data has been copied

stringDate=char(datetime('now','Format','yyyy_MM_dd_HH_mm_ss'));
lastPartSeriesUID='notDefined';
if isfield(dicomHeaderInfo{1},'Dicom_0020_000E')
  lastPartSeriesUID=dicomHeaderInfo{1}.Dicom_0020_000E;
end
if length(lastPartSeriesUID)>6
  lastPartSeriesUID=lastPartSeriesUID((end-5):end);
end
tempDirName=['receiving_',stringDate,'_LastPartSeriesUID_',lastPartSeriesUID];
finalDirName=['ready_',stringDate,'_LastPartSeriesUID_',lastPartSeriesUID];
userPath=userConfig.configAI.SendDirectory;
userPath=strrep(userPath,'"','');
tempDirName=fullfile(userPath,tempDirName);
finalDirName=fullfile(userPath,finalDirName);
status=mkdir(tempDirName);
if status~=1
  informationString='Could not make the directory at the destination folder. The data will not be forwarded to AI segmentation';
  writeToLog(informationString,configDecisionModule);
  return;
end
status=mkdir(fullfile(tempDirName,'dcminput'));
if status~=1
  informationString='Could not make the dicomData directory in the destination folder. The data will not be forwarded to AI segmentation';
  writeToLog(informationString,configDecisionModule);
  return;
end
statusCopy=true(length(folderNames),1);
userConfig.configAI.ModelName
informationString=['Start copying data to ',userConfig.configAI.ModelName];
writeToLog(informationString,configDecisionModule);
for iFiles=1:length(folderNames)
  orgfile=fullfile(folderNames{iFiles},[instanceUIDs{iFiles},'.dcm']);
  %writeToLog(orgfile,configDecisionModule)
  statusCopy(iFiles)=copyfile(orgfile,fullfile(tempDirName,'dcminput'));
end
if sum(statusCopy)~=length(statusCopy)
  informationString='Not all files could be copied to the AI system. The data will not be forwarded to AI segmentation';
  writeToLog(informationString,configDecisionModule);
  return;
end
%At this position, all files have been copied successfully.

%Now copy the config file info
statusRename=writeConfigToAISystem(userConfig,tempDirName,'aiconfig.txt');
if statusRename~=1
  informationString='Could not copy config file to destination folder. The data will not be forwarded to AI segmentation';
  writeToLog(informationString,configDecisionModule);
  return;
end

%Change the name of the folder
statusRename=movefile(tempDirName,finalDirName);
if statusRename~=1
  informationString='Could not rename the folder in the AI system. The data will not be forwarded to AI segmentation';
  writeToLog(informationString,configDecisionModule);
  return;
end
end