classdef codeTestReadAllUserConfigFiles < matlab.unittest.TestCase
  methods (TestMethodSetup)
    % Setup for each test
    function setPath(testCase)
      addpath('.\..');
    end
  end
  methods (Test)
    function testReadAllUserConfigFilesWithValidDirectory(testCase)
      % Test reading all user-defined AI configuration files from a valid directory
      configDir = tempname;
      % Create some dummy configuration files in the specified directory
      createDummyConfigFiles(configDir);
      % Call the function to read user configurations
      userConfigs = readAllUserConfigFiles(configDir);
      % Verify that the output is a cell array
      testCase.assertClass(userConfigs, 'cell', 'Unexpected output class');
      % Verify that the number of parsed configurations is as expected
      expectedNumConfigs = 2;  % Adjust based on the number of dummy files created
      testCase.verifyEqual(length(userConfigs), expectedNumConfigs, 'Unexpected number of parsed configurations');
      % Clean up: Delete dummy configuration files
      deleteDummyConfigFiles(configDir);
    end

    function testReadAllUserConfigFilesWithInvalidDirectory(testCase)
      % Test reading user-defined AI configuration files from an invalid directory
      configDir = 'path/to/invalid/configs';
      % Call the function and verify that it raises an error
      testCase.assertError(@() readAllUserConfigFiles(configDir), 'MATLAB:mainAiDecisionModule:CouldNotReadUserConfigFile');
    end
  end
end

function createDummyConfigFiles(configDir)
% Helper function to create dummy configuration files for testing
% Create two dummy configuration files in the specified directory
pathToDir=configDir;
if ~exist(pathToDir,'dir')
  mkdir(pathToDir)
end
dummyConfig1 = fopen(fullfile(pathToDir, 'config1.txt'), 'w');
fprintf(dummyConfig1,'T1_1:(0014,0015) Body Part Examined == "NECK"\n');
fprintf(dummyConfig1,'C1_1: T1_1\n');
fprintf(dummyConfig1,'Trigger:C1_1\n');
fprintf(dummyConfig1,'ModelName: "DummyModel1"\n');
fprintf(dummyConfig1,'ModelHash:"848b598eb4bac4e83bab28d82cb949a1"\n');
fprintf(dummyConfig1,'SendDirectory:"\\os210378\\AI_Inference"\n');
fprintf(dummyConfig1,'NiceLevel:"2"\n');
fprintf(dummyConfig1,'EmptyStructWithModelName:"true"\n');
fprintf(dummyConfig1,'ReturnDicomNodeIP_1:"srvodedcmrfl01v.rsyd.net" #If dicom is used all both IP, PORT and AET should be present\n');
fprintf(dummyConfig1,'ReturnDicomNodePort_1:"106"\n');
fprintf(dummyConfig1,'ReturnDicomNodeAET_1: "DUMP"\n');
fprintf(dummyConfig1,'ReturnDirectory:"\\\\prapprflstg01\\TempIdentifiableData\\CB\\AI_model_results\\HNModel"\n');
fprintf(dummyConfig1,'ReturnEmptyStructName:"true"\n'); 

fclose(dummyConfig1);

dummyConfig2 = fopen(fullfile(pathToDir, 'config2.txt'), 'w');
fprintf(dummyConfig2,'T1_1:(0014,0015) Body Part Examined == "NECK"\n');
fprintf(dummyConfig2,'C1_1: T1_1\n');
fprintf(dummyConfig2,'Trigger:C1_1\n');
fprintf(dummyConfig2,'ModelName: "DummyModel2"\n');
fprintf(dummyConfig2,'ModelHash:"848b598eb4bac4e83bab28d82cb949a1"\n');
fprintf(dummyConfig2,'SendDirectory:"\\os210378\\AI_Inference"\n');
fprintf(dummyConfig2,'NiceLevel:"2"\n');
fprintf(dummyConfig2,'EmptyStructWithModelName:"true"\n');
fprintf(dummyConfig2,'ReturnDicomNodeIP_1:"srvodedcmrfl01v.rsyd.net" #If dicom is used all both IP, PORT and AET should be present\n');
fprintf(dummyConfig2,'ReturnDicomNodePort_1:"106"\n');
fprintf(dummyConfig2,'ReturnDicomNodeAET_1: "DUMP"\n');
fprintf(dummyConfig2,'ReturnDirectory:"\\\\prapprflstg01\\TempIdentifiableData\\CB\\AI_model_results\\HNModel"\n');
fprintf(dummyConfig2,'ReturnEmptyStructName:"true"\n'); 

fclose(dummyConfig2);
end

function deleteDummyConfigFiles(configDir)
% Helper function to delete dummy configuration files after testing
delete(fullfile(configDir,'*'));
rmdir(configDir);
end