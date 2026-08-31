"""Procedurally synthesised sound effects.

Nine little WAV files are rendered in pure Python on first launch and cached
under ~/.cache/desktop-destroyer, so the package still ships zero assets.
If the machine has no working audio backend the whole thing quietly no-ops.
"""

from __future__ import annotations

import math
import os
import random
import struct
import wave
from pathlib import Path

from PySide6.QtCore import QUrl

RATE = 22050
BANK_VERSION = 1  # bump to force a re-render of the cache


def _cache_dir() -> Path:
    root = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    path = Path(root) / "desktop-destroyer" / f"sfx-v{BANK_VERSION}"
    path.mkdir(parents=True, exist_ok=True)
    return path


# --------------------------------------------------------------------------
# tiny DSP toolbox
# --------------------------------------------------------------------------


def _lowpass(samples: list[float], amount: float) -> list[float]:
    out, state = [], 0.0
    for value in samples:
        state += amount * (value - state)
        out.append(state)
    return out


def _highpass(samples: list[float], amount: float) -> list[float]:
    low, state, out = 0.0, 0.0, []
    for value in samples:
        state += amount * (value - state)
        out.append(value - state)
    return out


def _norm(samples: list[float], peak: float = 0.85) -> list[float]:
    top = max((abs(v) for v in samples), default=0.0)
    if top < 1e-9:
        return samples
    scale = peak / top
    return [v * scale for v in samples]


def _fade(samples: list[float], attack: int = 60, release: int = 220) -> list[float]:
    n = len(samples)
    attack, release = min(attack, n // 2), min(release, n // 2)
    for i in range(attack):
        samples[i] *= i / attack
    for i in range(release):
        samples[n - 1 - i] *= i / release
    return samples


def _write(path: Path, samples: list[float]) -> None:
    frames = b"".join(
        struct.pack("<h", max(-32767, min(32767, int(v * 32767)))) for v in samples
    )
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(frames)


# --------------------------------------------------------------------------
# the bank
# --------------------------------------------------------------------------


def _hammer(rng: random.Random) -> list[float]:
    n = int(0.34 * RATE)
    body = [
        math.sin(2 * math.pi * (78 - 26 * i / n) * i / RATE) * math.exp(-7.0 * i / n)
        for i in range(n)
    ]
    crack = _highpass([rng.uniform(-1, 1) * math.exp(-40.0 * i / n) for i in range(n)], 0.55)
    return _fade(_norm([b * 0.9 + c * 0.5 for b, c in zip(body, crack)]))


def _gunshot(rng: random.Random) -> list[float]:
    n = int(0.13 * RATE)
    burst = [rng.uniform(-1, 1) * math.exp(-32.0 * i / n) for i in range(n)]
    burst = _lowpass(burst, 0.42)
    thump = [math.sin(2 * math.pi * 110 * i / RATE) * math.exp(-24.0 * i / n) for i in range(n)]
    return _fade(_norm([b + t * 0.6 for b, t in zip(burst, thump)]), 20, 60)


def _saw_loop(rng: random.Random) -> list[float]:
    n = int(0.5 * RATE)
    out = []
    phase = 0.0
    for i in range(n):
        freq = 118 + 9 * math.sin(2 * math.pi * 6 * i / RATE)
        phase = (phase + freq / RATE) % 1.0
        tooth = 2.0 * phase - 1.0
        out.append(tooth * 0.55 + rng.uniform(-1, 1) * 0.18)
    return _norm(_lowpass(out, 0.30), 0.55)


def _flame_loop(rng: random.Random) -> list[float]:
    n = int(0.8 * RATE)
    noise = [rng.uniform(-1, 1) for _ in range(n)]
    roar = _lowpass(_lowpass(noise, 0.06), 0.10)
    hiss = _highpass(noise, 0.5)
    out = [
        r * (1.4 + 0.6 * math.sin(2 * math.pi * 2.3 * i / RATE)) + h * 0.18
        for i, (r, h) in enumerate(zip(roar, hiss))
    ]
    return _norm(out, 0.6)


def _spray_loop(rng: random.Random) -> list[float]:
    n = int(0.6 * RATE)
    noise = [rng.uniform(-1, 1) for _ in range(n)]
    out = _highpass(_lowpass(noise, 0.7), 0.25)
    return _norm([v * (0.8 + 0.2 * math.sin(2 * math.pi * 11 * i / RATE))
                  for i, v in enumerate(out)], 0.45)


def _water_loop(rng: random.Random) -> list[float]:
    n = int(0.7 * RATE)
    noise = [rng.uniform(-1, 1) for _ in range(n)]
    body = _lowpass(noise, 0.22)
    out = list(body)
    for _ in range(14):  # a few bubbles popping through the stream
        start = rng.randrange(0, n - 900)
        freq = rng.uniform(320, 900)
        for i in range(900):
            out[start + i] += 0.5 * math.sin(
                2 * math.pi * (freq + 700 * i / 900) * i / RATE
            ) * math.exp(-9.0 * i / 900)
    return _norm(out, 0.5)


def _phaser(_rng: random.Random) -> list[float]:
    n = int(0.42 * RATE)
    out, phase = [], 0.0
    for i in range(n):
        t = i / n
        freq = 1500 * math.exp(-3.4 * t) + 140
        phase += freq / RATE
        wobble = math.sin(2 * math.pi * 34 * t)
        out.append(math.sin(2 * math.pi * phase + 1.6 * wobble) * math.exp(-3.6 * t))
    return _fade(_norm(out), 30, 400)


def _stamp(rng: random.Random) -> list[float]:
    n = int(0.22 * RATE)
    thunk = [math.sin(2 * math.pi * 150 * i / RATE) * math.exp(-22.0 * i / n) for i in range(n)]
    click = _highpass([rng.uniform(-1, 1) * math.exp(-90.0 * i / n) for i in range(n)], 0.6)
    return _fade(_norm([t + c * 0.35 for t, c in zip(thunk, click)]), 15, 80)


def _chomp(rng: random.Random) -> list[float]:
    n = int(0.11 * RATE)
    out = [0.0] * n
    for _ in range(5):
        start = rng.randrange(0, n - 500)
        for i in range(500):
            out[start + i] += rng.uniform(-1, 1) * math.exp(-26.0 * i / 500)
    return _fade(_norm(_highpass(out, 0.45), 0.6), 10, 60)


BANK = {
    "hammer": (_hammer, False),
    "gunshot": (_gunshot, False),
    "saw": (_saw_loop, True),
    "flame": (_flame_loop, True),
    "spray": (_spray_loop, True),
    "water": (_water_loop, True),
    "phaser": (_phaser, False),
    "stamp": (_stamp, False),
    "chomp": (_chomp, False),
}


def build_cache() -> dict[str, Path]:
    """Render any missing WAV to the cache and return every path."""
    directory = _cache_dir()
    paths = {}
    for name, (make, _loop) in BANK.items():
        path = directory / f"{name}.wav"
        if not path.exists() or path.stat().st_size == 0:
            _write(path, make(random.Random(hash(name) & 0xFFFF)))
        paths[name] = path
    return paths


class Sfx:
    """Plays the bank.  One-shots get a small voice pool so they can overlap."""

    VOICES = 4

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._oneshot: dict[str, list] = {}
        self._loops: dict[str, object] = {}
        self._cursor: dict[str, int] = {}
        self._ready = False
        if enabled:
            self._load()

    def _load(self) -> None:
        """Never let a missing or broken audio stack take the game down."""
        try:
            from PySide6.QtMultimedia import QSoundEffect
        except ImportError:
            return
        try:
            paths = build_cache()
        except OSError:
            return

        # QSoundEffect.Loop.Infinite is an enum member; setLoopCount wants a plain int
        forever = QSoundEffect.Loop.Infinite.value

        try:
            for name, (_make, loops) in BANK.items():
                url = QUrl.fromLocalFile(str(paths[name]))
                if loops:
                    effect = QSoundEffect()
                    effect.setSource(url)
                    effect.setLoopCount(forever)
                    effect.setVolume(0.5)
                    self._loops[name] = effect
                else:
                    pool = []
                    for _ in range(self.VOICES):
                        effect = QSoundEffect()
                        effect.setSource(url)
                        effect.setVolume(0.6)
                        pool.append(effect)
                    self._oneshot[name] = pool
                    self._cursor[name] = 0
        except Exception:
            self._oneshot.clear()
            self._loops.clear()
            return
        self._ready = True

    # -- public API --------------------------------------------------------

    def play(self, name: str, volume: float = 0.6) -> None:
        if not (self.enabled and self._ready):
            return
        pool = self._oneshot.get(name)
        if not pool:
            return
        index = self._cursor[name]
        self._cursor[name] = (index + 1) % len(pool)
        effect = pool[index]
        try:
            effect.setVolume(volume)
            effect.play()
        except Exception:
            self._ready = False

    def loop(self, name: str, on: bool, volume: float = 0.5) -> None:
        if not self._ready:
            return
        effect = self._loops.get(name)
        if effect is None:
            return
        try:
            if on and self.enabled:
                effect.setVolume(volume)
                if not effect.isPlaying():
                    effect.play()
            elif effect.isPlaying():
                effect.stop()
        except Exception:
            self._ready = False

    def stop_all_loops(self) -> None:
        for effect in self._loops.values():
            try:
                if effect.isPlaying():
                    effect.stop()
            except Exception:
                pass

    def set_enabled(self, on: bool) -> None:
        self.enabled = on
        if not on:
            self.stop_all_loops()
        elif not self._ready:
            self._load()
