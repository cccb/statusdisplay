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
        self.__status = RoomStatus.UNKNOWN

        print('loading config')
        self.config = {}
        self.config.update(json.load(open("config_base.json")))
        self.config.update(json.load(open("config_device.json")))

        print('starting setup')
        self.wifi = self.setup_wifi(self.config['wifi'])
        #self.mqtt = self.setup_mqtt(self.config['mqtt'])
        self.matrix = self.setup_matrix(self.config['matrix'])
        print('setup done')

        self.set_room_status(RoomStatus.UNKNOWN, publish=False)

    def setup_wifi(self, config):
        from wifi import Wifi

        w = Wifi(config['ssid'], config['password'], config['ifconfig'])
        if not w.connect():
            machine.reset()
        # this sleep is needed to fix some init race condition
        time.sleep_ms(300)
        return w

    def setup_mqtt(self, config):
        from mqtt import MQTTClient

        def mqtt_callback(topic, message):
            if topic == config.get('statustopic'):
                parsed_status = self.translate_status_from_mqtt(message)
                print("status topic detected", parsed_status)
                self.set_room_status(parsed_status, publish=false)
            else:
                print("unknown mqtt message:", topic, message)

        c = MQTTClient('umqtt_'+devname, config['broker'], port=config['brokerport'])
        c.DEBUG = True
        c.set_callback(mqtt_callback)
        if topic == config.get('statustopic'):
            print("suscribing to mqtt status topic: ", config.get('statustopic'))
            c.subscribe(config.get('statustopic'))

        time.sleep_ms(300)

        print('trying to setup mqtt')
        while True:
            if not c.connect():
                print('new mqtt session being set up')
                c.subscribe(b'time')
                break
            else:
                print('mqtt connection failed, retrying')
                time.sleep(3)
        return c

    def config_for_status(self, input_status):
        status_config = self.config['roomstatus']['_default']
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

    def translate_status_from_mqtt(self, input_status):
        for configsection, result in (
                ('public_open', RoomStatus.PUBLIC_OPEN),
                ('private_open', RoomStatus.INTERNAL_OPEN),
                ('closed', RoomStatus.CLOSED)):
            status_config = self.config_for_status(configsection)
            if status_config and status_config.get('mqtt_name') == input_status:
                return result
        return RoomStatus.UNKNOWN

    def setup_matrix(self, config):
        from mytrix import Matrix

        m = Matrix(
                homeserver=config['homeserver'],
                matrix_id=config['matrix_id'],
                access_token=config['access_token'],
                username=config['username'],
                password=config['password'])
        if config.get('displayname'):
            m.set_displayname(config['displayname'])
        if config.get('rooms'):
            for room in config.get('rooms'):
                m.join_room(room)
        return m

    def loop(self):
        print('loop started')
        while self.__running:
            self.__loop_inner()

    def __loop_inner(self):
        print('loop')
        # parse button state
        time.sleep(1)

    def set_room_status(self, status, publish=True):
        status_config = self.config_for_status(status)
        message = "set room status: " + str(status) + ' ' + str(publish) + '\n'
        message += "mqtt status: " + self.translate_status_to_mqtt(status)
        print(message)
        # turn on correct led
        # print to correct matrix channel

try:
    app = Application()
    app.loop()
    print('app.loop() should never return. resetting...')
    machine.reset()
except Exception as e:
    sys.print_exception(e)
    machine.reset()
