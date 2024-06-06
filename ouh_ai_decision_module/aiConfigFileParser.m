% function I = aiConfigFileParser(filePath, varargin)
%
% Description:
%   This function reads a configuration file specified by the filePath
%   parameter, parses the content, and returns structured information in
%   the variable I. The configuration file contains rules and settings
%   for directing data to a segmentation model in an AI system.
%
% Input Arguments:
%   - filePath (char): Path to the AI config file.
%   - varargin (optional): Additional options.
%     - 'GetSubFunctionHandles' (logical): If true, function handles to
%       subfunctions are returned for code testing (default is false).
%
% Output:
%   - I (struct): MATLAB variable containing information from the config
%     file, including comparisons, combined conditions, triggers, and AI
%     system settings.
%
% Additional Notes:
%   - The configuration file format and expected rules are documented in
%     the code comments.
%   - This function includes subfunctions for specific tasks within the
%     parsing process. These subfunctions can be accessed using the
%     function handles provided when 'GetSubFunctionHandles' is true.
%
% Examples:
%   % Parse an AI config file
%   configFile = 'path/to/your/configfile.txt';
%   result = aiConfigFileParser(configFile);
%
% See Also:
%   readComparison, readCombined, readTrigger, readAIConfig, checkConfigInfo,
%   readConfigFile, isStringLogicalStatement
%
% Author: CaB
% Date: 2023-11-15

function I=aiConfigFileParser(filePath,varargin)

%The first part is made to enable passing of handles to the subfunction to
%the code testing
inputParam = inputParser;
addParameter(inputParam,'GetSubFunctionHandles',false,@islogical);
parse(inputParam,varargin{:});
inputval=inputParam.Results;
if inputval.GetSubFunctionHandles
  I=struct();
  I.readComparison=@readComparison;
  I.readCombined=@readCombined;
  I.readTrigger=@readTrigger;
  I.readAIConfig=@readAIConfig;
  I.checkConfigInfo=@checkConfigInfo;
  I.readConfigFile=@readConfigFile;
  I.isStringLogicalStatement=@isStringLogicalStatement;
  return;
end
%end handle parsing to code testing
I=[];
I.comparisons=[];
I.combined=[];
I.trigger=[];
I.configAI={};
foundTrigger=false;

%Read all lines in the config file
%The read removes empty linie, remarks, and trailing and leading spaces
textLines=readConfigFile(filePath);

%Loop over all lines in config file
for iLine=1:length(textLines)
  textLine=textLines{iLine};
  %If we are still before the trigger line determine the line type
  if ~foundTrigger
    %Line type combariosns (e.g. T23_45:)
    comparisonIndex = regexp(textLine,'^T[0-9]+_[0-9]+','once');
    if ~isempty(comparisonIndex)
      [comparisonName,comparison]=readComparison(textLine);
      I.comparisons.(comparisonName)=comparison;
    end
    %Line type coparison (e.g. C45:)
    combinedIndex= regexp(textLine,'^C[0-9]+_[0-9]+','once');
    if ~isempty(combinedIndex)
      [combinedName,combined]=readCombined(textLine);
      I.combined.(combinedName)=combined;
    end
    %Line type trigger
    triggerIndex =regexp(textLine,'^Trigger:', 'once');
    if ~isempty(triggerIndex)
      trigger=readTrigger(textLine);
      I.trigger=trigger;
      foundTrigger=true;
    end
  else
    %Line should be part of the infomration going to the config file for
    %the AI system
    [aiConfigName,aiConfig]=readAIConfig(textLine);
    I.configAI.(aiConfigName)=aiConfig;
  end
end
%Check that all restrictions on the config files are fully fulfilled. The
%following function casts an error in case the format of the read config
%file is correct.
checkConfigInfo(I);
end
%%
function [comparisonName,comparison]=readComparison(textLine)
comparison=[];
%Validate line format
temp=regexp(textLine,'^T[0-9]+_[0-9]+[ ]*:[ ]*\([0-9a-fA-F]{4},[0-9a-fA-F]{4}\).*[<|>|>=|==|<=|~=][ ]*".*"$', 'once');
if isempty(temp)
  ME.message='The format of a comparison line is wrong. Should be of the format as e.g. T1_16:(0008,103E) Series Description=="VT2w Sag 3mm SENSE" #The comparison can be == <= <= and ~=. Numbers on the left hand side should also be placed within apostrophes';
  ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
  error(ME);
end
%Get the T variable name
[startIndex,endIndex] = regexp(textLine,'^T[0-9]+_[0-9]+');
comparisonName=textLine(startIndex:endIndex);

%Get the Dicom group and element values
[startIndex,endIndex] = regexp(textLine,'\([0-9a-fA-F]{4},[0-9a-fA-F]{4}\)');
dicomtag=textLine(startIndex:endIndex);
comparison.DicomGroup=dicomtag(2:5);
comparison.DicomElement=dicomtag(7:10);


%Get the comparison operator
[startIndex,endIndex] = regexp(textLine,'((>=)|(==)|(<=)|(~=)|<|>)');
comparison.comparisonOperator=textLine(startIndex:endIndex);

%Get the value to compare to
temp=textLine(endIndex+1:end);
[startIndex,endIndex] = regexp(temp,'".*"');
comparison.Value=temp((startIndex(1)+1):(endIndex(1)-1));
%Replace possible tabulator with space
comparison.Value=regexprep(comparison.Value, '\t', ' ');
%Remove trailing and leading spaces
comparison.Value=strip(comparison.Value,'both');
%End get the value to compare to
end
%%
function [combineName,combined]=readCombined(textLine)
%Check that the line start by C then a number a underscore and anoter number
textLine=strip(textLine,'both');
[startIndex,endIndex]=regexp(textLine,'^C[0-9]+_[0-9]+[ ]*:','once');
if isempty(startIndex)
  ME.message='The format of a combination line is wrong. It should start with the format as e.g. C14_34 :';
  ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
  error(ME);
end
if ~isStringLogicalStatement(textLine((endIndex(1)+1):end))
  ME.message='The format of a combination line is not a valid logical expression. Should be of the format as e.g. ~(T1_16 && T1_17)||(T16_45) #The operators are similar to the syntax in MATLAB, thus the operators are &&, ||, and ~';
  ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
  error(ME);
end
combineName=strip(textLine(startIndex:endIndex-1),'both');
combined=strip(textLine(endIndex+1:end),'both');
end
%%
function trigger=readTrigger(textLine)
textLine=strip(textLine,'both');
[~,endIndex]=regexp(textLine,'^Trigger[ ]*:','once');
if isempty(endIndex)
  ME.message='The format of the Trigger line is wrong. Should start with the format as e.g. Trigger  :';
  ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
  error(ME);
end
if ~isStringLogicalStatement(textLine((endIndex(1)+1):end))
  ME.message='The format of a trigger line is not a valid logical expression. Should be of the format as e.g. ~(C1_3 && T1_16) || C2 #The operators are similar to the syntax in MATLAB, thus the operators are &&, ||, and ~';
  ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
  error(ME);
end
trigger=strip(textLine(endIndex+1:end),'both');
end
%%
function [aiConfigName,aiConfig]=readAIConfig(textLine)
textLine=strip(textLine,'both');
[startIndex,~] = regexp(textLine,'^[a-z,A-Z].*:.+', 'once');
if isempty(startIndex)
  ME.message='One of the AI config line does not start with a varibale name folllowed by and collon and the additional text.';
  ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
  error(ME);
end
%Use the collon as seperator
[~,endIndex] = regexp(textLine,':','once');
aiConfigName=strip(textLine(1:(endIndex(1)-1)),'both');
aiConfig=strip(textLine((endIndex(1)+1):end),'both');
% Check on format of some of the aiConfigNames
if strcmp(aiConfigName,'ModelName')
  if strcmp(aiConfig,'""')
    ME.message='The model name can not be an empty string.';
    ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
    error(ME);
  end
end
if strcmp(aiConfigName,'ModelHash')
  if strcmp(aiConfig,'""')
    ME.message='The model hash can not be an empty string.';
    ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
    error(ME);
  end
end
if strcmp(aiConfigName,'NiceLevel')
  startIndex=regexp(aiConfig,'^"[1-9]+[0-9]*"$','once');
  if isempty(startIndex)
    ME.message='The NiceLevel is not a positive integer in parenthesis.';
    ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
    error(ME);
  end
end
if strcmp(aiConfigName,'SendDirectory')
  if strcmp(aiConfig,'""')
    ME.message='The SendDirectory can not be an empty string.';
    ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
    error(ME);
  end
end
startIndex=regexp(aiConfigName,'^ReturnDicom','once');
if ~isempty(startIndex)
  if strcmp(aiConfig,'""')
    ME.message=['The ', aiConfigName,' can not be an empty string.'];
    ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
    error(ME);
  end
end
startIndex=regexp(aiConfigName,'^ReturnDirectory','once');
if ~isempty(startIndex)
  if strcmp(aiConfig,'""')
    ME.message=['The ', aiConfigName,' can not be an empty string.'];
    ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
    error(ME);
  end
end
if strcmp(aiConfigName,'InferenceMaxRunTime')
  startIndex=regexp(aiConfig,'^"[1-9][0-9]*"$','once');
  if isempty(startIndex)
    ME.message='Format of InferenceMaxRunTime line for the AI config does not have the correct value. It should be in second surround by "" e.g. "65"';
    ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
    error(ME);
  end
end  
if strcmp(aiConfigName,'EmptyStructWithModelName')
  startIndex=regexp(aiConfig,'^"(true|false)"$','once');
  if isempty(startIndex)
    ME.message='The value for the line EmptyStructWithModelName should be wither "true" or "false"';
    ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
    error(ME);
  end
end
startIndex=regexp(aiConfigName,'^Struct_[1-9]','once');
if ~isempty(startIndex)
  startIndex=regexp(aiConfig,'^".+"[ ]*".+"[ ]*".+"[ ]*\[[0-9]+,[0-9]+,[0-9]+\]"[ ]*"[0-9]+"$','once');
  if isempty(startIndex)
    ME.message='Format of a Struct line for the AI config does not have the correct structure. E.g. "InterStructName1" "Bladder_AI" "Organ" "[255,0,0]" "2"';
    ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
    error(ME);
  else
    %Chekc color in range 0-255
    [startIndex,endIndex]=regexp(aiConfig,'"\[[0-9]+,[0-9]+,[0-9]+\]"','once');
    colorString=aiConfig(startIndex+2:endIndex-2);
    startIndex=regexp(colorString,',');
    red=str2double(colorString(1:startIndex(1)));
    green=str2double(colorString(startIndex(1)+1:startIndex(2)-1));
    blue=str2double(colorString(startIndex(2)+1:end));
    if (red>255) || (green>255) || (blue>255)
      ME.message='In one of the Struct lines the colour values are not in the range 0-255';
      ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
      error(ME);
     end
  end  
end
end
%%
function checkConfigInfo(I)
%Throw an error in case some relevant config info is missing
if ~isfield(I.configAI,'ModelName') || isempty(I.configAI.ModelName)
  ME.message='The model name is lacking in the info for the AI.';
  ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
  error(ME);
end
if ~isfield(I.configAI,'ModelHash') || isempty(I.configAI.ModelHash)
  ME.message='The model hash value is lacking in the info for the AI';
  ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
  error(ME);
end
%Check if the Dicom return address is available and includes both IP, port, and AET.
returnDicomList=fields(I.configAI);
indexReturnDicom=cellfun(@(x) contains(x,'ReturnDicom'), returnDicomList);
returnDicomList=returnDicomList(indexReturnDicom);
%Extract the dicom return numbers after _
indexReturnDicom=[];
if ~isempty(returnDicomList)
  indexReturnDicom=unique(cellfun(@(x) str2double(extractAfter(x,'_')),returnDicomList));
end
returnDicomInfomationMissing=false;
if ~isempty(indexReturnDicom)
  for i=indexReturnDicom(:)'
    if ~isfield(I.configAI,['ReturnDicomNodeAET_',num2str(i)])
      returnDicomInfomationMissing=true;
    end
    if ~isfield(I.configAI,['ReturnDicomNodeIP_',num2str(i)])
      returnDicomInfomationMissing=true;
    end
    if ~isfield(I.configAI,['ReturnDicomNodePort_',num2str(i)])
      returnDicomInfomationMissing=true;
    end
  end
end
if returnDicomInfomationMissing
  ME.message='Only partial Dicom return information is provided. Both IP, Port and AET needs to be defined';
  ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
  error(ME);
end
%Check if the directory return address is available.
returnDirectoryList=fields(I.configAI);
indexReturnDirectory=cellfun(@(x) contains(x,'ReturnDirectory'), returnDirectoryList);
returnDirectoryList=returnDirectoryList(indexReturnDirectory);
%Extract the dicom return numbers after _
indexReturnDirectory=[];
if ~isempty(returnDirectoryList)
  indexReturnDirectory=unique(cellfun(@(x) str2double(extractAfter(x,'_')),returnDirectoryList));
end
%Check that at least one directory or Dicom return address is available.
if isempty(indexReturnDirectory) && isempty(indexReturnDicom)
  ME.message='No directory nor Dicom return address is provided.';
  ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
  error(ME);
end

%Check that trigger info is available
if isempty(I.trigger)
  ME.message='No trigger infomration found in config file';
  ME.identifier='MATLAB:aiConfigFileParser:WrongUserInput';
  error(ME);
end
end
%%
function I=readConfigFile(filePath)
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
I=I(:);
end
%%
function I=isStringLogicalStatement(textLine)
%A logical string can, in this context, be composed of T variables (e.g. T2_4), C variables (C3_2), &&, ||, ~(not), and parenthesis.
%However, the order of these is somewhat restricted. In the following, 'variable' will be either T variables og C variables.
%Using this, a logical expression can be:
%   variable  (C og T variable)
%	  ~logical expression
%	  (logical expression)
% 	logical expression && logical expression
%	  logical expression || logical expression
%Whether this structure is fulfilled is tested in the current recursive function.

%Start by removing leading and trailing spaces
textLine=strip(textLine,'both');
%An empty string is not a logical expresion return false
if isempty(textLine)
  I=false;
  return;
end

%Locate T and C varibale, && and || (need in the following)
%For && and || we will only use those in which the number of start and stop
%parenthesis are in balance at the two sides of the && and || operator

[startIndexVar,endIndexVar] = regexp(textLine,'^[T|C][0-9]+_[0-9]+$');
[startIndexAndOr,endIndexAndOr] = regexp(textLine,'(&&|\|\|)');
indexBalancedParenthesisSides=false(length(startIndexVar),1);

%Remove those “&&” and “||” where the parentheses are not balanced on the
%two sides. This is not a restriction from the above rules since only one
%rule includes parenthesis, and this rule includes both a start and stop
%parenthesis.
for i=1:length(startIndexAndOr)
  startLeftSide = length(strfind(textLine(1:(startIndexAndOr(i)-1)),'('));
  endLeftSide = length(strfind(textLine(1:(startIndexAndOr(i)-1)),')'));
  startRightSide = length(strfind(textLine((endIndexAndOr(i)+1):end),'('));
  endRightSide = length(strfind(textLine((endIndexAndOr(i)+1):end),')'));
  if startLeftSide==endLeftSide && startRightSide==endRightSide
    indexBalancedParenthesisSides(i)=true;
  end
end
startIndexAndOr=startIndexAndOr(indexBalancedParenthesisSides);
endIndexAndOr=endIndexAndOr(indexBalancedParenthesisSides);

%If the string is a variable C or T return true
if ~isempty(startIndexVar) && startIndexVar(1)==1 && endIndexVar(1)==length(textLine)
  I=true;
  return;
  
%If the string starte by ~ return the evaluation of logical expresion on
%the remaining part of the string
elseif strcmp(textLine(1),'~')
  I=isStringLogicalStatement(textLine(2:end));

%If the string start with "(" and ends with ")" and they are matching pairs
elseif strcmp(textLine(1),'(') && strcmp(textLine(length(textLine)),')') && ...
    indexForMatchingParenthesis(textLine)==length(textLine)
  I=isStringLogicalStatement(textLine(2:end-1));

%If there is an “&&” or “||” operator, return the result of the two sides
%surrounding the operator combined with the “and” operation (both sides
%need to be a logical expression)
elseif ~isempty(startIndexAndOr) && startIndexAndOr(1)>1 && ...
                endIndexAndOr(1)<length(textLine)
  I=isStringLogicalStatement(textLine(1:(startIndexAndOr(1)-1))) && ...
    isStringLogicalStatement(textLine((endIndexAndOr(1)+1):end));
  
%Otherwise return false
else
  I=false;
end
end
%%
function I=indexForMatchingParenthesis(inputString)
I=0;
startParenthesis='(';
endParenthesis=')';
if strcmp(inputString(1),'{')
  startParenthesis='{';
  endParenthesis='}';
elseif strcmp(inputString(1),'[')
  startParenthesis='[';
  endParenthesis=']';
end
counter=0;
index=1;
foundMatch=false;
while ~foundMatch && (index<=length(inputString))
  if strcmp(inputString(index),startParenthesis)
    counter=counter+1;
  end
  if strcmp(inputString(index),endParenthesis)
    counter=counter-1;
  end
  if counter==0
    foundMatch=true;
    I=index;
  end
  index=index+1;
end
end
