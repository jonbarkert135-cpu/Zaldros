"""The D-Bus wire format, checked against the specification's own rules.

We implement the marshalling ourselves (see `wire.py` for why), so these are the tests that stop a
silent protocol bug: a message that is one padding byte wrong is not "slightly wrong", it makes the
bus drop the connection with "Message is corrupted" and every reading in the shell goes blank.
"""

from __future__ import annotations

import random

import pytest

from zaldros_backend.wire import (Message, METHOD_CALL, METHOD_RETURN, Variant, WireError,
                                  marshal, message_length, split_signature, unmarshal)


def strip(value):
    """Variants marshal from a wrapper and unmarshal to the plain value."""
    if isinstance(value, Variant):
        return strip(value.value)
    if isinstance(value, dict):
        return {key: strip(item) for key, item in value.items()}
    if isinstance(value, list):
        return [strip(item) for item in value]
    if isinstance(value, tuple):
        return tuple(strip(item) for item in value)
    return value


CASES = [
    ("y", [255]), ("b", [True]), ("b", [False]), ("n", [-32768]), ("q", [65535]),
    ("i", [-2147483648]), ("u", [4294967295]), ("x", [-2 ** 63]), ("t", [2 ** 64 - 1]),
    ("d", [1.5]), ("s", [""]), ("s", ["Привет, мир"]), ("o", ["/org/freedesktop/UPower"]),
    ("g", ["a{sv}"]), ("as", [[]]), ("as", [["a", "bb", "ccc"]]),
    ("ay", [b"\x00\x01\xff"]), ("aay", [[b"/dev/sda1\x00", b"/\x00"]]),
    ("a{sv}", [{"Percentage": Variant("d", 87.5), "State": Variant("u", 2),
                "IconName": Variant("s", "battery")}]),
    ("(sun)", [("x", 3, -2)]), ("a(oa{sv})", [[("/dev/0", {"P": Variant("d", 55.0)})]]),
    ("sa{sv}as", ["org.freedesktop.UPower.Device", {"k": Variant("b", False)}, ["z"]]),
    ("a{oa{sa{sv}}}", [{"/org/bluez/hci0": {"org.bluez.Adapter1": {
        "Powered": Variant("b", True), "Alias": Variant("s", "Zaldros")}}}]),
    ("susssasa{sv}i", ["Zaldros", 0, "", "Заголовок", "Текст", ["default", "Открыть"],
                       {"urgency": Variant("y", 2)}, -1]),
]


@pytest.mark.parametrize("signature,values", CASES)
def test_every_type_survives_a_round_trip(signature, values):
    assert unmarshal(signature, marshal(signature, values)) == strip(values)


@pytest.mark.parametrize("signature,values", CASES)
def test_round_trip_holds_at_every_starting_offset(signature, values):
    """Alignment is relative to the start of the message, not of the value.

    A body marshalled at offset 0 and read back at offset 0 can pass while the real message —
    where the body starts after a variable-length header — is corrupt. So every case is checked
    at eight offsets, which covers every alignment class D-Bus has.
    """
    for offset in range(8):
        raw = b"\x00" * offset + marshal(signature, values, offset=offset)
        assert unmarshal(signature, raw, offset=offset) == strip(values)


def test_signatures_split_into_complete_types():
    assert split_signature("a{sv}i") == ["a{sv}", "i"]
    assert split_signature("(ii)a(oa{sv})") == ["(ii)", "a(oa{sv})"]
    assert split_signature("") == []


@pytest.mark.parametrize("bad", ["a", "(ii", "z", "a{s}"])
def test_a_signature_we_cannot_parse_raises_instead_of_guessing(bad):
    with pytest.raises(WireError):
        split_signature(bad) if bad != "a{s}" else marshal(bad, [{}])


def test_a_variant_must_say_what_it_holds():
    with pytest.raises(WireError):
        marshal("v", ["just a string"])


def test_value_count_must_match_the_signature():
    with pytest.raises(WireError):
        marshal("ss", ["one"])


def test_message_round_trip_keeps_every_header_field():
    message = Message(type=METHOD_CALL, serial=7, path="/org/freedesktop/UPower",
                      interface="org.freedesktop.DBus.Properties", member="GetAll",
                      destination="org.freedesktop.UPower", signature="s",
                      body=["org.freedesktop.UPower"])
    parsed, length = Message.from_bytes(message.to_bytes())
    assert length == len(message.to_bytes())
    for field in ("type", "serial", "path", "interface", "member", "destination", "signature",
                  "body"):
        assert getattr(parsed, field) == getattr(message, field)


def test_message_length_is_readable_from_the_first_sixteen_bytes():
    """The reader loop must know how much to take without parsing the whole message."""
    raw = Message(type=METHOD_RETURN, serial=3, reply_serial=2, signature="as",
                  body=[["a" * 100, "b"]]).to_bytes()
    assert message_length(raw) == len(raw)
    assert message_length(raw[:15]) is None


def test_a_truncated_message_is_an_error_not_a_half_reading():
    raw = Message(type=METHOD_RETURN, serial=1, reply_serial=1, signature="s",
                  body=["hello"]).to_bytes()
    with pytest.raises(WireError):
        Message.from_bytes(raw[:-3])


def test_random_property_dictionaries_survive(monkeypatch):
    """A fuzz pass over the one shape every service answers with: a{sv} of mixed types."""
    generator = random.Random(20260828)
    for _ in range(200):
        payload = {}
        for index in range(generator.randint(0, 6)):
            kind = generator.choice(["s", "u", "b", "d", "x", "as", "ay", "o"])
            value = {"s": "".join(generator.choice("абвxyz /-_") for _ in range(generator.randint(0, 12))),
                     "u": generator.randint(0, 2 ** 32 - 1),
                     "b": generator.choice([True, False]),
                     "d": generator.uniform(-1e6, 1e6),
                     "x": generator.randint(-2 ** 40, 2 ** 40),
                     "as": ["a" * generator.randint(0, 5) for _ in range(generator.randint(0, 3))],
                     "ay": bytes(generator.randint(0, 255) for _ in range(generator.randint(0, 9))),
                     "o": "/" + "/".join("p" * generator.randint(1, 4)
                                         for _ in range(generator.randint(1, 3)))}[kind]
            payload[f"Key{index}"] = Variant(kind, value)
        offset = generator.randint(0, 7)
        raw = marshal("a{sv}", [payload], offset=offset)
        assert unmarshal("a{sv}", b"\x00" * offset + raw, offset=offset) == [strip(payload)]
