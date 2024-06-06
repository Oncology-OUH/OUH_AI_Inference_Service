%function parsedOutput = parseMungoOutput(mungoString)
%
% Parses the output from a Mungo database query and returns a structured
% Matlab variable containing all the data.
%
% Input:
%   mungoString: A string received as output from a Mungo database query
%
% Output:
%   parsedOutput: Structured Matlab variable representing the Mungo database query result
%
% The function handles the Mungo database output, which is close to JSON
% format with some exceptions. The output consists of key-value pairs
% within square brackets, representing a list of values.
%
% The structure can be described as follows:
%   JSONLike = {keyValuePair1, keyValuePair2, ..., keyValuePairN}
%   keyValuePair = key : Value
%   key = A string starting with a letter (keys starting with underscore
%         are prefixed with 'n' in the output, e.g., _id becomes n_id)
%   Value = Various types including string, true, false, numeric value,
%           Long("number"), list of values, or another JSONLike object
%
% The function internally uses helper functions:
%   - parseValue: Handles parsing of individual values
%   - parseJsonLikePart: Handles parsing of JSONLike objects
%   - findOutermostCommasInString: Finds commas on the outermost level
%
% Example Usage:
%   queryResult = '[12 , "This is a test" ,  {keyNumber1:"TestString",keyNumber2: [12,34,[{keyNumber3:"New test String",keyNumber4:True},Long("42")]]}, "Another test string",42]';
%   parsedOutput = parseMungoOutput(queryResult);
%   
% Example Usage, that makes a full query on the Mungo database for the
% patient id (dicom tag 0010,0020) xxxxxx-xxxx, this can be usefull to
% finde relevant entries in the database:
%   query='{"100020":"xxxxxx-xxxx"}';
%   mungoString=mimDataBaseQuery(query);
%   MatlabOutput=parseMungoOutput(mungoString);
%
% Author: CaB
% Date: 2023-11-15

function parsedOutput =parseMungoOutput(mungoString)
%Replace newline and carriage return with an empty string
mungoString = strrep(mungoString, newline, '');
mungoString = strrep(mungoString, char(13), '');
%Replace single quotation marks with double.
%mungoString=strrep(mungoString,char(39),'"');

indexStart=strfind(mungoString,'[');
indexEnd=strfind(mungoString,']');
if isempty(indexStart) || isempty(indexEnd)
  ME.message='The format of the Mungo database string is wrong. Can not find the start and end hard parenthesis.';
  ME.identifier='MATLAB:mungoCall:WrongOutputFormatFromDataBase';
  error(ME);
end
indexStart=indexStart(1);
indexEnd=indexEnd(end);

parsedOutput =parseValue(mungoString(indexStart:indexEnd));
end
%%
function I=parseJsonLikePart(mungoString)


indexStart=strfind(mungoString,'{');
indexEnd=strfind(mungoString,'}');
if isempty(indexStart) || isempty(indexEnd)
  ME.message='The format of the Mungo database string is wrong. Can not find the start and end curly parenthesis.';
  ME.identifier='MATLAB:mungoCall:WrongOutputFormatFromDataBase';
  error(ME);
end
indexStart=indexStart(1);
indexEnd=indexEnd(end);
if (indexEnd-indexStart)==1
  I='';
  return
end
mungoString=mungoString(indexStart+1:indexEnd-1);
%At this stage the mungoString should be a list of keyValue pairs where
%start and end { and } has been removed

%Find the keyValues pairs in the sting by finding the commas on the
%outermost level. That means do not include the commas that are surrounded
%by curly or hard parenthesis or within quotation marks.
indexCommas=findOutermostCommasInString(mungoString);
indexCommas=[0,indexCommas,length(mungoString)+1];
%Now loop all the keyValuePairs
for i=1:(length(indexCommas)-1)
  keyValuePair=mungoString((indexCommas(i)+1):(indexCommas(i+1)-1));
  posCollon=strfind(keyValuePair,':');
  if isempty(posCollon)
    ME.message='The format of the Mungo database string is wrong. Seem to be missing a collon between key and value';
    ME.identifier='MATLAB:mungoCall:WrongOutputFormatFromDataBase';
    error(ME);
  end
  if posCollon(1)==1 || posCollon(1)==length(keyValuePair)
    ME.message='The format of the Mungo database string is wrong. Seem that either a key or value is missing around a collon';
    ME.identifier='MATLAB:mungoCall:WrongOutputFormatFromDataBase';
    error(ME);
  end
  key=strtrim(keyValuePair(1:(posCollon(1)-1)));
  if strcmp(key(1),'_')
    key=['n',key]; %#ok<AGROW>
  end
  %In some special cases in the Mungo db, a key is a number surrounded by
  %quotation marks (e.g. a dicom tag). In that case, add Number_ to key.
  if ~isempty(regexp(key,'^"[0-9,a-f,A-F]*"$','once'))
    key=['Number_',key(2:end-1)];
  end
  if ~isempty(regexp(key,"^'[0-9,a-f,A-F]*'$",'once'))
    key=['Number_',key(2:end-1)];
  end
  value=keyValuePair(posCollon(1)+1:end);
  value=parseValue(value);
  I.(key)=value;
end
end
%%
function I=parseValue(valueString)
valueString=strtrim(valueString);
if strcmpi(valueString,'true')
  I=true;
  return;
elseif strcmpi(valueString,'false')
  I=false;
  return;
elseif strcmp(valueString(1),'"') && strcmp(valueString(end),'"')
  I=valueString(2:(end-1));
  return;
elseif strcmp(valueString(1),char(39)) && strcmp(valueString(end),char(39))
  I=valueString(2:(end-1));
  return;
elseif ~isnan(str2double(valueString))
  I=str2double(valueString);
  return;
elseif ~isempty(regexp(valueString,'^Binary\.createFromBase64\(".*?",.*[0-9,a-f,A-F]+\)$', 'once')) %Matches Binary.createFromBase64("AAE=", 0) which is special case of value in Mungo db
  I=valueString;
  return;
elseif ~isempty(regexp(valueString,'^ISODate\(".*?"\)$','once')) %Matches ISODate("2023-10-26T00:00:00.000Z") which is special case of value in Mungo db
  I=valueString;
  return;
elseif strcmpi(valueString,'null') %Special case in the mungo database that the value can be null
  I=NaN;
  return;
elseif startsWith(valueString,'Long("') && endsWith(valueString,'")')
  temp=str2double(valueString(7:(end-2)));
  if isnan(temp)
    ME.message='The format of the Mungo database string is wrong. A value stated as long cannot be converted to a numeric value';
    ME.identifier='MATLAB:mungoCall:WrongOutputFormatFromDataBase';
    error(ME);
  end
  I=temp;
  return;
elseif strcmp(valueString(1),'[') && strcmp(valueString(end),']')
  %This is a list seprate the individual list items and join them in a
  %cell array
  if length(valueString)<=2
    ME.message='The format of the Mungo database string is wrong. A list seem to have no content';
    ME.identifier='MATLAB:mungoCall:WrongOutputFormatFromDataBase';
    error(ME);
  end
  valueString=valueString(2:(end-1));
  indexCommas=findOutermostCommasInString(valueString);
  indexCommas=[0,indexCommas,length(valueString)+1];
  %Now loop all the Values in the list
  I=cell(length(indexCommas)-1,1);
  for i=1:(length(indexCommas)-1)
    I{i}=parseValue(valueString((indexCommas(i)+1):(indexCommas(i+1)-1)));
  end
  return;
elseif strcmp(valueString(1),'{') && strcmp(valueString(end),'}')
  I=parseJsonLikePart(valueString);
  return;
else
  ME.message='The format of the Mungo database string is wrong. Could not interpret one of the values.';
  ME.identifier='MATLAB:mungoCall:WrongOutputFormatFromDataBase';
  error(ME);
end


end
function indexCommas=findOutermostCommasInString(mungoString)

%When counting the commas on the outer level, it is essential not to count
%commas within quotation marks e.g. a comman in a sting value. Single or
%double quotation marks can be used to surround strings in the database.
%This is supported to make it possible to use a quotation mark within the
%string (the other type of quotation mark will then surround the string in
%the database).
%
%A value could be e.g.
%
%{key1:"The test s efficiency, depends %on a curly start parenthesis {". Key2:.This is a “difficult test }.
%
%So wthen, searching for commas on the outer level, they should not be
%surrounded by curly, hard or normal parenthesis, nor within a string.
%
%The below implementation keeps track of whether the given position in the
%mungoString is inside or outside a substring. This is done by detecting
%the first type of quotation mark (these can only mark the start of a
%string or be part of a string). When such a quotation mark is found,
%nothing is performed on the following part of the mungoString until a
%similar quotation mark is located. So if the first quotation mark is “
%then everything following this point in the string including (e.g. ,   { [
%( ) will be seen as part of a substring and will thus not change the state
%of whether the given mungoSting position is at the outer level or inside a
%subsection. Outside a substring, the algorithm counts the start and end
%parenthesis to decide if a given point is inside or outside parenthesis.



indexCommas=[];
counterCurlyParenthesis=0;
counterHardParenthesis=0;
counterQuotationMarksDouble=0;
counterQuotationMarksSingle=0;
counterNormalParenthesis=0;
for i=1:length(mungoString)
  if strcmp(mungoString(i),'{') && counterQuotationMarksSingle==0 && counterQuotationMarksDouble==0
    counterCurlyParenthesis=counterCurlyParenthesis+1;
  elseif strcmp(mungoString(i),'}') && counterQuotationMarksSingle==0 && counterQuotationMarksDouble==0
    counterCurlyParenthesis=counterCurlyParenthesis-1;
  elseif strcmp(mungoString(i),'[') && counterQuotationMarksSingle==0 && counterQuotationMarksDouble==0
    counterHardParenthesis=counterHardParenthesis+1;
  elseif strcmp(mungoString(i),']') && counterQuotationMarksSingle==0 && counterQuotationMarksDouble==0
    counterHardParenthesis=counterHardParenthesis-1;
  elseif strcmp(mungoString(i),'(') && counterQuotationMarksSingle==0 && counterQuotationMarksDouble==0
    counterNormalParenthesis=counterNormalParenthesis+1;  
  elseif strcmp(mungoString(i),')') && counterQuotationMarksSingle==0 && counterQuotationMarksDouble==0
    counterNormalParenthesis=counterNormalParenthesis-1;  
  elseif strcmp(mungoString(i),"'") && counterQuotationMarksDouble==0
    counterQuotationMarksSingle=mod(counterQuotationMarksSingle+1,2);
  elseif strcmp(mungoString(i),'"')  && counterQuotationMarksSingle==0
    counterQuotationMarksDouble=mod(counterQuotationMarksDouble+1,2);
  else
    if counterCurlyParenthesis==0 && counterHardParenthesis==0 && counterQuotationMarksDouble==0 ...
        && counterQuotationMarksSingle==0 && counterNormalParenthesis==0 && strcmp(mungoString(i),',')
      %At this position there is a comma that seperated the key value
      %pairs on the outermost level
      indexCommas=[indexCommas,i]; %#ok<AGROW>
    end
  end
end
end
