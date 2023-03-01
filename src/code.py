import asyncio
import machine
from wifi import Wifi


# room status
UNKNOWN = 0
PUBLIC_OPEN = 1
INTERNAL_OPEN = 2
CLOSED = 3

CONFIG = {}


async def setup_wifi(config):
    wifi = Wifi(config["ssid"], config["password"], config["ifconfig"])
    if not wifi.connect():
        machine.reset()


async def main():
    running = True
    room_status = UNKNOWN
    room_status_updated = 0

    print("Loading config")
    config = {}
    with open("config_base.json", "r") as base, open("config_device.json", "r") as device:
        config.update(json.load(base))
        config.update(json.load(device))

    print("Starting setup")
    await setup_led_buttons()
    await setup_wifi(config["wifi"])
    # TODO: parallelice mqtt and matrix setup?
    await setup_mqtt(config["mqtt"])
    await setup_matrix(config["matrix"])

    print("Setup done")

    set_room_status(status=UNKNOWN, publish=False)



asyncio.run(main())

