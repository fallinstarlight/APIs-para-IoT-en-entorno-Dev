
CREATE DATABASE IF NOT EXISTS IotVehicle
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
USE IotVehicle;

CREATE TABLE vehicles (
    vehicleId INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    model VARCHAR(80),
    description VARCHAR(255),
    microcontroller VARCHAR(50),
    registrationDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    isActive BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE commands (
    commandId INT AUTO_INCREMENT PRIMARY KEY,
    vehicleId INT NOT NULL,
    name VARCHAR(60) NOT NULL,
    code INT NOT NULL,
    description VARCHAR(255),
    isActive BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uqCommandCode UNIQUE (vehicleId, code),
    CONSTRAINT uqCommandName UNIQUE (vehicleId, name),
    CONSTRAINT fkCommandVehicle
      FOREIGN KEY (vehicleId) REFERENCES vehicles(vehicleId)
      ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE vehicleStatus (
    statusId INT AUTO_INCREMENT PRIMARY KEY,
    vehicleId INT NOT NULL UNIQUE,
    commandId INT NULL,
    lastUpdate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      ON UPDATE CURRENT_TIMESTAMP,
    isConnected BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fkStatusVehicle
      FOREIGN KEY (vehicleId) REFERENCES vehicles(vehicleId)
      ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fkStatusCommand
      FOREIGN KEY (commandId) REFERENCES commands(commandId)
      ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE commandHistory (
    historyId BIGINT AUTO_INCREMENT PRIMARY KEY,
    vehicleId INT NOT NULL,
    commandId INT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(30) NOT NULL DEFAULT 'MANUAL',
    CONSTRAINT fkHistoryVehicle
      FOREIGN KEY (vehicleId) REFERENCES vehicles(vehicleId)
      ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fkHistoryCommand
      FOREIGN KEY (commandId) REFERENCES commands(commandId)
      ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE demos (
    demoId INT AUTO_INCREMENT PRIMARY KEY,
    vehicleId INT NOT NULL,
    name VARCHAR(80) NOT NULL,
    description VARCHAR(255),
    isActive BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fkDemoVehicle
      FOREIGN KEY (vehicleId) REFERENCES vehicles(vehicleId)
      ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE demoMovements (
    demoMovementId INT AUTO_INCREMENT PRIMARY KEY,
    demoId INT NOT NULL,
    commandId INT NOT NULL,
    sortOrder INT NOT NULL,
    durationMs INT UNSIGNED NOT NULL,
    pauseMs INT UNSIGNED NOT NULL DEFAULT 0,
    CONSTRAINT uqDemoOrder UNIQUE (demoId, sortOrder),
    CONSTRAINT fkMovementDemo
      FOREIGN KEY (demoId) REFERENCES demos(demoId)
      ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fkMovementCommand
      FOREIGN KEY (commandId) REFERENCES commands(commandId)
      ON DELETE RESTRICT ON UPDATE CASCADE
);