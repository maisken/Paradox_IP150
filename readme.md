# Paradox_IP150 Docker addon for HASS.IO

# Support for this Plugin can be found at:

https://community.home-assistant.io/t/paradox-alarm-mqtt-hassio-addon/38569

## This currently only supports Manual install:


I’ve set up a very basic hassio add-on that will run an mqtt interface for the Paradox ip150 module, via the ip150 web interface. If you are interested, you can find it at https://github.com/alfredopironti/Paradox_IP150 79

You can try it out by getting ssh access to your hassio installation, then
cd /addons
git clone https://github.com/alfredopironti/Paradox_IP150.git 36 paradox_ip150_mqtt

Then go to the homeassistant home page: click on hassio; then on the shopping-bag icon on top right; 
then on the circular refresh arrow top right, and the add-on should appear in the local list. 
Configure the IP address of your mqtt broker and ip150 module, set panel code and password, and you should be good to go.
There is currently no logging displayed.








### Basic configuration should allow you to get going:

Running built in mqtt

#### configuration.yaml
```
mqtt:
broker: localhost
port: 1883
```
#### configuration.yaml

alarm_control_panel:
```
platform: mqtt
name: House Paradox
state_topic: “paradox/alarm/state/1”
command_topic: “paradox/alarm/cmnd/1”
payload_disarm: “DISARM”
payload_arm_home: “ARM_HOME”
payload_arm_away: “ARM_AWAY”
#ARM_HOME = ARM_sleep @Line38 ip150.mqtt.py
```
#### configuration.yaml
```
platform: mqtt
state_topic: “paradox/zone/state/2”
name: “Study”
qos: 0
payload_on: “on”
payload_off: “off”
Repeat for all your Zones/Openings and so forth
```
#### Hass.io: add-on details => Paradox IP150MQTT Adapter (web based configuration)
```
{
“IP150_ADDRESS”: “http://[IP-OF-IP150]”,
“PANEL_CODE”: “[mastercode]”,
“PANEL_PASSWORD”: “[webpassword]”,
“MQTT_ADDRESS”: “mqtt://core-mosquitto”,
“MQTT_USERNAME”: “MQTT_user”,
“MQTT_PASSWORD”: “MQTT_pwd”,
“ALARM_PUBLISH_TOPIC”: “paradox/alarm/state”,
“ALARM_SUBSCRIBE_TOPIC”: “paradox/alarm/cmnd”,
“ZONE_PUBLISH_TOPIC”: “paradox/zone/state”,
“CTRL_PUBLISH_TOPIC”: “paradox/ctrl/state”,
“CTRL_SUBSCRIBE_TOPIC”: “paradox/ctrl/cmnd”
}
```
#### Hass.io: add-on details => Mosquitto broker (web based configuration)
```
{
“plain”: true,
“ssl”: false,
“anonymous”: true,
“logins”: [],
“customize”: {
“active”: false,
“folder”: “mosquitto”
},
“certfile”: “fullchain.pem”,
“keyfile”: “privkey.pem”
}
```

todo
[ ] make auto install
[ ] create support
[ ] clear issues
