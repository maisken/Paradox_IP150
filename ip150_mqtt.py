import ip150
from config import config as cfg
import paho.mqtt.client as mqtt

class IP150_MQTT_Error(Exception):
	pass

will = (cfg['CTRL_PUBLISH_TOPIC'], 'Disconnected', 1, True)

alarm_state_map = {
	'Disarmed'   : 'disarmed',
	'Armed'      : 'armed_away',
	'Armed_sleep': 'armed_home',
	'Armed_stay' : 'armed_home',
	'Entry_delay': 'pending',
	'Exit_delay' : 'pending'
	}

alarm_action_map = {
	'DISARM': 'Disarm',
	'ARM_AWAY': 'Arm',
	'ARM_HOME': 'Arm_sleep'
	}

def on_alarm_new_state(state, client):
	areas_status = state.get('areas_status',None)
	if areas_status:
		for area in areas_status:
			publish_state = alarm_state_map.get(area[1],None)
			if publish_state:
				client.publish(cfg['ALARM_PUBLISH_TOPIC']+'/'+str(area[0]), publish_state, 1, True)

def on_mqtt_connect(client, userdata, flags, rc):
	if rc != 0:
		raise IP150_MQTT_Error('Error while connecting to the MQTT broker. Reason code: {}'.format(str(rc)))

	client.subscribe([(cfg['ALARM_SUBSCRIBE_TOPIC']+'/+', 1), (cfg['CTRL_SUBSCRIBE_TOPIC'], 1)])

	client.publish(cfg['CTRL_PUBLISH_TOPIC'], 'Connected', 1, True)

	userdata.get_updates(on_alarm_new_state, client)


def on_mqtt_alarm_message(client, userdata, message):
	#Parse area number
	area = message.topic.rpartition('/')[2]
	if area.isdigit():
		action = alarm_action_map.get(message.payload.decode(),None)
		if action:
			userdata.set_area_action(area,action)

def mqtt_ctrl_disconnect(client, ip):
	ip.cancel_updates()
	client.publish(*will)
	client.disconnect()
	ip.logout()

def on_mqtt_ctrl_message(client, userdata, message):
	switcher = {
		'Disconnect': mqtt_ctrl_disconnect
	}

	func = switcher.get(message.payload.decode(),None)
	if func:
		return func(client, userdata)

def main():
	ip = ip150.Paradox_IP150(cfg['IP150_ADDRESS'])
	ip.login(cfg['PANEL_CODE'], cfg['PANEL_PASSWORD'])
	
	mqc = mqtt.Client(userdata = ip)
	mqc.on_connect = on_mqtt_connect
	mqc.message_callback_add(cfg['ALARM_SUBSCRIBE_TOPIC']+'/+', on_mqtt_alarm_message)
	mqc.message_callback_add(cfg['CTRL_SUBSCRIBE_TOPIC'],  on_mqtt_ctrl_message)
	mqc.will_set(*will)

	mqc.connect(cfg['MQTT_ADDRESS'])

	mqc.loop_forever()

if __name__ == '__main__':
	main()