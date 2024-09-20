# Meshtastic MQTT JSON converter

This tool translates [MQTT](https://mqtt.org/) messages posted by
[Meshtastic](https://meshtastic.org/) nodes, that are using the
[protobuf](https://protobuf.dev/) format, into [JSON](https://www.json.org/).

## Installation

``` sh
git clone https://github.com/jakeru/meshtastic_mqtt_json.git
cd meshtastic_mqtt_json
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

