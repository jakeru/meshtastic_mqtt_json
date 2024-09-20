#!/usr/bin/env python3

import json
import sys
from meshtastic import telemetry_pb2
from meshtastic import mqtt_pb2
from meshtastic import portnums_pb2
from meshtastic import mesh_pb2
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message


def decode_payload(payload: bytes, type: portnums_pb2.PortNum.ValueType) -> Message:
    if type == portnums_pb2.NODEINFO_APP:
        m = mesh_pb2.User()
    elif type == portnums_pb2.TELEMETRY_APP:
        m = telemetry_pb2.Telemetry()
    else:
        raise ValueError(f"Unsupported payload type: {type}")
    m.ParseFromString(payload)
    return m


def decode_service_envelope(msg: bytes) -> dict:
    se = mqtt_pb2.ServiceEnvelope()
    se.ParseFromString(msg)
    if not se.packet.HasField("decoded"):
        raise ValueError("Missing 'packet.decoded' field. Is packet encrypted?")
    decoded_payload = decode_payload(
        se.packet.decoded.payload, se.packet.decoded.portnum
    )
    se_dict = MessageToDict(se)
    se_dict["packet"]["decoded"] = MessageToDict(decoded_payload)
    return se_dict


if __name__ == "__main__":
    msg = sys.stdin.buffer.read()
    se = decode_service_envelope(msg)
    print(json.dumps(se))
