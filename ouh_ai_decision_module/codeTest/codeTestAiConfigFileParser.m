classdef codeTestAiConfigFileParser < matlab.unittest.TestCase
  properties
    funcHandles
  end

  methods (TestClassSetup)
    % Shared setup for the entire test class

  end
  methods (TestMethodSetup)
    % Setup for each test
    function setPath(testCase)
      addpath('.\..');
      testCase.funcHandles=aiConfigFileParser('','GetSubFunctionHandles',true);
    end
  end

  methods (Test)
    % Test methods
    
    %% Test for fucntion readConfigFile
    %Test that reading the config file provide the expected result
    function readConfigFile(testCase)
      aiConfigFilePath='MinimalExample.txt';
      actSolution=testCase.funcHandles.readConfigFile(aiConfigFilePath);
      load('linesInConfigTrueSolution.mat','-mat','trueSolution');
      compareActualAndTrue=isequal(actSolution,trueSolution);
      testCase.verifyEqual(compareActualAndTrue,true);
    end
    %% Test for function readComparison
    function readComparison(testCase)
      compareActualAndTrue=true;
      inputLine='T2_4 : (0018,0050) Slice Thickness > "2.5"';
      [actSolutionName,actSolutionComparison]=testCase.funcHandles.readComparison(inputLine);
      compareActualAndTrue=compareActualAndTrue && strcmp(actSolutionName,'T2_4');
      compareActualAndTrue=compareActualAndTrue && strcmp(actSolutionComparison.DicomGroup,'0018');
      compareActualAndTrue=compareActualAndTrue && strcmp(actSolutionComparison.DicomElement,'0050');
      compareActualAndTrue=compareActualAndTrue && strcmp(actSolutionComparison.comparisonOperator,'>');
      compareActualAndTrue=compareActualAndTrue && strcmp(actSolutionComparison.Value,'2.5');

      inputLine='T2_4 : (0018,0050) Slice Thickness >= "2.5"';
      [~,actSolutionComparison]=testCase.funcHandles.readComparison(inputLine);
      compareActualAndTrue=compareActualAndTrue && strcmp(actSolutionComparison.comparisonOperator,'>=');

      inputLine='T2_4 : (0018,0050) Slice Thickness <= "2.5"';
      [~,actSolutionComparison]=testCase.funcHandles.readComparison(inputLine);
      compareActualAndTrue=compareActualAndTrue && strcmp(actSolutionComparison.comparisonOperator,'<=');

      inputLine='T2_4 : (0018,0050) Slice Thickness < "2.5"';
      [~,actSolutionComparison]=testCase.funcHandles.readComparison(inputLine);
      compareActualAndTrue=compareActualAndTrue && strcmp(actSolutionComparison.comparisonOperator,'<');

      inputLine='T2_4 : (0018,0050) Slice Thickness == "2.5"';
      [~,actSolutionComparison]=testCase.funcHandles.readComparison(inputLine);
      compareActualAndTrue=compareActualAndTrue && strcmp(actSolutionComparison.comparisonOperator,'==');

      inputLine='T2_4 : (0018,0050) Slice Thickness ~= "2.5"';
      [~,actSolutionComparison]=testCase.funcHandles.readComparison(inputLine);
      compareActualAndTrue=compareActualAndTrue && strcmp(actSolutionComparison.comparisonOperator,'~=');

      testCase.verifyEqual(compareActualAndTrue,true);
    end
    function readComparisonWrongTName(testCase)
      inputLine='X2_4 : (0018,0050) Slice Thickness > "2.5"';
      verifyError(testCase,@() testCase.funcHandles.readComparison(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function readComparisonWrongDicomTag(testCase)
      inputLine='X2_4 : (0018,0X50) Slice Thickness > "2.5"';
      verifyError(testCase,@() testCase.funcHandles.readComparison(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function readComparisonWrongTextBetweenNameAndDicomTag(testCase)
      inputLine='X2_4 : )(0018,0X50) Slice Thickness > "2.5"';
      verifyError(testCase,@() testCase.funcHandles.readComparison(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    %% Test for function isStringLogicalStatement
    function isStringLogicalStatement(testCase)
      %Start test with some that should vealute to true
      inputLine='(T2_1 ||   T2_2)    &&    T2_3 && T2_4';
      actualValue=testCase.funcHandles.isStringLogicalStatement(inputLine);
      inputLine='((T2_10 || T2_2) && ((~T2_3)) && T2_4)';
      actualValue=actualValue && testCase.funcHandles.isStringLogicalStatement(inputLine);
      inputLine='((C2_10 || T2_2) && ((~T2_3)) && T2_4)';
      actualValue=actualValue && testCase.funcHandles.isStringLogicalStatement(inputLine);

      %Now test some that should evaluate to false
      inputLine='(T2_1 xx || T2_2) && T2_3 && T2_4';
      actualValue=actualValue && ~testCase.funcHandles.isStringLogicalStatement(inputLine);
      inputLine='(T2_1    (|| T2_2=) && T2_3 && T2_4';
      actualValue=actualValue && ~testCase.funcHandles.isStringLogicalStatement(inputLine);
      inputLine='(T2_1)())';
      actualValue=actualValue && ~testCase.funcHandles.isStringLogicalStatement(inputLine);

      verifyEqual(testCase,actualValue,true);
    end
    %% test for function readCombined
    function readCombined(testCase)
      compareActualAndTrue=true;
      inputLine = '   C2_2   :   (T2_1 || T2_2) && T2_3 && T2_4   ';
      [actualCombineName,actualCombined]=testCase.funcHandles.readCombined(inputLine);
      compareActualAndTrue = compareActualAndTrue && strcmp(actualCombineName,'C2_2');
      compareActualAndTrue = compareActualAndTrue && strcmp(actualCombined,'(T2_1 || T2_2) && T2_3 && T2_4');
      verifyEqual(testCase,compareActualAndTrue,true);
    end
    function readCombinedWrongInput1(testCase)
      inputLine='C2_2 : (T2_1 xx || T2_2) && T2_3 && T2_4';
      verifyError(testCase,@() testCase.funcHandles.readCombined(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function readCombinedWrongInput2(testCase)
      inputLine='C2_2 : (T2_1 (|| T2_2) && T2_3 && T2_4';
      verifyError(testCase,@() testCase.funcHandles.readCombined(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    %% test for function readTrigger
    function readTrigger(testCase)
      inputLine = '   Trigger   :   (C2_1 || T2_2) && C2_34   ';
      compareActualAndTrue=strcmp(testCase.funcHandles.readTrigger(inputLine),'(C2_1 || T2_2) && C2_34');
      verifyEqual(testCase,compareActualAndTrue,true);
    end
    function readTriggerWrongInput1(testCase)
      inputLine = '   Trigger  x :   (C2_1 || T2_2) && C2_34   ';
      verifyError(testCase,@() testCase.funcHandles.readTrigger(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function readTriggerWrongInput2(testCase)
      inputLine = '   Trigger  :   ()C2_1 || T2_2) && C2_34   ';
      verifyError(testCase,@() testCase.funcHandles.readTrigger(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    %% test for the function readAIConfig
    function readAIConfig(testCase)
      compareActualAndTrue=true;
      inputLine = '   TestItem  :  This is a test  ';
      [actualAiConfigName,actualAiConfig]=testCase.funcHandles.readAIConfig(inputLine);
      compareActualAndTrue=compareActualAndTrue && strcmp(actualAiConfigName,'TestItem');
      compareActualAndTrue=compareActualAndTrue && strcmp(actualAiConfig,'This is a test');
      verifyEqual(testCase,compareActualAndTrue,true);
    end
    function readAIConfigWrongInput1(testCase)
      inputLine = '   TestItem  This is a test  ';
      verifyError(testCase,@() testCase.funcHandles.readAIConfig(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function readAIConfigWrongInput2(testCase)
      inputLine = ':  This is a test  ';
      verifyError(testCase,@() testCase.funcHandles.readAIConfig(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function readAIConfigWrongInput3(testCase)
      inputLine = 'Item   :  ';
      verifyError(testCase,@() testCase.funcHandles.readAIConfig(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function readAIConfigWrongInput4(testCase)
      inputLine = 'Struct_1: "InterStructName1" "Bladder_AI" "Organ" "[257,0,0]" "2"';
      verifyError(testCase,@() testCase.funcHandles.readAIConfig(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function readAIConfigWrongInput5(testCase)
      inputLine = 'Struct_1:  "Bladder_AI" "Organ" "[254,0,0]" "2"';
      verifyError(testCase,@() testCase.funcHandles.readAIConfig(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function readAIConfigWrongInput6(testCase)
      inputLine = 'ModelName:""';
      verifyError(testCase,@() testCase.funcHandles.readAIConfig(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function readAIConfigWrongInput7(testCase)
      inputLine = 'NiceLevel:"High"';
      verifyError(testCase,@() testCase.funcHandles.readAIConfig(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function readAIConfigWrongInput8(testCase)
      inputLine = 'ReturnDicomNodeAET_1: ""';
      verifyError(testCase,@() testCase.funcHandles.readAIConfig(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function readAIConfigWrongInput9(testCase)
      inputLine = 'EmptyStructWithModelName:"1"';
      verifyError(testCase,@() testCase.funcHandles.readAIConfig(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function readAIConfigWrongInput10(testCase)
      inputLine = 'InferenceMaxRunTime : "x65"';
      verifyError(testCase,@() testCase.funcHandles.readAIConfig(inputLine),'MATLAB:aiConfigFileParser:WrongUserInput');
    end

    %% Test for function checkConfigInfo
    function checkConfigInfoWrongInput1(testCase)
      aiConfigFilePath='MinimalExample.txt';
      actSolution=aiConfigFileParser(aiConfigFilePath);
      actSolution.configAI=rmfield(actSolution.configAI,'ModelName');
      verifyError(testCase,@() testCase.funcHandles.checkConfigInfo(actSolution),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function checkConfigInfoWrongInput2(testCase)
      aiConfigFilePath='MinimalExample.txt';
      actSolution=aiConfigFileParser(aiConfigFilePath);
      actSolution.configAI=rmfield(actSolution.configAI,'ModelHash');
      verifyError(testCase,@() testCase.funcHandles.checkConfigInfo(actSolution),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function checkConfigInfoWrongInput3(testCase)
      aiConfigFilePath='MinimalExample.txt';
      actSolution=aiConfigFileParser(aiConfigFilePath);
      actSolution.configAI=rmfield(actSolution.configAI,'ReturnDicomNodePort_1');
      verifyError(testCase,@() testCase.funcHandles.checkConfigInfo(actSolution),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    function checkConfigInfoWrongInput4(testCase)
      aiConfigFilePath='MinimalExample.txt';
      actSolution=aiConfigFileParser(aiConfigFilePath);
      actSolution.configAI=rmfield(actSolution.configAI,'ReturnDicomNodeAET_1');
      verifyError(testCase,@() testCase.funcHandles.checkConfigInfo(actSolution),'MATLAB:aiConfigFileParser:WrongUserInput');
    end
    %% Test for function aiConfigFileParser
    function aiConfigFileParser(testCase)
      aiConfigFilePath='MinimalExample.txt';
      actSolution=aiConfigFileParser(aiConfigFilePath);
      load('MinimalExampleResult.mat','-mat','trueSolution')
      compareActualAndTrue=isequal(actSolution,trueSolution);
      testCase.verifyEqual(compareActualAndTrue,true);
    end
  end
end