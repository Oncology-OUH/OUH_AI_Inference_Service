classdef codeTestParseMungoOutput < matlab.unittest.TestCase
  methods (TestMethodSetup)
    % Setup for each test
    function setPath(testCase)
      addpath('.\..');
    end
  end
  methods (Test)
    function testParseMungoOutputWithString(testCase)
      % Test parsing Mungo output with a string value
      mungoString = '["TestString"]';
      parsedOutput = parseMungoOutput(mungoString);
      expectedOutput{1} = 'TestString';
      testCase.verifyEqual(parsedOutput, expectedOutput, 'Unexpected parsed output');
    end

    function testParseMungoOutputWithNumericValue(testCase)
      % Test parsing Mungo output with a numeric value
      mungoString = '[42]';
      parsedOutput = parseMungoOutput(mungoString);
      expectedOutput{1} = 42;
      testCase.verifyEqual(parsedOutput, expectedOutput, 'Unexpected parsed output');
    end

    function testParseMungoOutputWithTrueValue(testCase)
      % Test parsing Mungo output with a true value
      mungoString = '[true]';
      parsedOutput = parseMungoOutput(mungoString);
      expectedOutput{1} = true;
      testCase.verifyEqual(parsedOutput, expectedOutput, 'Unexpected parsed output');
    end

    function testParseMungoOutputWithFalseValue(testCase)
      % Test parsing Mungo output with a false value
      mungoString = '[false]';
      parsedOutput = parseMungoOutput(mungoString);
      expectedOutput{1} = false;
      testCase.verifyEqual(parsedOutput, expectedOutput, 'Unexpected parsed output');
    end

    function testParseMungoOutputWithNullValue(testCase)
      % Test parsing Mungo output with a null value
      mungoString = '[null]';
      parsedOutput = parseMungoOutput(mungoString);
      expectedOutput{1} = NaN;
      testCase.verifyEqual(parsedOutput, expectedOutput, 'Unexpected parsed output');
    end

    function testParseMungoOutputWithList(testCase)
      % Test parsing Mungo output with a list
      mungoString = '[1, "two", 3.0, false, [4, "five"], "six"]';
      parsedOutput = parseMungoOutput(mungoString);
      expectedOutput = {1; 'two'; 3.0; false; {4; 'five'}; 'six'};
      testCase.verifyEqual(parsedOutput, expectedOutput, 'Unexpected parsed output');
    end

    function testParseMungoOutputWithObject(testCase)
      % Test parsing Mungo output with an object
      mungoString = '[{key1: "value1", key2: [1, 2, 3], key3: true}]';
      parsedOutput = parseMungoOutput(mungoString);
      expectedOutput{1}.key1 = 'value1';
      expectedOutput{1}.key2 = {1; 2; 3};
      expectedOutput{1}.key3 = true;
      testCase.verifyEqual(parsedOutput, expectedOutput, 'Unexpected parsed output');
    end

    function testParseMungoOutputWithComplexStructure(testCase)
      % Test parsing Mungo output with a complex structure
      mungoString = '[{key1: "value1", key2: [1, {key3: 2.5, key4: false}, 3], key5: true}]';
      parsedOutput = parseMungoOutput(mungoString);
      expectedOutput{1}.key1 = 'value1';
      expectedOutput{1}.key2 = {1; struct('key3',2.5, 'key4', false); 3};
      expectedOutput{1}.key5 = true;
      testCase.verifyEqual(parsedOutput, expectedOutput, 'Unexpected parsed output');
    end
  end
end