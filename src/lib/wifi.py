import network
import time

class Wifi(object):
	nic = None
	essid = None
	password= None

	def __init__(self, ssid, password, ifconfig=None):
		self.nic = network.WLAN(network.STA_IF)
		self.nic.active(True)
		self.essid = ssid
		self.password = password
		if ifconfig:
			self.nic.ifconfig(tuple(ifconfig))

	def connect(self):
		if self.nic.isconnected():
			print('already connected to wifi, disconnecting')
			self.nic.disconnect()
		self.nic.connect(self.essid, self.password)
		retries = 0
		while not self.nic.isconnected() and not self.nic.status() == network.STAT_GOT_IP:
			time.sleep_ms(500)
			retries += 1

			if retries > 120*5:
				print('could not connect to wifi')
				return False
		print('connected. network config:', self.nic.ifconfig())
		return True
