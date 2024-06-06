% Function: getAllDicomDataForSeries
%
% Description:
%   Get Dicom header information provided by MIM software (the current
%   program is part of an Matlab MIM extension)
%   Retrieves DICOM header information for all DICOM series in the current session.
%
%
% Output:
%   dicomHeaderInfo - Cell array containing DICOM header information for each series.
%                     Each cell corresponds to a DICOM series and contains a cell array of DICOM headers.
%                     Each DICOM header is represented as a structure with field-value pairs.
%
% Usage:
%   dicomHeaderInfo = getAllDicomDataForSeries()
%
% Dependencies:
%   This function relies on a 'bridge' variable in the MATLAB base workspace,
%   which is assumed to be associated with the current session. When MIM
%   software uses Matlab as an extension (an externally created user program
%   used to enhance MIM functionality), MIM starts Matlab in the 'base'
%   environment in which the variable 'bridge' is defined by MIM. The 'base'
%   related Matlab script (created as part of the MIM communication with
%   Matlab) then calls the user-defined Matlab script. The MIM-Matlab
%   communication then relies on variables in the 'base' environment, which
%   can be accessed with a command like bridge = evalin('base','bridge'),
%   which accesses the bridge variable in the 'base' environment and creates
%   a local copy of that variable.
%
% Author: CaB
% Date: 2023-11-18

function dicomHeaderInfo = getAllDicomDataForSeries
% Retrieve the 'bridge' variable from the MATLAB base workspace
bridge = evalin('base', 'bridge');
% Get all DICOM series in the current session
dicomSeries = bridge.getSession().getAllDicomSeries();
% Initialize cell array to store DICOM header information for each series
dicomHeaderInfo = cell(length(dicomSeries), 1);
% Loop through each DICOM series
for iDicomSeries = 1:length(dicomSeries)
  % Get DICOM infos for the current series
  dicomInfos = dicomSeries(iDicomSeries).getDicomInfos();
  % Initialize cell array to store DICOM header information for each image in the series
  dicomHeaderImages = cell(length(dicomInfos), 1);
  % Loop through each DICOM image in the series
  for iImages = 1:length(dicomInfos)
    % Get tags list for the current DICOM image
    tagsList = dicomInfos(iImages).getTags();
    tagsListArray = tagsList.toArray();
    % Initialize structure to store DICOM header information
    dicomHeader = struct();
    % Loop through each DICOM tag
    for iDicomTags = 1:length(tagsListArray)
      hexTagValue = dec2hex(tagsListArray(iDicomTags), 8);
      %In the data provided by MIM two different methods are available
      %to access the dicom value of a given tag: getValueArray and
      %getValue. Within getValue there are included variable type
      %conversion from java to Matlab. The getValue will, unfortunately,
      %only return the first dicom value if the true value is a list. So,
      %for e.g. the value "ORIGINAL\PRIMARY\AXIAL", getValue will only return
      %the text "ORIGINAL" since, within the Java implementation, it is a
      %list consisting of "ORIGINAL", "PRIMARY", and "AXIAL". The below
      %code initially uses getValueArray. If the returned values are of
      %type java list (java.lang.Object[]), have a length larger than one,
      %and the content is char, then the individual text parts are pasted
      %together. If the returned type is numeric (including numeric
      %arrays), nothing needs to be done; however, for all other types, the
      %returned getValueArray values will be replaced with the return from
      %getValue to take advantage of the internal Java to Martlab data
      %conversion. The getValue is not used for the numeric values since it
      %does not handle all returned arrays of numeric values correctly, but
      %that is handled correctly by getValueArray.
      dicomVal = dicomInfos(iImages).getValueArray(hexTagValue);
      if isa(dicomVal,'java.lang.Object[]') && length(dicomVal)>1 && isa(dicomVal(1),'char')
        for iJavaPos=1:length(dicomVal)
          if iJavaPos==1
            tempString=dicomVal(iJavaPos);
          else
            tempString=[tempString,'\',dicomVal(iJavaPos)]; %#ok<AGROW>
          end
        end
        dicomVal=tempString;
      else
        if ~isnumeric(dicomVal)
          dicomVal = dicomInfos(iImages).getValue(hexTagValue);
        end
      end
      dicomName = ['Dicom_', hexTagValue(1:4), '_', hexTagValue(5:8)];
      dicomHeader.(dicomName) = dicomVal;
    end
    % Store DICOM header information for the current image, and sort the
    % the fields by name
    dicomHeaderImages{iImages} = orderfields(dicomHeader);
  end
  % Store DICOM header information for the current series
  dicomHeaderInfo{iDicomSeries} = dicomHeaderImages;
end
end