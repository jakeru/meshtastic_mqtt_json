#!/usr/bin/env python3

import json
import sys
from meshtastic import telemetry_pb2
from meshtastic import mqtt_pb2
from meshtastic import portnums_pb2
from meshtastic import mesh_pb2
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message

def message_to_dict(msg: Message):
    return MessageToDict(msg, preserving_proto_field_name=True)


def decode_payload(payload: bytes, type: portnums_pb2.PortNum.ValueType) -> dict:
    if type == portnums_pb2.TEXT_MESSAGE_APP:
        return { "text": payload.decode() }
    elif type == portnums_pb2.POSITION_APP:
        m = mesh_pb2.Position()
    elif type == portnums_pb2.NODEINFO_APP:
        m = mesh_pb2.User()
    elif type == portnums_pb2.TELEMETRY_APP:
        m = telemetry_pb2.Telemetry()
    elif type == portnums_pb2.RANGE_TEST_APP:
        return { "range_test": payload.decode() }
    else:
        raise ValueError(f"Unsupported payload type: {type}")
    m.ParseFromString(payload)
    return message_to_dict(m)


def decode_service_envelope(msg: bytes) -> dict:
    se = mqtt_pb2.ServiceEnvelope()
    se.ParseFromString(msg)
    if not se.packet.HasField("decoded"):
        raise ValueError("Missing 'packet.decoded' field. Is packet encrypted?")
    decoded_payload = decode_payload(
        se.packet.decoded.payload, se.packet.decoded.portnum
    )
    se_dict = message_to_dict(se)
    se_dict["packet"]["decoded"]["payload"] = decoded_payload
    se_dict["packet"]["decoded"]["size"] = len(msg)
    return se_dict


if __name__ == "__main__":
    msg = sys.stdin.buffer.read()
    se = decode_service_envelope(msg)
    print(json.dumps(se))
