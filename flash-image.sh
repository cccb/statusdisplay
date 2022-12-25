#!/bin/sh
esptool.py --port /dev/ttyUSB0 erase_flash
#esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 images/esp32-20220618-v1.19.1.bin
esptool.py --chip esp32c3 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x0 images/esp32c3-20220618-v1.19.1.bin
