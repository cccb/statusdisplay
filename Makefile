DEVICE = /dev/ttyUSB0
DEVICENAME = ?
IMAGE = images/esp32c3-20220618-v1.19.1.bin

default: help

image:  ## Flash Micropython firmware
	esptool.py --port ${DEVICE} erase_flash
	esptool.py --chip esp32c3 --port ${DEVICE} --baud 460800 write_flash -z 0x0 ${IMAGE}

code:  ## Flash programm
	ampy put src/lib/wifi.py wifi.py
	ampy put src/lib/mqtt.py mqtt.py
	ampy put src/lib/mytrix.py mytrix.py
	ampy put config/config_base.json config_base.json
	ampy put config/config_${DEVICENAME}.json config_device.json
	ampy put src/main.py main.py
	ampy reset

help:  ## Show this help
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'
