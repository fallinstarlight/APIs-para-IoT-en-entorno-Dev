DELIMITER $$

CREATE PROCEDURE spCreateVehicle(
    IN pName VARCHAR(80),
    IN pModel VARCHAR(80),
    IN pDescription VARCHAR(255),
    IN pMicrocontroller VARCHAR(50)
)
BEGIN
    INSERT INTO vehicles(name, model, description, microcontroller)
    VALUES(pName, pModel, pDescription, pMicrocontroller);

    SELECT LAST_INSERT_ID() AS vehicleId;
END$$

CREATE PROCEDURE spGetVehicles()
BEGIN
    SELECT * FROM vehicles ORDER BY vehicleId;
END$$

CREATE PROCEDURE spGetVehicle(IN pVehicleId INT)
BEGIN
    SELECT * FROM vehicles WHERE vehicleId = pVehicleId;
END$$

CREATE PROCEDURE spUpdateVehicle(
    IN pVehicleId INT,
    IN pName VARCHAR(80),
    IN pModel VARCHAR(80),
    IN pDescription VARCHAR(255),
    IN pMicrocontroller VARCHAR(50),
    IN pIsActive BOOLEAN
)
BEGIN
    UPDATE vehicles
       SET name=pName, model=pModel, description=pDescription,
           microcontroller=pMicrocontroller, isActive=pIsActive
     WHERE vehicleId=pVehicleId;
END$$

CREATE PROCEDURE spDeleteVehicle(IN pVehicleId INT)
BEGIN
    DELETE FROM vehicles WHERE vehicleId=pVehicleId;
END$$

CREATE PROCEDURE spCreateCommand(
    IN pVehicleId INT,
    IN pName VARCHAR(60),
    IN pCode INT,
    IN pDescription VARCHAR(255)
)
BEGIN
    INSERT INTO commands(vehicleId, name, code, description)
    VALUES(pVehicleId, pName, pCode, pDescription);

    SELECT LAST_INSERT_ID() AS commandId;
END$$

CREATE PROCEDURE spGetVehicleCommands(IN pVehicleId INT)
BEGIN
    SELECT * FROM commands
     WHERE vehicleId=pVehicleId
     ORDER BY code;
END$$

CREATE PROCEDURE spUpdateCommand(
    IN pCommandId INT,
    IN pName VARCHAR(60),
    IN pCode INT,
    IN pDescription VARCHAR(255),
    IN pIsActive BOOLEAN
)
BEGIN
    UPDATE commands
       SET name=pName, code=pCode,
           description=pDescription, isActive=pIsActive
     WHERE commandId=pCommandId;
END$$

CREATE PROCEDURE spDeleteCommand(IN pCommandId INT)
BEGIN
    DELETE FROM commands WHERE commandId=pCommandId;
END$$

CREATE PROCEDURE spUpdateStatus(
    IN pVehicleId INT,
    IN pCommandId INT,
    IN pIsConnected BOOLEAN
)
BEGIN
    INSERT INTO vehicleStatus(vehicleId, commandId, isConnected)
    VALUES(pVehicleId, pCommandId, pIsConnected)
    ON DUPLICATE KEY UPDATE
      commandId=VALUES(commandId),
      isConnected=VALUES(isConnected),
      lastUpdate=CURRENT_TIMESTAMP;
END$$

CREATE PROCEDURE spGetStatus(IN pVehicleId INT)
BEGIN
    SELECT s.vehicleId, v.name AS vehicleName,
           s.commandId, c.name AS commandName, c.code,
           s.isConnected, s.lastUpdate
      FROM vehicleStatus s
      JOIN vehicles v ON v.vehicleId=s.vehicleId
 LEFT JOIN commands c ON c.commandId=s.commandId
     WHERE s.vehicleId=pVehicleId;
END$$

CREATE PROCEDURE spRegisterHistory(
    IN pVehicleId INT,
    IN pCommandId INT,
    IN pSource VARCHAR(30)
)
BEGIN
    INSERT INTO commandHistory(vehicleId, commandId, source)
    VALUES(pVehicleId, pCommandId, pSource);
END$$

CREATE PROCEDURE spGetHistory(IN pVehicleId INT)
BEGIN
    SELECT h.historyId, h.vehicleId,
           c.name AS commandName, c.code,
           h.timestamp, h.source
      FROM commandHistory h
 LEFT JOIN commands c ON c.commandId=h.commandId
     WHERE h.vehicleId=pVehicleId
     ORDER BY h.timestamp DESC, h.historyId DESC LIMIT 10;
END$$

CREATE PROCEDURE spCreateDemo(
    IN pVehicleId INT,
    IN pName VARCHAR(80),
    IN pDescription VARCHAR(255)
)
BEGIN
    INSERT INTO demos(vehicleId, name, description)
    VALUES(pVehicleId, pName, pDescription);

    SELECT LAST_INSERT_ID() AS demoId;
END$$

CREATE PROCEDURE spGetDemos(IN pVehicleId INT)
BEGIN
    SELECT * FROM demos
     WHERE vehicleId=pVehicleId
     ORDER BY demoId;
END$$

CREATE PROCEDURE spUpdateDemo(
    IN pDemoId INT,
    IN pName VARCHAR(80),
    IN pDescription VARCHAR(255),
    IN pIsActive BOOLEAN
)
BEGIN
    UPDATE demos
       SET name=pName, description=pDescription, isActive=pIsActive
     WHERE demoId=pDemoId;
END$$

CREATE PROCEDURE spDeleteDemo(IN pDemoId INT)
BEGIN
    DELETE FROM demos WHERE demoId=pDemoId;
END$$

CREATE PROCEDURE spAddDemoMovement(
    IN pDemoId INT,
    IN pCommandId INT,
    IN pSortOrder INT,
    IN pDurationMs INT,
    IN pPauseMs INT
)
BEGIN
    INSERT INTO demoMovements
      (demoId, commandId, sortOrder, durationMs, pauseMs)
    VALUES
      (pDemoId, pCommandId, pSortOrder, pDurationMs, pPauseMs);
END$$

CREATE PROCEDURE spGetDemoMovements(IN pDemoId INT)
BEGIN
    SELECT dm.demoMovementId, dm.sortOrder,
           dm.commandId, c.name AS commandName, c.code,
           dm.durationMs, dm.pauseMs
      FROM demoMovements dm
      JOIN commands c ON c.commandId=dm.commandId
     WHERE dm.demoId=pDemoId
     ORDER BY dm.sortOrder;
END$$

CREATE PROCEDURE spUpdateDemoMovement(
    IN pDemoMovementId INT,
    IN pCommandId INT,
    IN pSortOrder INT,
    IN pDurationMs INT,
    IN pPauseMs INT
)
BEGIN
    UPDATE demoMovements
       SET commandId=pCommandId, sortOrder=pSortOrder,
           durationMs=pDurationMs, pauseMs=pPauseMs
     WHERE demoMovementId=pDemoMovementId;
END$$

CREATE PROCEDURE spDeleteDemoMovement(IN pDemoMovementId INT)
BEGIN
    DELETE FROM demoMovements
     WHERE demoMovementId=pDemoMovementId;
END$$

CREATE PROCEDURE spGetDemoVehicleId(IN pDemoId INT)
BEGIN
    SELECT vehicleId FROM demos WHERE demoId = pDemoId;
END$$

DELIMITER ;