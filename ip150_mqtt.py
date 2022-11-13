import argparse
import json
import logging
import urllib.parse

import paho.mqtt.client as mqtt

import ip150


class IP150_MQTT_Error(Exception):
	pass


class IP150_MQTT():

	_status_map = {
		'areas_status' : {
			'topic' : 'ALARM_PUBLISH_TOPIC',
			'map'   : {
				'Disarmed'   : 'disarmed',
				'Armed'      : 'armed_away',
				'Triggered'  : 'triggered',
				'Armed_sleep': 'armed_night',
				'Armed_stay' : 'armed_home',
				'Entry_delay': 'pending',
				'Exit_delay' : 'arming',
				'Ready'      : 'disarmed'
			}
		},
		'zones_status' : {
			'topic' : 'ZONE_PUBLISH_TOPIC',
			'map'	: {
				'Closed'         : 'off',
				'Open'           : 'on',
				'In_alarm'       : 'on',
				'Closed_Trouble' : 'off',
				'Open_Trouble'   : 'on',
				'Closed_Memory'  : 'off',
				'Open_Memory'    : 'on',
				'Bypass'         : 'off',
				'Closed_Trouble2': 'off',
				'Open_Trouble2'  : 'on'
			}
		}
	}

	_alarm_action_map = {
		'DISARM'	: 'Disarm',
		'ARM_AWAY'	: 'Arm',
		'ARM_NIGHT'	: 'Arm_sleep',
		'ARM_HOME'	: 'Arm_stay'
		}

	def __init__(self, opt_file):
		self._cfg = {}
		with opt_file:
			self._cfg = json.load(opt_file)
		log_level = getattr(logging, str(self._cfg['LOG_LEVEL']).upper(), None)
		log_error = False
		if not isinstance(log_level, int):
			log_error = True
			log_level = logging.WARNING
		logging.basicConfig(level=log_level)
		if log_error:
			# Can't log this before, as we need to call basicConfig first
			logging.warning('Wrong log level provided: "{}". Overriding with WARNING.'.format(self._cfg['LOG_LEVEL']))
		self._will = (self._cfg['CTRL_PUBLISH_TOPIC'], 'Disconnected', 1, True)

	def on_paradox_new_state(self, state, client):
		for d1 in state.keys():
			d1_map = self._status_map.get(d1,None)
			if d1_map:
				for d2 in state[d1]:
					publish_state = d1_map['map'].get(d2[1],None)
					if publish_state:
						client.publish(self._cfg[d1_map['topic']]+'/'+str(d2[0]), publish_state, 1, True)

	def on_paradox_update_error(self, e, client):
		# We try to do a proper shutdown,
		# like if the user asked us to disconnect via MQTT
		logging.warning('Error getting Paradox status update. Doing clean shutdown. Error details: {}'.format(e))
		self.mqtt_ctrl_disconnect(client)

	def on_mqtt_connect(self, client, userdata, flags, rc):
		if rc != 0:
			raise IP150_MQTT_Error('Error while connecting to the MQTT broker. Reason code: {}'.format(str(rc)))

		client.subscribe([(self._cfg['ALARM_SUBSCRIBE_TOPIC']+'/+', 1), (self._cfg['CTRL_SUBSCRIBE_TOPIC'], 1)])

		client.publish(self._cfg['CTRL_PUBLISH_TOPIC'], 'Connected', 1, True)

		self.ip.get_updates(on_update=self.on_paradox_new_state, on_error=self.on_paradox_update_error, userdata=client, poll_interval=self._cfg['REFRESH_RATE'])


	def on_mqtt_alarm_message(self, client, userdata, message):
		#Parse area number
		area = message.topic.rpartition('/')[2]
		if area.isdigit():
			action = self._alarm_action_map.get(message.payload.decode(),None)
			if action:
				self.ip.set_area_action(area,action)

	def mqtt_ctrl_disconnect(self, client):
		self.ip.cancel_updates()
		client.publish(*self._will)
		client.disconnect()
		self.ip.logout()

	def on_mqtt_ctrl_message(self, client, userdata, message):
		switcher = {
			'Disconnect': self.mqtt_ctrl_disconnect
		}

		func = switcher.get(message.payload.decode(),None)
		if func:
			return func(client)

	def parse_mqtt_url(self):
		parsed = urllib.parse.urlsplit(self._cfg['MQTT_ADDRESS'])
		port = parsed.port
		if not port:
			if parsed.scheme == 'mqtt':
				port = 1883
			elif parsed.scheme == 'mqtts':
				port = 8883
			else:
				raise IP150_MQTT_Error('No port defined, nor "mqtt" nor "mqtts" scheme.')
		return (parsed.hostname, port)

	def loop_forever(self):
		mqtt_hostname, mqtt_port = self.parse_mqtt_url()

		self.ip = ip150.Paradox_IP150(self._cfg['IP150_ADDRESS'])
		self.ip.login(self._cfg['PANEL_CODE'], self._cfg['PANEL_PASSWORD'])

		mqc = mqtt.Client()
		mqc.on_connect = self.on_mqtt_connect
		mqc.message_callback_add(self._cfg['ALARM_SUBSCRIBE_TOPIC']+'/+', self.on_mqtt_alarm_message)
		mqc.message_callback_add(self._cfg['CTRL_SUBSCRIBE_TOPIC'], self.on_mqtt_ctrl_message)
		mqc.username_pw_set(self._cfg['MQTT_USERNAME'], self._cfg['MQTT_PASSWORD'])
		mqc.will_set(*self._will)

		mqc.connect(mqtt_hostname, mqtt_port)

		mqc.loop_forever()

if __name__ == '__main__':
	argp = argparse.ArgumentParser(description='MQTT adapter for IP150 Alarms')
	argp.add_argument('config', type=argparse.FileType(), default='options.json', nargs='?')
	args = vars(argp.parse_args())
	ip_mqtt = IP150_MQTT(args['config'])
	ip_mqtt.loop_forever()
