# Paradox_IP150
Hassio add-on, Python and MQTT bindings for controlling a Paradox alarm via the IP150 web interface V3.

# Dependencies
For best results, requires a Paradox IP150S with a firmware below 4.x. 1.x seems to work the best. It is worth considering to have your IP150S use the DNS from your router and then block access to 54.165.77.37 and upgrade.insightgoldatpmh.com as IP150's have been known to upgrade their firmware automatically.

# Paradox_IP150 Docker add-on for HASS.IO

# Support for this Plugin can be found at:

https://community.home-assistant.io/t/paradox-alarm-mqtt-hassio-addon/38569

# Installation
From the Home Assistant home page, click on the Hass.io menu item, then go the Add-on Store tab.

Add a repository with the following URL:

https://github.com/maisken/hassio-addons

Once you have enabled the repository, the Paradox IP150 MQTT Adapter add-on should become available for installation.

After installing the add-on, make sure to configure it. As a minimum, configure the IP address of your MQTT broker and ip150 module, set panel code and password, and you should be good to go.

There is currently no logging displayed from the hass.io add-on when the add-on is working correctly. Errors for the hass.io add-on are only displayed when the add-on is configured incorrectly.

### Basic configuration should allow you to get going:

Make sure you have an MQTT broker running, for instance by using Hass.io integrations.
Also, the IP150 module only works with a self-signed certificate, which offers little protection over plaintext.
Hence, the recommended setup is to:
- Disable remote access to the IP150 module on your router
- Configure the IP150 module to work via HTTP (port 80)
- You can still arm, disarm and see if the alarm triggered via the Home Assistant interface, which can be securely accessed remotely

Then:

#### Hass.io: add-on configuration details => Paradox IP150MQTT Adapter (web based configuration)
```
{
"IP150_ADDRESS": "http://[IP-OF-IP150]",
"PANEL_CODE": "[mastercode]",
"PANEL_PASSWORD": "[webpassword]",
"REFRESH_RATE": 0.5,
"MQTT_ADDRESS": "mqtt://[IP-OF-MQTT-BROKER]",
"MQTT_USERNAME": "MQTT_user",
"MQTT_PASSWORD": "MQTT_pwd",
"LOG_LEVEL": "WARNING",
"ALARM_PUBLISH_TOPIC": "paradox/alarm/state",
"ALARM_SUBSCRIBE_TOPIC": "paradox/alarm/cmnd",
"ZONE_PUBLISH_TOPIC": "paradox/zone/state",
"CTRL_PUBLISH_TOPIC": "paradox/ctrl/state",
"CTRL_SUBSCRIBE_TOPIC": "paradox/ctrl/cmnd"
}
```

#### configuration.yaml - Configuring the alarm control panel
```
alarm_control_panel:
  - platform: mqtt
    name: "House Paradox"
    state_topic: "paradox/alarm/state/1"
    command_topic: "paradox/alarm/cmnd/1"
    qos: 1
    availability_topic: "paradox/ctrl/state"
    payload_available: "Connected"
    payload_not_available: "Disconnected"
```
#### Lovelace card for the alarm control panel
```
type: alarm-panel
states:
  - arm_home
  - arm_away
  - arm_night
entity: alarm_control_panel.house_paradox
name: Alarm
```

#### configuration.yaml - Configuring PIR sensors (optional)
```
binary_sensor:
  - platform: mqtt
    state_topic: "paradox/zone/state/2"
    name: "Study"
    qos: 1
    payload_on: "on"
    payload_off: "off"
    availability_topic: "paradox/ctrl/state"
    payload_available: "Connected"
    payload_not_available: "Disconnected"
#Repeat for other Zones/Openings in your setup
```
