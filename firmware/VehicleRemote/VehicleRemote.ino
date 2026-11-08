/* Wi-Fi provisioning + per-vehicle WebSocket + 74HC595 controller.
   Open this sketch folder alone, not the two original sketches together.
   Libraries: WiFiManager (tzapu), WebSockets (Markus Sattler), ArduinoJson 7.
   See ../../docs/INTEGRATION.md for wiring, configuration and protocol. */
#include <Arduino.h>
#if defined(ESP32)
#include <WiFi.h>
#elif defined(ESP8266)
#include <ESP8266WiFi.h>
#else
#error "Select an ESP32 or ESP8266 board."
#endif
#include <WiFiManager.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include "config.h"
#include "VehicleLogic.h"

static_assert(SER_PIN != WIFI_RESET_PIN && SRCLK_PIN != WIFI_RESET_PIN &&
              RCLK_PIN != WIFI_RESET_PIN, "Reset button conflicts with shift register");
static_assert(VEHICLE_ID > 0, "Vehicle ID must be positive");

WiFiManager wifiManager;
WebSocketsClient webSocket;
VehicleLogic vehicle;
char deviceName[24];
char socketPath[48];
bool socketStarted = false;
bool socketConnected = false;
bool awaitingSnapshot = true;
bool buttonHeld = false;
bool restartPending = false;
uint32_t buttonSince = 0, restartAt = 0;
uint32_t disconnectedAt = 0, lastReconnectAt = 0, lastReportAt = 0;
uint32_t lastPingAt = 0, lastPongAt = 0;
int previousWifiStatus = -1;
uint8_t writtenOutput = 0xFF;

void writeOutputs() {
  if (writtenOutput == vehicle.output) return;
  digitalWrite(RCLK_PIN, LOW);
  shiftOut(SER_PIN, SRCLK_PIN, MSBFIRST, vehicle.output);
  digitalWrite(RCLK_PIN, HIGH);
  writtenOutput = vehicle.output;
  Serial.printf("Shift register: 0x%02X\n", writtenOutput);
}

void stopVehicle(const char* reason) {
  vehicle.disconnect();
  writeOutputs();
  Serial.printf("STOP: %s\n", reason);
}

void receiveStatus(uint8_t* payload, size_t length) {
  if (length > 4096) { stopVehicle("oversized WebSocket message"); return; }
  JsonDocument doc;
  const DeserializationError error = deserializeJson(doc, payload, length);
  if (error) { stopVehicle("invalid JSON"); return; }
  const char* event = doc["event"] | "";
  if (strcmp(event, "pong") == 0) { lastPongAt = millis(); return; }
  // Print complete state/demo messages to the serial monitor at 115200 baud.
  Serial.print("WS: "); serializeJson(doc, Serial); Serial.println();
  if (!doc["vehicleId"].is<uint32_t>() || doc["vehicleId"].as<uint32_t>() != VEHICLE_ID) return;

  if (strcmp(event, "state") == 0) {
    if (awaitingSnapshot) {
      awaitingSnapshot = false;
      stopVehicle("snapshot received; waiting for a fresh command");
      return;
    }
    // Each demo movement is followed by a duplicate state, without timing.
    // Never execute these states: they would extend/restart timed demo pulses.
    if (strcmp(doc["source"] | "", "DEMO") == 0) return;
    if (doc["commandId"].isNull()) { stopVehicle("empty command"); return; }
    if (!doc["code"].is<int>()) { stopVehicle("missing command code"); return; }
    const int code = doc["code"].as<int>();
    if (code < 0 || code > 8) { stopVehicle("unsupported command code"); return; }
    vehicle.manual(code, millis());
  } else if (!awaitingSnapshot) {
    const int32_t demoId = doc["demoId"] | 0;
    if (strcmp(event, "demo_start") == 0) vehicle.demoStart(demoId);
    else if (strcmp(event, "movement") == 0) {
      if (!doc["code"].is<int>() || !doc["durationMs"].is<uint32_t>()) {
        stopVehicle("invalid demo movement"); return;
      }
      const int code = doc["code"].as<int>();
      if (code < 0 || code > 8 || doc["durationMs"].as<uint32_t>() > 3600000) {
        stopVehicle("unsupported demo movement"); return;
      }
      vehicle.movement(demoId, code, doc["durationMs"].as<uint32_t>(), millis());
    } else if (strcmp(event, "pause") == 0) vehicle.pause(demoId);
    else if (strcmp(event, "demo_end") == 0 || strcmp(event, "demo_error") == 0)
      vehicle.demoEnd(demoId);
  }
  writeOutputs();
}

void onWebSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED:
      socketConnected = true;
      awaitingSnapshot = true;
      lastPingAt = lastPongAt = millis();
      stopVehicle("WebSocket connected; synchronizing");
      Serial.printf("WebSocket connected: ws://%s:%u%s\n", API_HOST, API_PORT, socketPath);
      webSocket.sendTXT("ping");
      break;
    case WStype_DISCONNECTED:
      socketConnected = false;
      awaitingSnapshot = true;
      stopVehicle("WebSocket disconnected; retrying automatically");
      break;
    case WStype_TEXT: receiveStatus(payload, length); break;
    case WStype_ERROR:
      stopVehicle("WebSocket error");
      socketConnected = false;
      webSocket.disconnect();
      break;
    case WStype_FRAGMENT_TEXT_START:
    case WStype_FRAGMENT_BIN_START:
    case WStype_BIN:
      stopVehicle("unsupported WebSocket frame");
      break;
    default: break;
  }
}

void serviceOutputs() {
  vehicle.tick(millis());
  if (socketConnected && static_cast<uint32_t>(millis() - lastPongAt) >= PONG_TIMEOUT_MS) {
    stopVehicle("WebSocket heartbeat timeout");
    socketConnected = false;
    webSocket.disconnect();
  }
  writeOutputs();
}

void printConnectionInfo() {
  Serial.printf("Wi-Fi status: %d; device: %s\n", WiFi.status(), deviceName);
  if (WiFi.status() != WL_CONNECTED) return;
  Serial.print("SSID: "); Serial.println(WiFi.SSID());
  Serial.print("IPv4: "); Serial.println(WiFi.localIP());
  Serial.printf("RSSI: %ld dBm; WebSocket: %s\n", static_cast<long>(WiFi.RSSI()),
                socketConnected ? "connected" : "disconnected");
}

void announcePortal(WiFiManager*) {
  stopVehicle("Wi-Fi setup");
  Serial.printf("Connect phone to %s; open http://192.168.4.1\n", deviceName);
  Serial.println("Select Configure WiFi. The setup network has no Internet access.");
}

void requestCredentialsReset() {
  if (restartPending) return;
  stopVehicle("clearing Wi-Fi credentials");
  if (socketStarted) webSocket.disconnect();
  wifiManager.resetSettings();
  restartPending = true;
  restartAt = millis();
}

void handleReset() {
  if (digitalRead(WIFI_RESET_PIN) == HIGH) buttonHeld = false;
  else if (!buttonHeld) { buttonHeld = true; buttonSince = millis(); }
  else if (static_cast<uint32_t>(millis() - buttonSince) >= 5000) requestCredentialsReset();
  for (uint8_t n = 0; n < 32 && Serial.available(); ++n) {
    const char c = static_cast<char>(Serial.read());
    if (c == 'R' || c == 'r') requestCredentialsReset();
  }
}

void monitorConnection() {
  const uint32_t now = millis();
  const int status = WiFi.status();
  if (status != previousWifiStatus) {
    printConnectionInfo();
    if (status == WL_CONNECTED) {
      if (wifiManager.getConfigPortalActive()) wifiManager.stopConfigPortal();
      WiFi.setAutoReconnect(true);
      // Reinitialize the endpoint after a Wi-Fi outage.
      webSocket.begin(API_HOST, API_PORT, socketPath, "");
      webSocket.setReconnectInterval(WS_RECONNECT_MS);
      socketStarted = true;
      lastReportAt = now;
    } else if (previousWifiStatus == WL_CONNECTED) {
      stopVehicle("Wi-Fi lost");
      socketConnected = false;
      if (socketStarted) webSocket.disconnect();
      socketStarted = false;
      disconnectedAt = lastReconnectAt = now;
    }
    previousWifiStatus = status;
  }
  if (status == WL_CONNECTED) {
    if (static_cast<uint32_t>(now - lastReportAt) >= 60000) {
      printConnectionInfo(); lastReportAt = now;
    }
    return;
  }
  if (wifiManager.getConfigPortalActive()) return;
  if (static_cast<uint32_t>(now - disconnectedAt) >= 120000) {
    wifiManager.startConfigPortal(deviceName, PORTAL_PASSWORD);
    disconnectedAt = millis();
  } else if (static_cast<uint32_t>(now - lastReconnectAt) >= 30000) {
    lastReconnectAt = now;
    Serial.println("Reconnecting to saved Wi-Fi...");
    WiFi.reconnect();
  }
}

void setup() {
  pinMode(SER_PIN, OUTPUT); pinMode(SRCLK_PIN, OUTPUT); pinMode(RCLK_PIN, OUTPUT);
  digitalWrite(SER_PIN, LOW); digitalWrite(SRCLK_PIN, LOW); digitalWrite(RCLK_PIN, LOW);
  Serial.begin(115200);
  writeOutputs(); // All outputs LOW before attempting any networking.
  pinMode(WIFI_RESET_PIN, INPUT_PULLUP);
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  uint8_t mac[6]; WiFi.macAddress(mac);
  snprintf(deviceName, sizeof(deviceName), "INDISCIPLINE-%02X%02X%02X", mac[3], mac[4], mac[5]);
  snprintf(socketPath, sizeof(socketPath), "/ws/status/%lu", static_cast<unsigned long>(VEHICLE_ID));
  Serial.printf("\n%s | R/r or hold GPIO%u to GND for 5s: reset Wi-Fi\n", deviceName, WIFI_RESET_PIN);
  webSocket.onEvent(onWebSocketEvent);
  wifiManager.setDebugOutput(false);
  wifiManager.setHostname(deviceName);
  wifiManager.setConfigPortalBlocking(false);
  wifiManager.setConfigPortalTimeout(0);
  wifiManager.setConnectTimeout(15);
  wifiManager.setSaveConnectTimeout(15);
  wifiManager.setConnectRetries(1);
  wifiManager.setAPStaticIPConfig(IPAddress(192,168,4,1), IPAddress(192,168,4,1), IPAddress(255,255,255,0));
  wifiManager.setAPCallback(announcePortal);
  wifiManager.setShowPassword(false);
  wifiManager.setShowInfoUpdate(false);
  WiFi.setAutoReconnect(true);
  wifiManager.autoConnect(deviceName, PORTAL_PASSWORD);
  disconnectedAt = lastReconnectAt = millis();
  monitorConnection();
}

void loop() {
  if (!restartPending) handleReset();
  if (restartPending) {
    if (static_cast<uint32_t>(millis() - restartAt) >= 250) ESP.restart();
    yield(); return;
  }
  serviceOutputs();
  monitorConnection();
  wifiManager.process();
  if (socketStarted && WiFi.status() == WL_CONNECTED) {
    webSocket.loop();
    if (socketConnected && static_cast<uint32_t>(millis() - lastPingAt) >= PING_INTERVAL_MS) {
      lastPingAt = millis();
      webSocket.sendTXT("ping"); // The existing Python endpoint replies {"event":"pong"}.
    }
  }
  serviceOutputs();
  yield();
}
