#!/usr/bin/env python3

import argparse
import binascii
import json
import logging
import queue
import threading

# local python file
import meshtastic_json

# requires pip package paho-mqtt
import paho.mqtt.client as mqtt

# requires pip package protobuf
from google.protobuf.message import DecodeError


def on_connect(client, userdata, _flags, _rc, _properties):
    topics = userdata["args"].mqtt_topic
    logging.info(
        "Connected to MQTT server %s port %d using %s",
        client.host,
        client.port,
        client.transport,
    )
    for topic in topics:
        logging.info("Subscribing to topic '%s'", topic)
        client.subscribe(topic, 0)


def on_disconnect(_client, _userdata, _disconnect_flags, _reason_code, _properties):
    logging.warning("Disconnected from MQTT server. Will try to reconnect soon.")


def on_connect_fail(_client, _userdata):
    logging.info("Failed to connect to MQTT server. Will retry soon again.")


def on_message(_client, userdata, msg: mqtt.MQTTMessage):
    userdata["queue"].put(msg)


def process_message(msg: mqtt.MQTTMessage, mqtt_client: mqtt.Client):
    logging.info(f"Got message with topic '{msg.topic}' of size {len(msg.payload)} B")
    search = "/e/"
    if not search in msg.topic:
        logging.warning(f"Ignoring topic '{msg.topic}': missing '{search}'")
        return
    try:
        payload = meshtastic_json.decode_service_envelope(msg.payload)
    except (ValueError, DecodeError) as e:
        logging.warning(
            (
                "Failed to decode message of size "
                f"{len(msg.payload)} "
                f"from topic '{msg.topic}': {e}"
            )
        )
        logging.info(f"Payload ({len(msg.payload)} B): {binascii.hexlify(msg.payload)}")
        return
    topic_out = msg.topic.replace(search, "/json/")
    payload_out = json.dumps(payload)
    try:
        res = mqtt_client.publish(topic_out, payload_out)
        res.wait_for_publish()
        logging.info(f"Wrote message of size {len(payload_out)} B to '{topic_out}'")
    except (ValueError, RuntimeError) as e:
        logging.warning(f"Failed to publish message to topic '{topic_out}': {e}")


def message_processor(message_queue: queue.Queue, mqtt_client: mqtt.Client):
    while message := message_queue.get():
        process_message(message, mqtt_client)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Meshtastic MQTT subscriber",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", help="Verbose mode", action="store_true")
    parser.add_argument(
        "--mqtt_host",
        default="localhost",
        help="The MQTT broker address",
    )
    parser.add_argument(
        "--mqtt_port",
        type=int,
        default=1883,
        help="The MQTT broker port",
    )
    parser.add_argument(
        "--mqtt_keepalive",
        type=int,
        default=30,
        help="The MQTT keepalive interval (in seconds)",
    )
    parser.add_argument(
        "-t",
        "--mqtt_topic",
        required=True,
        metavar="TOPIC",
        action="append",
        help="The topic(s) to subscribe to ('#' for all topics). Can be specified multiple times",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    log_format = "%(asctime)-15s %(levelname)-7s %(name)-6s %(message)s"
    logging.basicConfig(format=log_format, level=log_level)
    for level in (logging.DEBUG, logging.INFO):
        logging.addLevelName(level, logging.getLevelName(level).lower())

    q = queue.Queue()
    userdata = {"queue": q, "args": args}
    mqttc = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        userdata=userdata,
        reconnect_on_failure=True,
    )

    mqttc.on_message = on_message
    mqttc.on_connect = on_connect
    mqttc.on_disconnect = on_disconnect
    mqttc.on_connect_fail = on_connect_fail

    mqttc.connect(args.mqtt_host, args.mqtt_port, args.mqtt_keepalive)

    logging.info("Running until stopped with ctrl+c...")

    processor = threading.Thread(target=message_processor, args=(q, mqttc))
    processor.start()

    try:
        mqttc.loop_forever()
    except KeyboardInterrupt:
        pass

    q.put(None)
    processor.join()


if __name__ == "__main__":
    main()
