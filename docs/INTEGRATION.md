# ESP vehicle + web controller

The Python API and both original `.ino` files are unchanged. The merged sketch is
`firmware/VehicleRemote/VehicleRemote.ino`. Open that folder alone in Arduino IDE;
compiling the original two sketches together creates duplicate `setup()` / `loop()` functions.

## 1. Firmware setup

1. Install the ESP32 board package (Espressif) and select your board. For the original
   NodeMCU, select **NodeMCU 1.0 (ESP-12E Module)** with ESP8266 core 3.1.2.
2. Install **WiFiManager by tzapu 2.0.17**, **WebSockets by Markus Sattler 2.6.1**,
   and **ArduinoJson by Benoit Blanchon 7.4.2** through Library Manager.
3. Edit `firmware/VehicleRemote/config.h`: set `API_HOST` to the API computer's LAN IP,
   `API_PORT` (8000 by default), and `VEHICLE_ID` to an existing database vehicle.
   `API_HOST` is only a hostname/IP, without `http://`, a port or a path.
4. Check the wiring below, upload the merged sketch, and open Serial Monitor at **115200**.
5. With no saved Wi-Fi, connect a phone to **INDISCIPLINE-xxxxxx**, password
   **Starlight65_** (configurable in `config.h`). Open **http://192.168.4.1** and use
   Configure WiFi to save your network. Saved credentials are reused on restart.
6. The serial monitor reports Wi-Fi, WebSocket connection changes, full state/demo
   messages and every changed output byte. Once connected, send a fresh command.

The supplied originals target ESP8266 despite the ESP32 request. The merged sketch
supports both. Default ESP32 pin choices target the **classic ESP32 DevKit**; verify
available pins for ESP32-C3/S3 and other variants before using them.

| Signal | 74HC595 pin | ESP32 GPIO | ESP8266 NodeMCU |
| --- | --- | --- | --- |
| SER / DS, data | 14 | 23 | GPIO14 / D5 |
| SRCLK / SHCP, shift clock | 11 | 18 | GPIO13 / D7 |
| RCLK / STCP, latch | 12 | 19 | GPIO12 / D6 |
| Wi-Fi reset button to GND | — | 27 | **GPIO4 / D2** |

The original controller's introductory wiring comment swapped the clock/latch IC
pins; its actual code uses D7 for shift clock and D6 for latch. The table reflects
that code and the 74HC595 pinout. Move the original Wi-Fi reset button off D5: D5
already carries shift-register data. The new button uses `INPUT_PULLUP`.
Connect grounds together, VCC (16) to 3.3 V, OE (13) to GND and MR (10) to 3.3 V.
Keep the existing vehicle driver circuit between the register and actuators.

Hold the reset button for 5 seconds, or send **R/r** over serial, to clear Wi-Fi
credentials and reboot into setup. Outputs stop first. The old serial movement
commands are replaced by API commands. Wi-Fi reconnects automatically; after a
2-minute outage the configuration portal becomes available again.

## 2. Start the existing API

Use the project's Python environment and existing `.env` / MySQL configuration.
If setting up a new database, use the existing SQL scripts; do not rerun sample
inserts against an already populated database.

```powershell
.carrito/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Use **one worker**: the API's WebSocket registry and demo state are in memory.
Allow port 8000 through the computer's firewall on your local network. The ESP
and API must be able to reach each other; Internet access is not required for LAN use.
The sketch uses `ws://HOST:PORT/ws/status/VEHICLE_ID` (plain WebSocket for the LAN).
It does not implement WSS/certificate configuration for an Internet-hosted API.

## 3. Open the web controller

Open `web/index.html` directly. The page uses relative CSS and JavaScript files.
To publish on GitHub Pages, deploy the contents of `web/` together. Set the reachable
API URL and vehicle ID in **Menu → Connection**. For HTTPS hosting, use an HTTPS
API address that the phone can reach and that permits cross-origin browser requests.

Drag the left stick to drive or the right lever to raise/lower the load. Release to
send STOP. Lights and sound send one toggle followed by STOP after the 500 ms pulse.
Select a demo on the remote and press **Run demo**. Keyboard users can hold a direction
key on the drive stick or an up/down arrow on the load lever and release it to stop.

- Menu → History: the latest 10 history records, matching the existing stored procedure.
- Menu → Commands: list, create, edit, activate/deactivate and delete commands.
- Menu → Demos: inspect steps and run a stored demo.
- Menu → All endpoints: generated from `/openapi.json`; supplies path parameters and
  editable JSON bodies for every REST endpoint, including vehicle/demo/movement CRUD,
  manual history registration and status updates. Mutating requests have a review dialog.
- Requests use `fetch` AJAX. `/status` already registers manual history, so the control
  buttons do not separately call `/history` and create duplicate records.

The browser deliberately **does not open a WebSocket**. The API permits one socket
per vehicle and two sockets in total; the ESP needs that subscription. Close other
WebSocket test clients for the same vehicle before connecting the ESP. The page
polls `GET /status/{vehicle_id}` every 2 seconds and labels it **API status**.

## Command and timing contract

Commands are mapped by their stable **code**, not their auto-increment database ID.
The browser discovers the correct ID through `/commands/vehicle/{vehicle_id}`.

| Code | Sample ID | Action | Register output |
| --- | --- | --- | --- |
| 0 | 9 | STOP | 0x00 |
| 1 | 1 | Forward | 0x80 / QH |
| 2 | 2 | Backward | 0x20 / QF |
| 3 | 3 | Left | 0x10 / QE |
| 4 | 4 | Right | 0x40 / QG |
| 5 | 5 | Raise load | 0x02 / QB |
| 6 | 6 | Lower load | 0x04 / QC |
| 7 | 7 | Toggle lights | 0x01 / QA |
| 8 | 8 | Toggle sound | 0x08 / QD |

- **Manual/API movement, codes 1–6:** the selected output remains HIGH until another
  command replaces it, STOP arrives, or the connection fails. No 500 ms timeout.
  Exactly one output is selected at a time, matching the API's single active command.
- **Lights/sound:** each command pulses the physical toggle input for 500 ms. This
  retains the original vehicle's toggle behavior. It replaces the previous output;
  lights/sound are not separately tracked motor-state channels. The physical on/off
  state is not available through this API, so the UI never claims to know it.
- **Demos:** timed pulses retain the original **500 ms**, or **2000 ms** for raise/lower.
  Each pulse is capped by that movement's `durationMs` if shorter. If a step lasts
  longer, outputs remain LOW for the rest of the step. The API schedules subsequent
  steps and `pauseMs`. No `delay()` is used. `pause`, `demo_end`, and `demo_error`
  clear the current demo's output.
- The demo runner emits both `movement` and a duplicate `state` with `source: DEMO`.
  Firmware executes only `movement`; the duplicate cannot restart or prolong a pulse.
- Manual commands (including STOP/null) interrupt the active demo on the ESP. Its
  remaining events are ignored. The API still finishes its schedule because it has
  no cancellation endpoint. A new `demo_start` can start a new run. Concurrent demos
  are not combined: the ESP accepts the first run and ignores competing run events.
- Boot and disconnect clear all register outputs. The first state after connection
  is printed but never executed: this prevents replaying old movement or toggle state.
  Send a fresh command after connecting/reconnecting. Rejoining a demo midway does
  not resume that demo; wait for it to end before starting a new run.
- Every second the ESP sends the endpoint's text `ping`; missing JSON `pong` for
  3500 ms causes a stop and reconnection attempt. Detected Wi-Fi/socket loss stops
  immediately when serviced. This is loop-based firmware, not a hard real-time
  watchdog; blocking network/library operations can add detection latency.
- Unknown/malformed commands stop the outputs. Browser STOP falls back to a null
  command if no active code-0 row exists. A STOP clicked during an AJAX request is
  sent after that request completes; no movement requests are queued behind it.

## Existing API limits (no Python changes made)

`isConnected` is supplied by the caller and stored in the database; it is **not ESP
presence detection**. HTTP acceptance does not confirm hardware execution. The page
shows the last database command, which can remain a demo command even after that
demo ends or is interrupted. Use the serial monitor for actual execution diagnostics.

The API has no device acknowledgment, physical light/sound feedback, demo cancellation,
or browser-disconnect stop. Closing the page does not stop a persistent command while
the ESP's WebSocket remains alive. Use STOP before leaving the controls. Supporting
these features reliably would require a separately agreed API/protocol change.

## Verification

```powershell
node --check web/app.js
node --test tests/web_test.cjs
New-Item -ItemType Directory -Force .build | Out-Null
g++ -std=c++11 -Wall -Wextra tests/vehicle_logic_test.cpp -o .build/vehicle_logic_test.exe
.build/vehicle_logic_test.exe
```

The C++ checks cover bit mapping, persistent movement/load, STOP, disconnect, toggle
pulses, demo durations/pauses, demo interruption, concurrent runs and timer rollover.
The JS checks cover API ID discovery, STOP ordering/fallback, inactive commands,
error handling and settings. A board build and physical bench check are distinct:
verify wiring, actuator polarity, Wi-Fi provisioning and disconnect stopping on the
actual vehicle before relying on the integration.

For an isolated check using the actual Python routes with an in-memory database,
run `.carrito/Scripts/python.exe tests/preview_api.py` in one terminal, then
`.carrito/Scripts/python.exe tests/api_smoke.py` in another. This fixture listens
only on `127.0.0.1:8766`, never connects to MySQL, and resets when stopped. You can
temporarily point the web page at that address to test its controls without hardware.
Restore the production API address after testing.

Verified during implementation: ESP8266 NodeMCU compilation with core 3.1.2 and the
library versions above; C++ policy tests; six JS request tests; the real API protocol
against the isolated fixture; browser controls, history, command editing, demo step
inspection and endpoint discovery; desktop and 375 px phone layouts. ESP32 board
compilation and physical vehicle behavior have not been verified in this environment.

Library references: [WiFiManager](https://github.com/tzapu/WiFiManager),
[WebSocketsClient](https://github.com/Links2004/arduinoWebSockets/blob/master/src/WebSocketsClient.h),
[ArduinoJson deserialization](https://arduinojson.org/v7/api/json/deserializejson/).
