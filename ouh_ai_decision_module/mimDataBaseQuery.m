% function mungoString = mimDataBaseQuery(query, varargin)
%
% Summary:
%   Queries a specified MongoDB database using mongosh based on the provided query.
%
% Input:
%   query: Database query in JSON like format.
%
% Optional Input:
%   - ip: IP address of the database. Default is '127.0.0.1'.
%   - port: Communication port of the database. Default is 34543.
%   - dataBaseName: Name of the database. Default is 'metabase_v2'.
%   - fileNameForMongosh: Path to the mongosh terminal program, including the filename (e.g., 'mongosh').
%   - collectionName: Name of the collection to query
%   - getCollectionNames: true or false (default false); if true, only the names of the available collections will be returned independent of a specific query

%
% Output:
%   mungoString: Result of the database query.
%
% Details:
%   The function uses the mongosh terminal program to query the specified MongoDB
%   database based on the provided query. The result is returned as a string.
%
% Example:
%   query = '{"100020":"ptid"},{"mimdata.folders":1,"mimdata.sopInstanceUids": 1 }';
%   result = mimDataBaseQuery(query, 'ip', '127.0.0.1', 'port', 27017);
%
%   query = '';
%   result = mimDataBaseQuery(query, 'getCollectionNames',true);
%
%   query = '';
%   mungoString =mimDataBaseQuery(query, 'collectionName','patientLists');
%
% Author: CaB
% Date: 2023-11-15


function mungoString=mimDataBaseQuery(query,varargin)
inputParam = inputParser;
addParameter(inputParam,'ip','127.0.0.1',@ischar);
addParameter(inputParam,'port',34543,@isnumeric);
addParameter(inputParam,'dataBaseName','metabase_v2',@ischar);
addParameter(inputParam,'fileNameForMongosh','C:\MIM_scripting_matlab\mongosh-2.0.2-win32-x64\bin\mongosh',@ischar);
addParameter(inputParam,'collectionName','dicom',@ischar);
addParameter(inputParam,'getCollectionNames',false,@islogical);
parse(inputParam,varargin{:});
inputval=inputParam.Results;

%Write a temp file that will be used when calling mongosh (mongo shell)
fileName=tempname;
fileID = fopen(fileName,'w');
textLine=['db=connect("',inputval.ip,':',num2str(inputval.port),'/',inputval.dataBaseName,'");\n'];
[~]=fprintf(fileID,textLine);
%textLine='DBQuery.shellBatchSize = 10000;\n';
textLine='config.set("displayBatchSize",10000);\n';
[~]=fprintf(fileID,textLine);
if inputval.getCollectionNames
  textLine='printjson(db.getCollectionNames())\n';
else
  textLine=['printjson(db.',inputval.collectionName,'.find(',query,').batchSize(100000))\n'];
end
[~]=fprintf(fileID,textLine);
%textLine='db.close()';
%[~]=fprintf(fileID,textLine);
fclose(fileID);
command=[inputval.fileNameForMongosh,' -nodb --file ',fileName];
[~,mungoString] = system(command);
% if ~inputval.getCollectionNames && status~=1
%     ME.message='The call to the Mungo database was not successful';
%     ME.identifier='MATLAB:mungoCall:WrongOutputFormatFromDataBase';
%     error(ME);
% end
delete(fileName);
end