classdef codeTestWriteToLog < matlab.unittest.TestCase
  methods (TestMethodSetup)
    % Setup for each test
    function setPath(testCase)
      addpath('.\..');
    end
  end
  methods (Test)
    function testWriteToLogWithValidInput(testCase)
      % Test writing information to a log file with valid input
      informationString = 'Test log entry.';
      configDecisionModule.pathToLogFilesDir = tempname;
      mkdir(configDecisionModule.pathToLogFilesDir);

      % Call the function to write to the log
      writeToLog(informationString, configDecisionModule);

      % Verify that the log file is created
      stringDate=char(datetime('today','Format','yyyy_MM_dd'));
      logFileName = fullfile(configDecisionModule.pathToLogFilesDir, [stringDate, '_logFileDecisionModule.txt']);
      testCase.assertGreaterThan(exist(logFileName, 'file'), 0, 'Log file not created.');

      % Clean up: Delete the log file
      delete(logFileName);
      rmdir(configDecisionModule.pathToLogFilesDir);
    end

  end
end