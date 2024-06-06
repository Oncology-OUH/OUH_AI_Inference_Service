classdef codeTestCheckTriggerForSeries < matlab.unittest.TestCase
  methods (TestMethodSetup)
    % Setup for each test
    function addPaths(testCase)
      % Add paths to required functions
      addpath('.\..'); % Add paths as needed
    end
  end

  methods (Test)
    function testTriggerStatusWithValidInput(testCase)
      % Test trigger status with valid input
      dicomHeaders = cell(1, 3);
      dicomHeaders{1} = struct('Dicom_Group1_Element1', 20, 'Dicom_Group1_Element2', 'A','Dicom_0020_0032',[0,0,10]);
      dicomHeaders{2} = struct('Dicom_Group1_Element1', 25, 'Dicom_Group1_Element2', 'A','Dicom_0020_0032',[0,0,20]);
      dicomHeaders{3} = struct('Dicom_Group1_Element1', 20, 'Dicom_Group1_Element2', 'A','Dicom_0020_0032',[0,0,30]);

      aiConfigFile.comparisons.T1_1.DicomGroup = 'Group1';
      aiConfigFile.comparisons.T1_1.DicomElement = 'Element1';
      aiConfigFile.comparisons.T1_1.comparisonOperator = '>';
      aiConfigFile.comparisons.T1_1.Value = '12';

      aiConfigFile.comparisons.T1_2.DicomGroup = 'Group1';
      aiConfigFile.comparisons.T1_2.DicomElement = 'Element2';
      aiConfigFile.comparisons.T1_2.comparisonOperator = '==';
      aiConfigFile.comparisons.T1_2.Value = 'A';

      aiConfigFile.combined.C1_1 = 'T1_1 && T1_2';

      aiConfigFile.trigger = 'C1_1';

      [triggerStatus, consecutive, imagePosAvailable] = checkTriggerForSeries(dicomHeaders, aiConfigFile);

      % Verify trigger status
      expectedTriggerStatus = [true; true; true];
      testCase.verifyEqual(triggerStatus, expectedTriggerStatus, 'Trigger status does not match.');
      
      % Verify consecutive and imagePosAvailable
      testCase.verifyEqual(consecutive, true, 'Consecutive does not match.');
      testCase.verifyEqual(imagePosAvailable, true, 'Image position availability does not match.');
    
      dicomHeaders = cell(1, 3);
      dicomHeaders{1} = struct('Dicom_Group1_Element1', 10, 'Dicom_Group1_Element2', 'A','Dicom_0020_0032',[0,0,10]);
      dicomHeaders{2} = struct('Dicom_Group1_Element1', 25, 'Dicom_Group1_Element2', 'A','Dicom_0020_0032',[0,0,20]);
      dicomHeaders{3} = struct('Dicom_Group1_Element1', 20, 'Dicom_Group1_Element2', 'A','Dicom_0020_0032',[0,0,30]);

      [triggerStatus, consecutive, imagePosAvailable] = checkTriggerForSeries(dicomHeaders, aiConfigFile);

      % Verify trigger status
      expectedTriggerStatus = [false; true; true];
      testCase.verifyEqual(triggerStatus, expectedTriggerStatus, 'Trigger status does not match.');
      
      % Verify consecutive and imagePosAvailable
      testCase.verifyEqual(consecutive, true, 'Consecutive does not match.');
      testCase.verifyEqual(imagePosAvailable, true, 'Image position availability does not match.');
    end
  end
end