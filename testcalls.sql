USE IotVehicle;
SELECT * FROM commands;
SELECT * FROM demos;

CALL spCreateVehicle(
  'Starlight\'s Haul Truck',
  'Indiscipline',
  'ESP8266-controlled construction vehicle',
  'ESP8266'
);

CALL spCreateCommand(1, 'FORWARD',       1, 'Move the vehicle forward');
CALL spCreateCommand(1, 'BACKWARD',      2, 'Move the vehicle backward');
CALL spCreateCommand(1, 'TURN_LEFT',     3, 'Turn left');
CALL spCreateCommand(1, 'TURN_RIGHT',    4, 'Turn right');
CALL spCreateCommand(1, 'RAISE_LOAD',    5, 'Raise the load');
CALL spCreateCommand(1, 'LOWER_LOAD',    6, 'Lower the load');
CALL spCreateCommand(1, 'TOGGLE_LIGHTS', 7, 'Toggle lights');
CALL spCreateCommand(1, 'TOGGLE_SOUND',  8, 'Toggle sound');
CALL spCreateCommand(1, 'STOP',          0, 'Stop any movement');

CALL spUpdateStatus(1, 9, 1);

CALL spRegisterHistory(1, 1, 'WORKBENCH');
CALL spRegisterHistory(1, 3, 'WORKBENCH');
CALL spRegisterHistory(1, 5, 'WORKBENCH');
CALL spRegisterHistory(1, 7, 'WORKBENCH');
CALL spRegisterHistory(1, 9, 'WORKBENCH');

CALL spRegisterHistory(1, 6, 'ATOTONILCO');
CALL spRegisterHistory(1, 4, 'ATOTONILCO');
CALL spRegisterHistory(1, 5, 'ATOTONILCO');

CALL spGetHistory(1);

CALL spCreateDemo(
  1,
  'Main demo',
  'Automatic vehicle movement sequence'
);

CALL spAddDemoMovement(1, 1, 1, 2000, 400);
CALL spAddDemoMovement(1, 3, 2, 1000, 300);
CALL spAddDemoMovement(1, 5, 3, 1500, 300);
CALL spAddDemoMovement(1, 7, 4, 900,  250);
CALL spAddDemoMovement(1, 8, 5, 900,  250);
CALL spAddDemoMovement(1, 6, 6, 1500, 300);
CALL spAddDemoMovement(1, 2, 7, 2000, 400);
CALL spAddDemoMovement(1, 9, 8, 500,  0);

CALL spGetVehicles();
CALL spGetVehicleCommands(1);
CALL spGetStatus(1);
CALL spGetHistory(1);
CALL spGetDemos(1);
CALL spGetDemoMovements(2);

CALL spCreateDemo(
  1,
  'Random demo',
  'Automatic sequence with random movements and timings'
);

CALL spAddDemoMovement(2, 4, 1,  1750, 320);  -- TURN_RIGHT
CALL spAddDemoMovement(2, 1, 2,  2300, 150);  -- FORWARD
CALL spAddDemoMovement(2, 7, 3,  600,  480);  -- TOGGLE_LIGHTS
CALL spAddDemoMovement(2, 3, 4,  1200, 275);  -- TURN_LEFT
CALL spAddDemoMovement(2, 5, 5,  1900, 400);  -- RAISE_LOAD
CALL spAddDemoMovement(2, 8, 6,  750,  220);  -- TOGGLE_SOUND
CALL spAddDemoMovement(2, 2, 7,  2100, 350);  -- BACKWARD
CALL spAddDemoMovement(2, 6, 8,  1400, 300);  -- LOWER_LOAD
CALL spAddDemoMovement(2, 4, 9,  950,  500);  -- TURN_RIGHT
CALL spAddDemoMovement(2, 1, 10, 2600, 100);  -- FORWARD
CALL spAddDemoMovement(2, 9, 11, 450,  0);    -- STOP

CALL spGetDemos(1);
CALL spGetDemoMovements(2);