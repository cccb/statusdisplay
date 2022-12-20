import machine
import time
import sys
import json

from wifi import Wifi
from mqtt import MQTTClient
from mytrix import Matrix

def load_config():
    config = {}
    config.update(json.load(open("config_base.json")))
    return config

def setup_wifi(config):
    w = Wifi(config['ssid'], config['password'], config['ifconfig'])
    if not w.connect():
        machine.reset()
    # this sleep is needed to fix some init race condition
    time.sleep_ms(300)
    return w

def setup_mqtt():
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

def setup():
    print('starting setup')
    config = load_config()
    wifi_con = setup_wifi(config)
    return
    mqtt_con = setup_mqtt(config)

    print('init done')
    return wifi_con, mqtt_con

def loop():
    time.sleep(10)
    print('loop')

try:
    setup()
    print('setup done')
    while True:
        loop()
        time.sleep_ms(50)
except Exception as e:
    sys.print_exception(e)
    machine.reset()
