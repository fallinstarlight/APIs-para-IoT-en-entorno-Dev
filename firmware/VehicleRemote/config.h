#pragma once

// Address of the computer running uvicorn. Do not use localhost/127.0.0.1.
constexpr char API_HOST[] = "54.165.156.220";
constexpr uint16_t API_PORT = 8000;
constexpr uint32_t VEHICLE_ID = 1;
constexpr char PORTAL_PASSWORD[] = "Starlight65_";

// Classic ESP32 DevKit. Change these for other ESP32 board variants.
#if defined(ESP32)
constexpr uint8_t SER_PIN = 23;
constexpr uint8_t SRCLK_PIN = 18;
constexpr uint8_t RCLK_PIN = 19;
constexpr uint8_t WIFI_RESET_PIN = 27;
#elif defined(ESP8266)
// Preserve the original sketch's actual wiring (its opening comment was wrong).
constexpr uint8_t SER_PIN = 14;    // D5
constexpr uint8_t SRCLK_PIN = 13;  // D7
constexpr uint8_t RCLK_PIN = 12;   // D6
constexpr uint8_t WIFI_RESET_PIN = 4; // D2: moved away from shift-register data!
#endif

constexpr uint32_t PING_INTERVAL_MS = 1000;
constexpr uint32_t PONG_TIMEOUT_MS = 3500;
constexpr uint32_t WS_RECONNECT_MS = 3000;
