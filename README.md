# Statusdisplay

(internal) Wiki: https://wiki.berlin.ccc.de/Statusdisplay

## Flashing

Needed:
* [ampy](https://pypi.org/project/adafruit-ampy/)
* [esptool.py](https://github.com/espressif/esptool)

Most distros package them or compatible tools.

Steps:

* connect the esp as `/dev/ttyUSB0` (edit the scripts if your esp is named something else, like for example `/dev/ttyACM0`)
* add a base config with the name `config/config_base.json` from the template `config/config_base.json.template`.
* add a device sepcific override config with the name `config/config_<device name>.json`. You can override hash keys here.
* `./flash-image.sh`: flashes Micropython image.
* `./flash-python.sh <device name>`: Flashes the python part for a specific device.
