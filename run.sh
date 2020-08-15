#!/usr/bin/env bash

while true
do
python3 ip150_mqtt.py /data/options.json
# 20 seconds should be enough to ensure the session expired on the server
sleep 20
done
