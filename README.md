# CCCB Statusdisplay

- [internal docs](https://wiki.berlin.ccc.de/Statusdisplay)

## Hardware

- [ESP32-C3 Core](https://de.aliexpress.com/item/1005004797382555.html)

## Software

- [CircuitPython](https://circuitpython.org/board/luatos_core_esp32c3/)

## Setup

### Configuration

- connect the esp as `/dev/ttyUSB0` (edit the scripts if your esp is named something else, like for example `/dev/ttyACM0`)
- add a base config with the name `config/config_base.json` from the template `config/config_base.json.template`
- add a device sepcific override config with the name `config/config_<device name>.json` (you can override hash keys here)

### Flashing

1. Install needed software:
   - [ampy](https://pypi.org/project/adafruit-ampy/)
   - [esptool.py](https://github.com/espressif/esptool)
2. Flash firmware:
   ```shell
   make image
   ```
3. Copy code:
   ```shell
   make code
   ```

---

Made with :heart: and :snake:.
