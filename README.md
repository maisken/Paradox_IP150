# Paradox_IP150
Hassio add-on, Python and MQTT bindings for controlling a Paradox alarm via the IP150 web interface V3

# Paradox_IP150 Docker addon for HASS.IO

# Support for this Plugin can be found at:

https://community.home-assistant.io/t/paradox-alarm-mqtt-hassio-addon/38569

## This currently only supports manual install:


This add-on will run an mqtt interface for the Paradox ip150 module, via the ip150 web interface.

You can try it out by getting ssh access to your hassio installation, then

    cd /addons
    git clone https://github.com/alfredopironti/Paradox_IP150.git paradox_ip150_mqtt

Then go to the homeassistant home page: click on Hass.io in the menu; then on the add-on store tab.
The add-on should appear in the local add-ons list.

Configure the IP address of your mqtt broker and ip150 module, set panel code and password, and you should be good to go.
There is currently no logging displayed.

### Basic configuration should allow you to get going:

Make sure you have an MQTT broker running, for instance by using Hass.io integrations. Then:

#### configuration.yaml - Configuring the alarm control panel
```
alarm_control_panel:

platform: mqtt
name: House Paradox
state_topic: “paradox/alarm/state/1”
command_topic: “paradox/alarm/cmnd/1”
payload_disarm: “DISARM”
payload_arm_home: “ARM_HOME”
payload_arm_away: “ARM_AWAY”
#ARM_HOME = ARM_sleep @Line38 ip150.mqtt.py
```
#### configuration.yaml - Configuring PIR sensors (optional)
```
platform: mqtt
state_topic: “paradox/zone/state/2”
name: “Study”
qos: 0
payload_on: “on”
payload_off: “off”
#Repeat for other Zones/Openings in your setup
```
#### Hass.io: add-on configuration details => Paradox IP150MQTT Adapter (web based configuration)
```
{
“IP150_ADDRESS”: “http://[IP-OF-IP150]”,
“PANEL_CODE”: “[mastercode]”,
“PANEL_PASSWORD”: “[webpassword]”,
“MQTT_ADDRESS”: “mqtt://[IP-OF-MQTT-BROKER]”,
“MQTT_USERNAME”: “MQTT_user”,
“MQTT_PASSWORD”: “MQTT_pwd”,
“ALARM_PUBLISH_TOPIC”: “paradox/alarm/state”,
“ALARM_SUBSCRIBE_TOPIC”: “paradox/alarm/cmnd”,
“ZONE_PUBLISH_TOPIC”: “paradox/zone/state”,
“CTRL_PUBLISH_TOPIC”: “paradox/ctrl/state”,
“CTRL_SUBSCRIBE_TOPIC”: “paradox/ctrl/cmnd”
}
```
