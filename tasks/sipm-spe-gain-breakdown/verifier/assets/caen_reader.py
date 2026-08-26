"""Independent reader for the DT5720 standard-firmware event stream.

Written from the event-format description alone and deliberately kept separate
from the oracle implementation: it walks the file record by record with
`struct`, so a mistake in the oracle's vectorised bit manipulation cannot be
mirrored here and grade itself correct.

Slow on purpose. It is only ever pointed at a handful of files.
"""

from __future__ import annotations

import itertools
import struct
from dataclasses import dataclass
from pathlib import Path

HEADER_MARKER = 0xA
HEADER_WORDS = 4
TIME_TAG_BITS = 31  # bits[31:0] of word 4, 31-bit counter + roll-over flag
EVENT_COUNTER_BITS = 24  # bits[23:0] of word 3


@dataclass(frozen=True)
class Event:
    counter: int
    time_tag: int
    channels: list[list[int]]


def read_events(path: Path, limit: int | None = None) -> list[Event]:
    """Decode events from one binary file, oldest first."""
    events: list[Event] = []
    with Path(path).open("rb") as handle:
        while limit is None or len(events) < limit:
            header = handle.read(HEADER_WORDS * 4)
            if len(header) < HEADER_WORDS * 4:
                break
            word0, word1, word2, word3 = struct.unpack("<4I", header)

            if (word0 >> 28) != HEADER_MARKER:
                raise ValueError(f"{Path(path).name}: bad header marker at event {len(events)}")
            record_words = word0 & 0x0FFFFFFF
            n_channels = bin(word1).count("1")
            if n_channels == 0:
                raise ValueError(f"{Path(path).name}: empty channel mask")

            payload_words = record_words - HEADER_WORDS
            payload = handle.read(payload_words * 4)
            if len(payload) < payload_words * 4:
                break

            # Pack2 mode: two 12-bit samples per 32-bit word, the earlier one
            # right-aligned in the low half.
            words = struct.unpack(f"<{payload_words}I", payload)
            samples: list[int] = []
            for word in words:
                samples.append(word & 0xFFFF)
                samples.append((word >> 16) & 0xFFFF)

            per_channel = len(samples) // n_channels
            channels = [
                samples[index * per_channel : (index + 1) * per_channel]
                for index in range(n_channels)
            ]
            events.append(
                Event(
                    counter=word2 & ((1 << EVENT_COUNTER_BITS) - 1),
                    time_tag=word3 & ((1 << TIME_TAG_BITS) - 1),
                    channels=channels,
                )
            )
    return events


def count_events(path: Path) -> int:
    """Number of complete records in a file, from its own headers."""
    total = 0
    with Path(path).open("rb") as handle:
        while True:
            header = handle.read(4)
            if len(header) < 4:
                return total
            (word0,) = struct.unpack("<I", header)
            if (word0 >> 28) != HEADER_MARKER:
                raise ValueError(f"{Path(path).name}: bad header marker at event {total}")
            record_words = word0 & 0x0FFFFFFF
            skipped = handle.read((record_words - 1) * 4)
            if len(skipped) < (record_words - 1) * 4:
                return total
            total += 1


def counter_steps(counters: list[int]) -> list[int]:
    """Event-counter increments, unwrapped over the counter's own width."""
    modulus = 1 << EVENT_COUNTER_BITS
    return [
        (later - earlier) % modulus
        for earlier, later in itertools.pairwise(counters)
    ]


def time_tag_steps(time_tags: list[int]) -> list[int]:
    """Trigger-time-tag increments, unwrapped over the tag's own width.

    The tag is a free-running 31-bit counter, so a wrap shows up as a negative
    raw difference and is corrected by taking the difference modulo 2**31.
    """
    modulus = 1 << TIME_TAG_BITS
    return [
        (later - earlier) % modulus
        for earlier, later in itertools.pairwise(time_tags)
    ]
