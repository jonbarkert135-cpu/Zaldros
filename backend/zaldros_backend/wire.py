"""The D-Bus wire format, implemented from the specification.

Why we own this
---------------
Zaldros needs to read `a{sv}` from UPower, NetworkManager, BlueZ, udisks2 and systemd — that is
what a property dictionary is on D-Bus, and there is no way around it. PySide6's QtDBus cannot:
`QDBusArgument.asVariant()` comes back as a null converter (`pointerToPython(): SbkConverter is
null for VoidPtr`), so every dictionary and every variant reply decodes to `None`. Measured on
PySide6 6.x in this tree against a live `dbus-daemon`, not assumed.

The alternatives were a C dependency (python3-dbus / gi), a vendored pure-Python library
(jeepney, MIT) or this. Both of the first two would have to be installed by the CI workflow, and
the app that pushes this repository is not allowed to touch `.github/workflows/*`, so a dependency
we cannot install is a test suite we cannot run. This file has no dependency at all: the standard
library and the specification.

Reference: D-Bus Specification, "Message Protocol" / "Type System"
(https://dbus.freedesktop.org/doc/dbus-specification.html), fetched 2026-08-27.

Everything here is pure functions over bytes, so it is testable without a bus, and it is fuzzed
round-trip in the test suite.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

LITTLE_ENDIAN = ord("l")
BIG_ENDIAN = ord("B")
PROTOCOL_VERSION = 1

# Message types (spec §Message Format, "Message types")
METHOD_CALL = 1
METHOD_RETURN = 2
ERROR = 3
SIGNAL = 4

# Header flags
NO_REPLY_EXPECTED = 0x1
NO_AUTO_START = 0x2
ALLOW_INTERACTIVE_AUTHORIZATION = 0x4

# Header field codes
FIELD_PATH = 1
FIELD_INTERFACE = 2
FIELD_MEMBER = 3
FIELD_ERROR_NAME = 4
FIELD_REPLY_SERIAL = 5
FIELD_DESTINATION = 6
FIELD_SENDER = 7
FIELD_SIGNATURE = 8
FIELD_UNIX_FDS = 9

# Alignment of every fixed-size type, in bytes (spec, "Type System" table).
_ALIGNMENT = {
    "y": 1, "b": 4, "n": 2, "q": 2, "i": 4, "u": 4, "x": 8, "t": 8, "d": 8,
    "s": 4, "o": 4, "g": 1, "a": 4, "(": 8, "{": 8, "v": 1, "h": 4,
}

_FIXED = {
    "y": ("B", 1), "n": ("<h", 2), "q": ("<H", 2), "i": ("<i", 4), "u": ("<I", 4),
    "x": ("<q", 8), "t": ("<Q", 8), "d": ("<d", 8), "h": ("<I", 4),
}


class WireError(ValueError):
    """A message we cannot parse or a value we cannot send. Never swallowed."""


def alignment(signature: str) -> int:
    return _ALIGNMENT.get(signature[0], 1)


def _pad(length: int, to: int) -> int:
    return (-length) % to


def split_signature(signature: str) -> list[str]:
    """"a{sv}i" -> ["a{sv}", "i"]. A signature is a concatenation of complete types."""
    out: list[str] = []
    index = 0
    while index < len(signature):
        end = _complete_type_end(signature, index)
        out.append(signature[index:end])
        index = end
    return out


def _complete_type_end(signature: str, index: int) -> int:
    if index >= len(signature):
        raise WireError(f"signature ends mid-type: {signature!r}")
    code = signature[index]
    if code == "a":
        return _complete_type_end(signature, index + 1)
    if code in "({":
        closing = ")" if code == "(" else "}"
        depth = 0
        for position in range(index, len(signature)):
            if signature[position] in "({":
                depth += 1
            elif signature[position] in ")}":
                depth -= 1
                if depth == 0:
                    return position + 1
        raise WireError(f"unbalanced {code!r} in {signature!r}")
    if code not in "ybnqiuxtdsogvh":
        raise WireError(f"unknown type code {code!r} in {signature!r}")
    return index + 1


# --------------------------------------------------------------------------------------------
# Marshalling
# --------------------------------------------------------------------------------------------

class Variant:
    """An explicit variant. Needed when the value's type cannot be guessed from Python.

    `Variant("s", "wlan0")` marshals as `v` holding a string. Reading a variant gives back the
    plain Python value, never this wrapper — the wrapper exists only for the send direction.
    """

    __slots__ = ("signature", "value")

    def __init__(self, signature: str, value: Any) -> None:
        self.signature = signature
        self.value = value

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Variant({self.signature!r}, {self.value!r})"

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, Variant) and other.signature == self.signature
                and other.value == self.value)


def marshal(signature: str, values: list[Any], offset: int = 0) -> bytes:
    """Marshal `values` according to `signature`, starting at stream position `offset`.

    `offset` matters: D-Bus alignment is relative to the start of the whole message, not to the
    start of the body, so the body of a message must be marshalled with the header's length as
    the offset. Getting this wrong produces messages that a real bus rejects with
    "Message is corrupted" — which is exactly how this was caught.
    """
    parts: list[bytes] = []
    position = offset
    types = split_signature(signature)
    if len(types) != len(values):
        raise WireError(f"signature {signature!r} wants {len(types)} values, got {len(values)}")
    for one, value in zip(types, values):
        chunk, position = _marshal_one(one, value, position)
        parts.append(chunk)
    return b"".join(parts)


def _marshal_one(signature: str, value: Any, position: int) -> tuple[bytes, int]:
    code = signature[0]
    pad = b"\0" * _pad(position, alignment(signature))
    position += len(pad)

    if code == "b":
        data = struct.pack("<I", 1 if value else 0)
    elif code in _FIXED:
        fmt, _size = _FIXED[code]
        if code == "y":
            data = struct.pack("B", int(value) & 0xFF)
        elif code == "d":
            data = struct.pack("<d", float(value))
        else:
            data = struct.pack(fmt, int(value))
    elif code in "so":
        raw = str(value).encode("utf-8")
        data = struct.pack("<I", len(raw)) + raw + b"\0"
    elif code == "g":
        raw = str(value).encode("ascii")
        if len(raw) > 255:
            raise WireError("signature longer than 255 bytes")
        data = bytes([len(raw)]) + raw + b"\0"
    elif code == "v":
        if not isinstance(value, Variant):
            raise WireError(f"a variant must be sent as Variant(signature, value), got {value!r}")
        inner_sig, _ = _marshal_one("g", value.signature, position)
        inner_pos = position + len(inner_sig)
        inner, _ = _marshal_one(value.signature, value.value, inner_pos)
        data = inner_sig + inner
    elif code == "a":
        data = _marshal_array(signature, value, position)
    elif code == "(":
        data = _marshal_struct(signature, value, position)
    else:  # pragma: no cover - split_signature already rejects unknown codes
        raise WireError(f"cannot marshal {signature!r}")
    return pad + data, position + len(data)


def _marshal_array(signature: str, value: Any, position: int) -> bytes:
    element = signature[1:]
    # The length is a UINT32 followed by padding to the element's alignment; the length counts
    # the elements only, never that padding.
    body_start = position + 4
    body_start += _pad(body_start, alignment(element))
    parts: list[bytes] = []
    cursor = body_start
    if element.startswith("{"):
        key_sig, value_sig = _dict_entry_types(element)
        items = value.items() if isinstance(value, dict) else value
        for key, item in items:
            pad = b"\0" * _pad(cursor, 8)
            cursor += len(pad)
            key_bytes, cursor = _marshal_one(key_sig, key, cursor)
            value_bytes, cursor = _marshal_one(value_sig, item, cursor)
            parts.append(pad + key_bytes + value_bytes)
    elif element == "y" and isinstance(value, (bytes, bytearray)):
        parts.append(bytes(value))
        cursor += len(value)
    else:
        for item in value:
            chunk, cursor = _marshal_one(element, item, cursor)
            parts.append(chunk)
    body = b"".join(parts)
    if len(body) > 67108864:
        raise WireError("array longer than the 64 MiB the specification allows")
    prefix = struct.pack("<I", len(body))
    return prefix + b"\0" * _pad(position + 4, alignment(element)) + body


def _marshal_struct(signature: str, value: Any, position: int) -> bytes:
    members = split_signature(signature[1:-1])
    if len(members) != len(value):
        raise WireError(f"struct {signature!r} wants {len(members)} members, got {len(value)}")
    parts: list[bytes] = []
    cursor = position
    for member_sig, item in zip(members, value):
        chunk, cursor = _marshal_one(member_sig, item, cursor)
        parts.append(chunk)
    return b"".join(parts)


def _dict_entry_types(signature: str) -> tuple[str, str]:
    inner = signature[1:-1]
    types = split_signature(inner)
    if len(types) != 2:
        raise WireError(f"a dict entry has exactly two types, {signature!r} has {len(types)}")
    return types[0], types[1]


# --------------------------------------------------------------------------------------------
# Unmarshalling
# --------------------------------------------------------------------------------------------

class _Reader:
    def __init__(self, data: bytes, endian: int = LITTLE_ENDIAN, offset: int = 0) -> None:
        self.data = data
        self.position = offset
        self.prefix = "<" if endian == LITTLE_ENDIAN else ">"

    def align(self, to: int) -> None:
        self.position += _pad(self.position, to)

    def take(self, count: int) -> bytes:
        end = self.position + count
        if end > len(self.data):
            raise WireError(f"message truncated: wanted {count} bytes at {self.position}")
        chunk = self.data[self.position:end]
        self.position = end
        return chunk

    def fixed(self, code: str) -> Any:
        fmt, size = _FIXED[code]
        self.align(size)
        raw = self.take(size)
        if code == "y":
            return raw[0]
        return struct.unpack(self.prefix + fmt[1:], raw)[0]

    def read(self, signature: str) -> Any:
        code = signature[0]
        if code == "b":
            self.align(4)
            return struct.unpack(self.prefix + "I", self.take(4))[0] != 0
        if code in _FIXED:
            return self.fixed(code)
        if code in "so":
            self.align(4)
            length = struct.unpack(self.prefix + "I", self.take(4))[0]
            raw = self.take(length)
            self.take(1)
            return raw.decode("utf-8", "replace")
        if code == "g":
            length = self.take(1)[0]
            raw = self.take(length)
            self.take(1)
            return raw.decode("ascii", "replace")
        if code == "v":
            inner = self.read("g")
            types = split_signature(inner)
            if len(types) != 1:
                raise WireError(f"a variant holds exactly one type, got {inner!r}")
            return self.read(types[0])
        if code == "a":
            return self._read_array(signature)
        if code == "(":
            self.align(8)
            return tuple(self.read(member) for member in split_signature(signature[1:-1]))
        raise WireError(f"cannot read {signature!r}")

    def _read_array(self, signature: str) -> Any:
        element = signature[1:]
        self.align(4)
        length = struct.unpack(self.prefix + "I", self.take(4))[0]
        self.align(alignment(element))
        end = self.position + length
        if end > len(self.data):
            raise WireError("array claims more bytes than the message holds")
        if element == "y":
            return self.take(length)
        if element.startswith("{"):
            key_sig, value_sig = _dict_entry_types(element)
            out: dict[Any, Any] = {}
            while self.position < end:
                self.align(8)
                key = self.read(key_sig)
                out[key] = self.read(value_sig)
            return out
        items = []
        while self.position < end:
            items.append(self.read(element))
        return items


def unmarshal(signature: str, data: bytes, endian: int = LITTLE_ENDIAN,
              offset: int = 0) -> list[Any]:
    reader = _Reader(data, endian, offset)
    return [reader.read(one) for one in split_signature(signature)]


# --------------------------------------------------------------------------------------------
# Messages
# --------------------------------------------------------------------------------------------

@dataclass
class Message:
    """One D-Bus message, in the form the rest of Zaldros speaks."""

    type: int = METHOD_CALL
    flags: int = 0
    serial: int = 0
    path: str | None = None
    interface: str | None = None
    member: str | None = None
    error_name: str | None = None
    reply_serial: int | None = None
    destination: str | None = None
    sender: str | None = None
    signature: str = ""
    body: list[Any] = field(default_factory=list)

    @property
    def is_error(self) -> bool:
        return self.type == ERROR

    def error_text(self) -> str:
        """The human-readable half of an error reply, or "" for anything else."""
        if not self.is_error:
            return ""
        detail = str(self.body[0]) if self.body else ""
        return f"{self.error_name}: {detail}" if detail else str(self.error_name)

    def to_bytes(self) -> bytes:
        fields: list[tuple[int, Variant]] = []
        if self.path is not None:
            fields.append((FIELD_PATH, Variant("o", self.path)))
        if self.interface is not None:
            fields.append((FIELD_INTERFACE, Variant("s", self.interface)))
        if self.member is not None:
            fields.append((FIELD_MEMBER, Variant("s", self.member)))
        if self.error_name is not None:
            fields.append((FIELD_ERROR_NAME, Variant("s", self.error_name)))
        if self.reply_serial is not None:
            fields.append((FIELD_REPLY_SERIAL, Variant("u", self.reply_serial)))
        if self.destination is not None:
            fields.append((FIELD_DESTINATION, Variant("s", self.destination)))
        if self.signature:
            fields.append((FIELD_SIGNATURE, Variant("g", self.signature)))

        body = marshal(self.signature, list(self.body), offset=0) if self.signature else b""
        # The fixed header is 12 bytes, then the header-field array. The body starts at the next
        # 8-byte boundary after the header, and its own alignment restarts there — which is why
        # the body is marshalled at offset 0 above.
        head = struct.pack("<BBBBII", LITTLE_ENDIAN, self.type, self.flags, PROTOCOL_VERSION,
                           len(body), self.serial)
        head += marshal("a(yv)", [fields], offset=len(head))
        head += b"\0" * _pad(len(head), 8)
        return head + body

    @classmethod
    def from_bytes(cls, data: bytes) -> tuple["Message", int]:
        """Parse one message; returns it and how many bytes it consumed."""
        if len(data) < 16:
            raise WireError("a D-Bus message is at least 16 bytes")
        endian = data[0]
        if endian not in (LITTLE_ENDIAN, BIG_ENDIAN):
            raise WireError(f"unknown endianness byte {endian!r}")
        prefix = "<" if endian == LITTLE_ENDIAN else ">"
        _, kind, flags, version, body_length, serial = struct.unpack(prefix + "BBBBII", data[:12])
        if version != PROTOCOL_VERSION:
            raise WireError(f"protocol version {version}, we speak {PROTOCOL_VERSION}")
        reader = _Reader(data, endian, 12)
        fields = reader.read("a(yv)")
        reader.align(8)
        header_end = reader.position
        total = header_end + body_length
        if len(data) < total:
            raise WireError("incomplete message")

        message = cls(type=kind, flags=flags, serial=serial)
        for code, value in fields:
            if code == FIELD_PATH:
                message.path = value
            elif code == FIELD_INTERFACE:
                message.interface = value
            elif code == FIELD_MEMBER:
                message.member = value
            elif code == FIELD_ERROR_NAME:
                message.error_name = value
            elif code == FIELD_REPLY_SERIAL:
                message.reply_serial = value
            elif code == FIELD_DESTINATION:
                message.destination = value
            elif code == FIELD_SENDER:
                message.sender = value
            elif code == FIELD_SIGNATURE:
                message.signature = value
        if message.signature:
            message.body = unmarshal(message.signature, data[:total], endian, header_end)
        return message, total


def message_length(data: bytes) -> int | None:
    """How long the message starting at `data[0]` is, or None if the header is not complete yet.

    Used by the reader loop so it can pull exactly one message off the socket without guessing.
    """
    if len(data) < 16:
        return None
    endian = data[0]
    prefix = "<" if endian == LITTLE_ENDIAN else ">"
    body_length = struct.unpack(prefix + "I", data[4:8])[0]
    fields_length = struct.unpack(prefix + "I", data[12:16])[0]
    header_end = 16 + fields_length
    header_end += _pad(header_end, 8)
    return header_end + body_length
