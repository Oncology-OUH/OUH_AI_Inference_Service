classdef codeTestWriteConfigToAISystem < matlab.unittest.TestCase
  methods (TestMethodSetup)
    % Setup for each test
    function setPath(testCase)
      addpath('.\..');
    end
  end
  methods (Test)
    function testWriteValidConfig(testCase)
      % Test writing a valid configuration
      configInfo.configAI.ModelName = 'MyModel';
      configInfo.configAI.ModelHash = 'a1b2c3';
      configInfo.configAI.SendDirectory = '/path/to/send';
      dirPath = tempdir;
      configFileName = 'config.txt';
      status = writeConfigToAISystem(configInfo, dirPath, configFileName);

      % Verify that the file was written successfully
      testCase.verifyEqual(status, 1);
      delete(fullfile(dirPath,configFileName));
    end
  end
end