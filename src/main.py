import machine
import time
import sys
import json

# this should be an enum but micropython doesn't support them
# so we look like an enum but are in reality just class attributes.
class RoomStatus():
    UNKNOWN = 0
    PUBLIC_OPEN = 1
    INTERNAL_OPEN = 2
    CLOSED = 3

class Application():
    def __init__(self):
        self.__running = True
        self.__room_status = RoomStatus.UNKNOWN
        self.__room_status_updated = 0

        print('loading config')
        self.config = {}
        self.config.update(json.load(open("config_base.json")))
        self.config.update(json.load(open("config_device.json")))

        print('starting setup')
        self.setup_led_buttons()
        self.setup_wifi(self.config['wifi'])
        self.setup_mqtt(self.config['mqtt'])
        self.setup_matrix(self.config['matrix'])
        self.watchdog = machine.WDT(timeout=10000)
        self.watchdog.feed()
        print('setup done')

        self.set_room_status(RoomStatus.UNKNOWN, publish=False)

    def setup_led_buttons(self):
        self.leds = {}
        self.buttons = {}
        for status_option in (RoomStatus.PUBLIC_OPEN, RoomStatus.INTERNAL_OPEN, RoomStatus.CLOSED):
            status_config = self.config_for_status(status_option)
            self.leds[status_option] = None
            self.buttons[status_option] = None
            if status_config.get('led_pin'):
                self.leds[status_option] = machine.Pin(status_config['led_pin'], machine.Pin.OUT)
                self.leds[status_option].off()
            if status_config.get('button_pin'):
                self.buttons[status_option] = machine.Pin(status_config['button_pin'], machine.Pin.IN, machine.Pin.PULL_UP)

    def setup_wifi(self, config):
        from wifi import Wifi

        self.wifi = Wifi(config['ssid'], config['password'], config['ifconfig'])
        if not self.wifi.connect():
            machine.reset()
        # this sleep is needed to fix some init race condition
        time.sleep_ms(300)

    def setup_mqtt(self, config):
        if not config:
            print("no mqtt config found, skipping mqtt setup")
            self.mqtt = None
            return

        from mqtt import MQTTClient

        def mqtt_callback(topic, message):
            topic = topic.decode()
            message = message.decode()
            if topic == config.get('statustopic'):
                parsed_status = self.translate_status_from_mqtt(message)
                print("status topic detected", parsed_status)
                self.set_room_status(parsed_status, publish=False, force_update=True)
            else:
                print("unknown mqtt message:", topic, message)

        self.mqtt = MQTTClient(config['devicename'], server=config['broker'], port=config['brokerport'])
        self.mqtt.DEBUG = True
        self.mqtt.set_callback(mqtt_callback)
        time.sleep_ms(300)
        print("connecting to mqtt server at", config['broker'], config['brokerport'])
        while True:
            if not self.mqtt.connect():
                print('new mqtt session being set up')
                break
            else:
                print('mqtt connection failed, retrying')
                time.sleep(3)
        statustopic = config.get('statustopic')
        if statustopic:
            print("suscribing to mqtt status topic: ", statustopic)
            self.mqtt.subscribe(statustopic)

    def config_for_status(self, input_status):
        status_config = self.config['roomstatus']['_default'].copy()
        if input_status == RoomStatus.PUBLIC_OPEN:
            status_config.update(self.config['roomstatus']['public_open'])
        elif input_status == RoomStatus.INTERNAL_OPEN:
            status_config.update(self.config['roomstatus']['internal_open'])
        elif input_status == RoomStatus.CLOSED:
            status_config.update(self.config['roomstatus']['closed'])
        else:
            return None
        return status_config

    def translate_status_to_mqtt(self, input_status):
        status_config = self.config_for_status(input_status)
        if status_config:
            return status_config.get('mqtt_name')
        else:
            return self.config['roomstatus']['closed'].get('mqtt_name')

    def translate_status_to_human(self, input_status):
        status_config = self.config_for_status(input_status)
        if status_config:
            return status_config.get('human_name')
        else:
            return "Unknown"

    def translate_status_from_mqtt(self, input_status):
        for status_option in (RoomStatus.PUBLIC_OPEN, RoomStatus.INTERNAL_OPEN, RoomStatus.CLOSED):
            status_config = self.config_for_status(status_option)
            if status_config and status_config.get('mqtt_name') == input_status:
                return status_option
        return RoomStatus.UNKNOWN

    def setup_matrix(self, config):
        if not config:
            print("no matrix config found, skipping matrix setup")
            self.matrix = None
            return

        from mytrix import Matrix

        self.matrix = Matrix(
                homeserver=config['homeserver'],
                matrix_id=config['matrix_id'],
                access_token=config['access_token'],
                username=config['username'],
                password=config['password'])
        if config.get('displayname'):
            self.matrix.set_displayname(config['displayname'])
        if config.get('rooms'):
            for room in config.get('rooms'):
                self.matrix.join_room(room)

    def loop(self):
        print('loop started')
        while self.__running:
            self.watchdog.feed()
            if self.mqtt:
                self.mqtt.ping()
                self.mqtt.check_msg()
            self.check_buttons()
            time.sleep_ms(50)

    def check_buttons(self):
        for status, button in self.buttons.items():
            if button and button.value() == 0:
                self.set_room_status(status, publish=True)

    def update_leds(self):
        for status, led in self.leds.items():
            if led:
                led.value(self.__room_status == status)

    def publish_to_matrix(self, status_config, status_to_send):
        if not (status_config or status_config.get('matrix_rooms') or self.matrix):
            return
        message = "Room Status is now " + self.translate_status_to_human(status_to_send)
        for room in status_config['matrix_rooms']:
            print("writing status to matrix:", room)
            self.matrix.send_room_message(room, message)

    def set_room_status(self, new_status, publish=True, force_update=False):
        old_status = self.__room_status

        if not force_update:
            if (new_status == old_status):
                return
            if not (time.ticks_ms() - self.__room_status_updated) > 3000:
                return
        print("set status to", self.translate_status_to_human(new_status))
        self.__room_status = new_status
        self.__room_status_updated = time.ticks_ms()
        self.update_leds()

        if not publish:
            return

        if self.mqtt:
            statustopic = self.config.get('mqtt', {}).get('statustopic')
            if statustopic:
                print("writing status to mqtt:", statustopic)
                self.mqtt.publish(statustopic, self.translate_status_to_mqtt(new_status), retain=True)

        if new_status == RoomStatus.CLOSED:
            # The closed status is a special case since we want to announce it to different rooms depending if we were public or private open.
            # So if that's the case, we use the matrix room setting of the old_status.
            status_config = self.config_for_status(old_status)
            self.publish_to_matrix(status_config, new_status)
        else:
            status_config = self.config_for_status(new_status)
            self.publish_to_matrix(self.config_for_status(new_status), new_status)

        if new_status == RoomStatus.INTERNAL_OPEN and old_status == RoomStatus.PUBLIC_OPEN:
            # we do not want to leak the fact we are switching to internal open instead of closing, so we
            # send a closed message to the public channel
            self.publish_to_matrix(self.config_for_status(RoomStatus.PUBLIC_OPEN), RoomStatus.CLOSED)

try:
    app = Application()
    app.loop()
    print('app.loop() should never return. resetting...')
    machine.reset()
except Exception as e:
    sys.print_exception(e)
    machine.reset()
