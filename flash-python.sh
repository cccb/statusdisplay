#!/bin/sh

export AMPY_PORT=/dev/ttyUSB0
export DEVICENAME=${1}

ampy put src/lib/wifi.py wifi.py
ampy put src/lib/mqtt.py mqtt.py
ampy put src/lib/mytrix.py mytrix.py
ampy put config/config_base.json config_base.json
ampy put config/config_${DEVICENAME}.json config_device.json
ampy put src/main.py main.py

ampy reset
