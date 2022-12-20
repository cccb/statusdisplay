import machine
import time
import sys
import json

class Application():
    def __init__(self):
        self.__running = True

        print('loading config')
        self.config = {}
        self.config.update(json.load(open("config_base.json")))

        print('starting setup')
        self.wifi = self.setup_wifi(self.config['wifi'])
        #self.mqtt = self.setup_mqtt(self.config['mqtt'])
        self.matrix = self.setup_matrix(self.config['matrix'])
        print('setup done')

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

        c = MQTTClient('umqtt_'+devname, mqttserver, port=mqttport)
        c.DEBUG = True
        c.set_callback(subscription_handler)

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
        time.sleep(10)

try:
    app = Application()
    print('setup done')
    app.loop()
    print('app.loop() should never return. resetting...')
    machine.reset()
except Exception as e:
    sys.print_exception(e)
    machine.reset()
