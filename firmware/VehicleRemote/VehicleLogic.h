#pragma once
#include <stdint.h>

// Hardware-independent output policy, also exercised by tests/vehicle_logic_test.cpp.
class VehicleLogic {
 public:
  uint8_t output = 0;
  int32_t activeDemo = 0;

  static uint8_t pattern(int code) {
    switch (code) {
      case 1: return 0x80; // W / forward
      case 2: return 0x20; // S / backward
      case 3: return 0x10; // A / left
      case 4: return 0x40; // D / right
      case 5: return 0x02; // Z / raise
      case 6: return 0x04; // X / lower
      case 7: return 0x01; // G / lights toggle input
      case 8: return 0x08; // F / sound toggle input
      default: return 0;
    }
  }

  static uint32_t pulseDuration(int code) {
    return (code == 5 || code == 6) ? 2000 : 500;
  }

  void stop() { output = 0; timed = false; }
  void disconnect() { stop(); activeDemo = 0; }

  void manual(int code, uint32_t now) {
    activeDemo = 0; // Remaining events from the interrupted demo cannot restart it.
    stop();
    output = pattern(code);
    // Physical toggle inputs need a single press, not a continuous/repeated press.
    if (code == 7 || code == 8) arm(now, pulseDuration(code));
  }

  void demoStart(int32_t id) {
    if (id <= 0 || activeDemo != 0) return; // Ignore competing demo runs.
    stop();
    activeDemo = id;
  }

  void movement(int32_t id, int code, uint32_t durationMs, uint32_t now) {
    if (id <= 0 || id != activeDemo) return;
    stop();
    // Preserve original 500 ms pulses (2000 ms for load), capped by the API step.
    uint32_t duration = pulseDuration(code);
    if (durationMs < duration) duration = durationMs;
    if (!duration) return;
    output = pattern(code);
    arm(now, duration);
  }

  void pause(int32_t id) { if (id > 0 && id == activeDemo) stop(); }
  void demoEnd(int32_t id) {
    if (id > 0 && id == activeDemo) { stop(); activeDemo = 0; }
  }
  void tick(uint32_t now) {
    if (timed && static_cast<uint32_t>(now - startedAt) >= duration) stop();
  }

 private:
  bool timed = false;
  uint32_t startedAt = 0;
  uint32_t duration = 0;
  void arm(uint32_t now, uint32_t ms) {
    startedAt = now;
    duration = ms;
    timed = output != 0;
  }
};
