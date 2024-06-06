%function [triggerStatus,consecutive,imagePosAvailable]=checkTriggerForSeries(dicomHeaders,aiConfigFile)
%
%   Description:
%       This function checks trigger conditions for each DICOM header in the provided
%       series, evaluating comparisons specified in the AI configuration file. It
%       performs basic comparisons and combined logical operations, and finally, a
%       trigger calculation based on the combined conditions.
%       All basic comparisons that can not be performed e.g. due to
%       comparison between number and string or no information for the
%       given dicom tag in the file, will result in the value false.
%
%   Input:
%       dicomHeaders - Cell array of DICOM headers for the series.
%       aiConfigFile - AI configuration structure containing trigger and comparison
%                      information.
%
%   Output:
%       triggerStatus - Logical array indicating whether trigger conditions are met for
%                       each DICOM header.
%       consecutive - Logical value indicating whether the included images are
%                     consecutive in position.
%       imagePosAvailable - Logical value indicating whether the position information
%                           is available for trigger calculation.
%
%   Example:
%       dicomHeaderInfo = getAllDicomDataForSeries;
%       aiConfig = readAllUserConfigFiles('/path/to/configs');
%       [triggerStatus, consecutive, imagePosAvailable] = checkTriggerForSeries(dicomHeaderInfo, aiConfig);
%
% Author: CaB
% Date: 2023-11-15

function [triggerStatus,consecutive,imagePosAvailable]=checkTriggerForSeries(dicomHeaders,aiConfigFile)
triggerStatus=false(length(dicomHeaders),1);
comparisonList=fieldnames(aiConfigFile.comparisons);
combinedList=fieldnames(aiConfigFile.combined);

% Loop through each dicomHeader
for i=1:length(dicomHeaders)
  dicomHeader=dicomHeaders{i};
  comparisonListBoolean=[];
  %Perform all the Tx_y test. The basic comparisons
  %All basic comparisons that can not be performed e.g. due to comparison
  %between number and string or no information for the given dicom tag in
  %the file, will result in the value false. The try-catch statement ensures
  %this functionality.
  for j=1:length(comparisonList)
    try
      group=aiConfigFile.comparisons.(comparisonList{j}).DicomGroup;
      element=aiConfigFile.comparisons.(comparisonList{j}).DicomElement;
      fieldName=['Dicom_',group,'_',element];
      if isfield(dicomHeader,fieldName)
        actualDicomValue=dicomHeader.(fieldName);
      else
        actualDicomValue=NaN;
      end

      %Make logical test string
      comparisonOperator=aiConfigFile.comparisons.(comparisonList{j}).comparisonOperator;
      compareValue=aiConfigFile.comparisons.(comparisonList{j}).Value;
      compareValue=strip(compareValue,'both');
      if isnumeric(actualDicomValue)
        testString=[num2str(actualDicomValue),comparisonOperator,compareValue];
      else
        testString=['"',actualDicomValue,'"',comparisonOperator,'"',compareValue,'"'];
      end
      logicalValue=eval(testString);
    catch
      logicalValue=false;
    end
    comparisonListBoolean.(comparisonList{j})=logicalValue;
  end
  %Perform the combined comparisons
  for j=1:length(combinedList)
    try
      temp=aiConfigFile.combined.(combinedList{j});
      [startIndex,endIndex] = regexp(temp,'T[0-9]+_[0-9]+');
      testString=temp(1:startIndex(1)-1);
      for k=1:length(startIndex)
        value=comparisonListBoolean.(temp(startIndex(k):endIndex(k)));
        nextStart=length(temp);
        if k<length(startIndex)
          nextStart=startIndex(k+1)-1;
        end
        testString=[testString,num2str(value),temp(endIndex(k)+1:nextStart)]; %#ok<AGROW>
      end
      logicalValue=eval(testString);
    catch
      logicalValue=false;
    end
    comparisonListBoolean.(combinedList{j})=logicalValue;

  end
  %Perform the trigger calculation
  try
    temp=aiConfigFile.trigger;
    [startIndex,endIndex] = regexp(temp,'T[0-9]+_[0-9]+|C[0-9]+_[0-9]+');
    testString=temp(1:startIndex(1)-1);
    for k=1:length(startIndex)
      value=comparisonListBoolean.(temp(startIndex(k):endIndex(k)));
      nextStart=length(temp);
      if k<length(startIndex)
        nextStart=startIndex(k+1)-1;
      end
      testString=[testString,num2str(value),temp(endIndex(k)+1:nextStart)]; %#ok<AGROW>
    end
    logicalValue=eval(testString);
  catch
    logicalValue=false;
  end
  % Update output variables
  % The initial value of false changes to true if the logical value is
  % true. Checking for the possibility of the logical value being NaN
  % (should not be possible due to the above try-catch statements); in that
  % case, the initialised false value is unchanged.
  if ~isnan(logicalValue) && logicalValue
    triggerStatus(i)=true;
  end
end
%If found images check wheter they are consecutive
consecutive=NaN;
imagePosAvailable=NaN;
if sum(triggerStatus)>0
  [consecutive,imagePosAvailable]=validateConsecutive(dicomHeaders,triggerStatus);
end
end
%%
function [I,imagePosAvailable] =validateConsecutive(dicomHeaders,indexInclude)
I=true;
imagePosAvailable=true;
try
  imagePos=sort(cellfun(@(x) x.Dicom_0020_0032(3),dicomHeaders(indexInclude==1)));
catch
  imagePosAvailable=false;
  I=false;
  return;
end
meanDistance=mean(imagePos(2:end)-imagePos(1:(end-1)));
expectedPos=(0:length(imagePos)-1)*meanDistance+min(imagePos);
indexPositionOk=abs(imagePos(:)-expectedPos(:))<.01*meanDistance;
if sum(indexPositionOk)~=length(imagePos)
  I=false;
end
end
