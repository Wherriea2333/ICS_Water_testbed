PROGRAM RawWater
  VAR
    P101 AT %QX0.0 : BOOL;
    P101_INPUT AT %IX0.0 : BOOL;
    P102 AT %QX0.1 : BOOL;
    P102_INPUT AT %IX0.1 : BOOL;
    MV101 AT %QX0.2 : BOOL;
    MV101_INPUT AT %IX0.2 : BOOL;
    ContainerMaxVolume AT %QW0 : INT;
    ContainerMaxVolume_INPUT AT %IW0 : INT;
    LIT101 AT %QW1 : INT;
    LIT101_INPUT AT %IW1 : INT;
    FIT101 AT %QW2 : INT;
    FIT101_INPUT AT %IW2 : INT;
    FIT201 AT %QW3 : INT;
    FIT201_INPUT AT %IW3 : INT;
  END_VAR

  ContainerMaxVolume := ContainerMaxVolume_INPUT;
  FIT101 := FIT101_INPUT;
  FIT201 := FIT201_INPUT;
  LIT101 := LIT101_INPUT;
END_PROGRAM


CONFIGURATION Config0

  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#20ms,PRIORITY := 0);
    PROGRAM instance0 WITH task0 : RawWater;
  END_RESOURCE
END_CONFIGURATION