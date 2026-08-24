"""Train consists and kinematics for the mixed-traffic block section.

Axle geometries are representative public Chinese rolling-stock dimensions
(published dimensions of C70-class gondolas and 25-series 25.5 m
coaches). A train is a list of axle offsets (m, measured back
from the leading axle) with per-axle loads (tonnes/axle), entering the
section at t0 with speed v0 and constant acceleration a.

Coordinates: x increases from counting point A (x=0) to B (x=1003 m).
direction=+1 trains enter at x=0 moving +x; direction=-1 trains enter at
x=SECTION_EXIT moving -x. The leading axle is at the entry boundary at t0.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

WHEEL_CIRCUMFERENCE_M = 2.9   # ~920 mm freight wheel
# (train_id, axle_index) wheels with a flat spot -> periodic impacts
FLAT_WHEELS = {("T1", 30), ("T3", 57), ("T5", 12)}

SECTION_ENTRY = 0.0      # m, outermost sensor at point A
SECTION_EXIT = 1003.0    # m, outermost sensor at point B


def _bogie_vehicle(n_vehicles, axle_pair, bogie2_offset, pitch, first_offset):
    """Axle offsets for n identical 4-axle bogie vehicles coupled in line."""
    offsets = []
    for i in range(n_vehicles):
        base = first_offset + i * pitch
        offsets += [base, base + axle_pair, base + bogie2_offset, base + bogie2_offset + axle_pair]
    return offsets


def loco_6axle(loads_t=21.0):
    """Six-axle electric freight/passenger locomotive (two 3-axle bogies)."""
    offsets = [0.0, 2.25, 4.5, 9.6, 11.85, 14.1]
    return offsets, [loads_t] * 6, 17.0  # trailing coupler length


def c70_wagons(n, rng, loaded_fraction=0.6):
    """C70-class 4-axle freight wagons: 1.83 m bogie wheelbase, 8.7 m bogie
    centers, 13.4 m coupled pitch. Each wagon independently loaded (~20 t/axle)
    or empty (~5.8 t/axle) with small scatter."""
    offsets = _bogie_vehicle(n, 1.83, 8.7, 13.4, 0.0)
    loads = []
    for _ in range(n):
        if rng.random() < loaded_fraction:
            wagon_axle_t = rng.normal(20.0, 0.6)
        else:
            wagon_axle_t = rng.normal(5.8, 0.15)
        loads += [max(wagon_axle_t, 4.5)] * 4
    return offsets, loads, n * 13.4


def coaches_25m(n, rng, axle_t=14.0):
    """25.5 m passenger coaches: 2.4 m bogie wheelbase, 18 m bogie centers."""
    offsets = _bogie_vehicle(n, 2.4, 18.0, 25.5, 0.0)
    loads = [max(rng.normal(axle_t, 0.35), 10.0) for _ in range(4 * n)]
    return offsets, loads, n * 25.5


@dataclass
class Train:
    train_id: str
    t0: float                 # s, leading axle at entry boundary
    direction: int            # +1 (A->B) or -1 (B->A); entry side for shunts
    v0: float                 # m/s at t0
    accel: float              # m/s^2 (constant; unused when reversing)
    axle_offsets: list        # m from leading axle, increasing
    axle_loads_t: list        # tonnes per axle
    note: str = ""
    reverse_at_m: float = 0.0  # >0: shunting move — stop at this depth, back out
    dwell_s: float = 0.0       # stop duration before reversing
    v_return: float = 0.0      # exit speed magnitude

    @property
    def reverses(self) -> bool:
        return self.reverse_at_m > 0.0

    @property
    def n_axles(self) -> int:
        return len(self.axle_offsets)

    def wheel_loads_n(self) -> np.ndarray:
        """One rail carries half of each axle load."""
        return np.asarray(self.axle_loads_t) * 1000.0 * 9.80665 / 2.0

    def _distance(self, t):
        """Path distance of the leading axle relative to the entry boundary.

        Negative before t0 (train approaching from outside the section) so
        the strain onset is smooth, not a parked-train step artifact.
        For shunting moves: uniform deceleration to a stop at reverse_at_m,
        dwell, uniform acceleration back out, then linear away.
        """
        tau = np.asarray(t, dtype=float) - self.t0
        if not self.reverses:
            return self.v0 * tau + 0.5 * self.accel * tau * tau
        S = self.reverse_at_m
        a1 = self.v0 ** 2 / (2.0 * S)
        t1 = self.v0 / a1
        a2 = self.v_return ** 2 / (2.0 * S)
        t2 = self.v_return / a2
        tau2 = tau - t1 - self.dwell_s
        return np.select(
            [tau < 0, tau < t1, tau2 < 0, tau2 < t2],
            [self.v0 * tau,
             self.v0 * tau - 0.5 * a1 * tau ** 2,
             S,
             S - 0.5 * a2 * tau2 ** 2],
            default=-self.v_return * (tau2 - t2))

    def axle_positions(self, t):
        """Positions (n_axles, len(t)) at times t."""
        s = self._distance(t)
        offs = np.asarray(self.axle_offsets)[:, None]
        if self.direction == +1:
            return SECTION_ENTRY + s[None, :] - offs
        return SECTION_EXIT - s[None, :] + offs

    def _path_target(self, x: float, axle_idx: int) -> float:
        off = self.axle_offsets[axle_idx]
        if self.direction == +1:
            return (x - SECTION_ENTRY) + off
        return (SECTION_EXIT - x) + off

    def crossing_time(self, x: float, axle_idx: int, which: str = "first") -> float:
        """Time axle_idx crosses coordinate x ('first' or 'exit' crossing)."""
        d = self._path_target(x, axle_idx)
        if not self.reverses:
            if abs(self.accel) < 1e-12:
                tau = d / self.v0
            else:
                tau = (-self.v0 + np.sqrt(self.v0**2 + 2.0 * self.accel * d)) / self.accel
            return self.t0 + tau
        S = self.reverse_at_m
        a1 = self.v0 ** 2 / (2.0 * S)
        a2 = self.v_return ** 2 / (2.0 * S)
        t1, t2 = self.v0 / a1, self.v_return / a2
        if which == "first":
            if d <= 0:
                return self.t0 + d / self.v0
            tau = (self.v0 - np.sqrt(max(self.v0 ** 2 - 2 * a1 * d, 0.0))) / a1
            return self.t0 + tau
        tau2 = np.sqrt(max(2.0 * (S - d), 0.0) / a2) if d >= 0 else t2 - d / self.v_return
        return self.t0 + t1 + self.dwell_s + tau2

    def crossing_speed(self, x: float, axle_idx: int, which: str = "first") -> float:
        """|speed| of axle_idx as it crosses x."""
        d = self._path_target(x, axle_idx)
        if not self.reverses:
            return float(np.sqrt(max(self.v0 ** 2 + 2.0 * self.accel * d, 0.0)))
        S = self.reverse_at_m
        if which == "first":
            return float(np.sqrt(max(self.v0 ** 2 * (1.0 - d / S), 0.0))) if d > 0 else self.v0
        return float(np.sqrt(max(self.v_return ** 2 * (1.0 - d / S), 0.0))) if d > 0 else self.v_return

    def speed_at_distance(self, d: float) -> float:
        return float(np.sqrt(self.v0**2 + 2.0 * self.accel * max(d, 0.0)))

    def occupancy(self) -> tuple[float, float]:
        """(t_in, t_out). Through: first axle over entry boundary -> last
        axle over exit boundary. Shunt: first axle in -> lead axle back out
        over the same boundary (the lead axle exits last)."""
        entry_x = SECTION_ENTRY if self.direction == +1 else SECTION_EXIT
        if self.reverses:
            return (self.crossing_time(entry_x, 0, "first"),
                    self.crossing_time(entry_x, 0, "exit"))
        exit_x = SECTION_EXIT if self.direction == +1 else SECTION_ENTRY
        return (self.crossing_time(entry_x, 0),
                self.crossing_time(exit_x, self.n_axles - 1))


def build_timetable(rng) -> list[Train]:
    """The six-passage mixed-traffic timetable from the design spec."""
    trains = []

    off, lt, tail = loco_6axle()
    w_off, w_lt, _ = c70_wagons(30, rng)
    trains.append(Train("T1", 100.0, +1, 18.0, 0.0,
                        off + [o + tail for o in w_off], lt + w_lt,
                        note="freight, mixed empty/loaded"))

    off, lt, tail = loco_6axle()
    w_off, w_lt, _ = c70_wagons(2, rng, loaded_fraction=0.0)
    trains.append(Train("TS", 215.0, +1, 10.0, 0.0,
                        off + [o + tail for o in w_off], lt + w_lt,
                        note="shunting work train: enters A, stops inside, reverses out",
                        reverse_at_m=250.0, dwell_s=40.0, v_return=10.0))

    off, lt, tail = loco_6axle()
    c_off, c_lt, _ = coaches_25m(14, rng)
    trains.append(Train("T2", 380.0, +1, 36.0, 0.0,
                        off + [o + tail for o in c_off], lt + c_lt,
                        note="passenger, fast"))

    off, lt, tail = loco_6axle()
    w_off, w_lt, _ = c70_wagons(24, rng)
    trains.append(Train("T3", 560.0, -1, 19.5, 0.0,
                        off + [o + tail for o in w_off], lt + w_lt,
                        note="freight, opposite direction"))

    off, lt, tail = loco_6axle()
    c_off, c_lt, _ = coaches_25m(10, rng)
    trains.append(Train("T4", 800.0, +1, 12.5, 0.25,
                        off + [o + tail for o in c_off], lt + c_lt,
                        note="passenger, accelerating out of station"))

    off, lt, tail = loco_6axle()
    w_off, w_lt, _ = c70_wagons(20, rng)
    trains.append(Train("T5", 1080.0, -1, 17.0, 0.0,
                        off + [o + tail for o in w_off], lt + w_lt,
                        note="freight, passes during solar thermal transient"))

    insp_off, _, _ = coaches_25m(1, rng)
    trains.append(Train("T6", 1300.0, +1, 22.0, 0.0,
                        insp_off, [12.5] * 4,
                        note="track-inspection vehicle, calibration pass 1 (A->B)"))
    insp_off2, _, _ = coaches_25m(1, rng)
    trains.append(Train("T6R", 1400.0, -1, 22.0, 0.0,
                        insp_off2, [12.5] * 4,
                        note="track-inspection vehicle, calibration pass 2 (B->A)"))

    return trains
