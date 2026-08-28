"""Audio: PipeWire, through the only control surface it has.

PipeWire is not on D-Bus. Volume lives on a node's `Props` parameter in the PipeWire protocol, and
the mixer logic that turns that into one number per device is a WirePlumber module reachable from
libwireplumber or its Lua API — there is no `org.freedesktop.PipeWire` interface to call
[WirePlumber 0.5 documentation, 2026-08-27]. Binding libwireplumber would drag GObject
introspection into the shell process.

So this is the one facet that runs a program, and it says so in `source`: every reading is marked
`wpctl` or `pactl`, never dressed up as something it is not. The parsing is pinned by tests
against wpctl's and pactl's real output, and unknown output is an unavailable reading, not a zero.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Callable

from .bus import Result
from .catalog import Audio
from .reading import Reading

VOLUME_LINE = re.compile(r"Volume:\s*([0-9]*\.?[0-9]+)")
PACTL_VOLUME = re.compile(r"(\d+)%")
NO_SERVER = "аудиосервер не найден"
NO_SINK = "устройство вывода не найдено"


class AudioFacet:
    def __init__(self, runner=subprocess.run) -> None:
        self._run = runner
        self._tool: str | None = None
        self._looked = False

    def tool(self) -> str | None:
        """`wpctl` if PipeWire is here, `pactl` if only PulseAudio is, otherwise nothing."""
        if not self._looked:
            self._looked = True
            self._tool = (Audio.WPCTL if shutil.which(Audio.WPCTL)
                          else Audio.PACTL if shutil.which(Audio.PACTL) else None)
        return self._tool

    def _text(self, *args: str, timeout: float = 2.0) -> str | None:
        try:
            done = self._run(list(args), capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.SubprocessError):
            return None
        if done.returncode != 0:
            return None
        return done.stdout

    # -- output ------------------------------------------------------------------------------
    def volume(self) -> Reading:
        tool = self.tool()
        if tool is None:
            return Reading.missing(NO_SERVER, "none")
        if tool == Audio.WPCTL:
            out = self._text(Audio.WPCTL, "get-volume", Audio.DEFAULT_SINK)
            if out is None:
                return Reading.missing(NO_SINK, Audio.WPCTL)
            match = VOLUME_LINE.search(out)
            if match is None:
                return Reading.missing(NO_SINK, Audio.WPCTL)
            return Reading.measured(round(float(match.group(1)) * 100), "", Audio.WPCTL,
                                    muted="[MUTED]" in out)
        volume_out = self._text(Audio.PACTL, "get-sink-volume", "@DEFAULT_SINK@")
        if volume_out is None:
            return Reading.missing(NO_SINK, Audio.PACTL)
        match = PACTL_VOLUME.search(volume_out)
        if match is None:
            return Reading.missing(NO_SINK, Audio.PACTL)
        mute_out = self._text(Audio.PACTL, "get-sink-mute", "@DEFAULT_SINK@") or ""
        return Reading.measured(int(match.group(1)), "", Audio.PACTL,
                                muted="yes" in mute_out.lower())

    def set_volume(self, percent: int) -> Result:
        """Set the output volume. Clamped to 0..100: the slider cannot ask for 150 %.

        wpctl would happily boost past 1.0 and clip; Windows's slider stops at the top, so ours
        does too.
        """
        tool = self.tool()
        value = max(0, min(100, int(percent)))
        if tool == Audio.WPCTL:
            return self._command(Audio.WPCTL, "set-volume", Audio.DEFAULT_SINK,
                                 f"{value / 100:.2f}")
        if tool == Audio.PACTL:
            return self._command(Audio.PACTL, "set-sink-volume", "@DEFAULT_SINK@", f"{value}%")
        return Result.bad(NO_SERVER, "none")

    def set_muted(self, muted: bool) -> Result:
        tool = self.tool()
        if tool == Audio.WPCTL:
            return self._command(Audio.WPCTL, "set-mute", Audio.DEFAULT_SINK,
                                 "1" if muted else "0")
        if tool == Audio.PACTL:
            return self._command(Audio.PACTL, "set-sink-mute", "@DEFAULT_SINK@",
                                 "1" if muted else "0")
        return Result.bad(NO_SERVER, "none")

    def toggle_muted(self) -> Result:
        tool = self.tool()
        if tool == Audio.WPCTL:
            return self._command(Audio.WPCTL, "set-mute", Audio.DEFAULT_SINK, "toggle")
        if tool == Audio.PACTL:
            return self._command(Audio.PACTL, "set-sink-mute", "@DEFAULT_SINK@", "toggle")
        return Result.bad(NO_SERVER, "none")

    # -- input -------------------------------------------------------------------------------
    def microphone(self) -> Reading:
        """The microphone's level and mute state — the second slider in Windows quick settings."""
        tool = self.tool()
        if tool != Audio.WPCTL:
            return Reading.missing(NO_SERVER if tool is None else "не опрошено", str(tool))
        out = self._text(Audio.WPCTL, "get-volume", Audio.DEFAULT_SOURCE)
        if out is None:
            return Reading.missing("микрофон не найден", Audio.WPCTL)
        match = VOLUME_LINE.search(out)
        if match is None:
            return Reading.missing("микрофон не найден", Audio.WPCTL)
        return Reading.measured(round(float(match.group(1)) * 100), "", Audio.WPCTL,
                                muted="[MUTED]" in out)

    def set_microphone_muted(self, muted: bool) -> Result:
        if self.tool() != Audio.WPCTL:
            return Result.bad(NO_SERVER, str(self.tool()))
        return self._command(Audio.WPCTL, "set-mute", Audio.DEFAULT_SOURCE, "1" if muted else "0")

    # -- devices -----------------------------------------------------------------------------
    def outputs(self) -> list[Reading]:
        """The output devices, with the default one marked — the Windows sound flyout's list.

        `wpctl status` marks the default with a "*". Parsed conservatively: a line we do not
        recognise is skipped rather than guessed at.
        """
        if self.tool() != Audio.WPCTL:
            return []
        out = self._text(Audio.WPCTL, "status")
        if out is None:
            return []
        devices: list[Reading] = []
        section = ""
        for line in out.splitlines():
            stripped = line.strip()
            if stripped.endswith(":") and "├" not in line and "│" not in line:
                section = stripped[:-1].casefold()
                continue
            if "Sinks:" in line:
                section = "sinks"
                continue
            if "Sources:" in line:
                section = "sources"
                continue
            if section != "sinks":
                continue
            match = re.search(r"(\*?)\s*(\d+)\.\s+(.+?)\s*\[vol:", stripped)
            if match is None:
                continue
            devices.append(Reading.measured(int(match.group(2)), match.group(3).strip(),
                                            Audio.WPCTL, default=match.group(1) == "*"))
        return devices

    def streams(self) -> list[Reading]:
        """Per-application volume — the «Микшер громкости» list.

        `wpctl status` lists playback streams under «Streams:»; each one carries the node id and
        the application's own name. The volume of a single stream is then read with
        `wpctl get-volume <id>`, because the status listing does not print it for streams.
        A stream whose volume cannot be read is listed with an unavailable reading, not with 100 %.
        """
        if self.tool() != Audio.WPCTL:
            return []
        out = self._text(Audio.WPCTL, "status")
        if out is None:
            return []
        streams: list[Reading] = []
        in_streams = False
        for line in out.splitlines():
            stripped = line.strip(" │├└─*")
            if stripped.startswith("Streams:"):
                in_streams = True
                continue
            if not in_streams:
                continue
            if stripped.endswith(":") and not stripped[0:1].isdigit():
                in_streams = stripped.startswith("Streams")
                continue
            match = re.match(r"(\d+)\.\s+(.+)", stripped)
            if match is None:
                continue
            node_id, name = int(match.group(1)), match.group(2).strip()
            volume = self._node_volume(node_id)
            if volume is None:
                streams.append(Reading.missing("громкость потока не читается",
                                               f"{Audio.WPCTL} get-volume {node_id}"))
                continue
            percent, muted = volume
            streams.append(Reading.measured(percent, name, Audio.WPCTL, node=node_id,
                                            muted=muted))
        return streams

    def _node_volume(self, node_id: int) -> tuple[int, bool] | None:
        text = self._text(Audio.WPCTL, "get-volume", str(node_id))
        if text is None:
            return None
        match = VOLUME_LINE.search(text)
        if match is None:
            return None
        return (round(float(match.group(1)) * 100), "[MUTED]" in text)

    def set_stream_volume(self, node_id: int, percent: int) -> Result:
        """Set one application's volume. Clamped to 0..150 like every Linux mixer, because
        PipeWire happily accepts 500 % and destroys the user's ears."""
        if self.tool() != Audio.WPCTL:
            return Result.bad(NO_SERVER, str(self.tool()))
        value = max(0, min(int(percent), 150))
        return self._command(Audio.WPCTL, "set-volume", str(int(node_id)), f"{value / 100:.2f}")

    def set_stream_muted(self, node_id: int, muted: bool) -> Result:
        if self.tool() != Audio.WPCTL:
            return Result.bad(NO_SERVER, str(self.tool()))
        return self._command(Audio.WPCTL, "set-mute", str(int(node_id)), "1" if muted else "0")

    def inputs(self) -> list[Reading]:
        """Recording devices, the same way `outputs()` reads playback ones."""
        if self.tool() != Audio.WPCTL:
            return []
        out = self._text(Audio.WPCTL, "status")
        if out is None:
            return []
        devices: list[Reading] = []
        section = ""
        for line in out.splitlines():
            stripped = line.strip()
            if "Sinks:" in line:
                section = "sinks"
                continue
            if "Sources:" in line:
                section = "sources"
                continue
            if section != "sources":
                continue
            match = re.search(r"(\*?)\s*(\d+)\.\s+(.+?)\s*\[vol:", stripped)
            if match is None:
                continue
            devices.append(Reading.measured(int(match.group(2)), match.group(3).strip(),
                                            Audio.WPCTL, default=match.group(1) == "*"))
        return devices

    def set_default_input(self, node_id: int) -> Result:
        if self.tool() != Audio.WPCTL:
            return Result.bad(NO_SERVER, str(self.tool()))
        return self._command(Audio.WPCTL, "set-default", str(int(node_id)))

    def set_default_output(self, node_id: int) -> Result:
        if self.tool() != Audio.WPCTL:
            return Result.bad(NO_SERVER, str(self.tool()))
        return self._command(Audio.WPCTL, "set-default", str(int(node_id)))

    # -- change notification -----------------------------------------------------------------
    def watch(self, _callback: Callable[[], None]) -> list:
        """Nothing to subscribe to.

        There is no signal to wait on without linking libwireplumber, so audio is the one reading
        the shell refreshes on demand: when the volume flyout opens, when the user drags the
        slider, and when a media key is pressed. That is honest and it costs nothing while the
        panel is closed — which is the whole point of not polling it every second.
        """
        return []

    def _command(self, *args: str) -> Result:
        try:
            done = self._run(list(args), capture_output=True, text=True, timeout=3.0)
        except (OSError, subprocess.SubprocessError) as exc:
            return Result.bad(f"{args[0]}: {exc}", args[0])
        if done.returncode != 0:
            return Result.bad((done.stderr or "").strip() or f"{args[0]} exit {done.returncode}",
                              args[0])
        return Result.good(True, args[0])
