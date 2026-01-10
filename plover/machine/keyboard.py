# -*- coding: utf-8 -*-
# Copyright (c) 2010 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"For use with a computer keyboard (preferably NKRO) as a steno machine."

import json
import threading
from threading import Timer
from dataclasses import dataclass
from typing import Callable, Sequence

from plover import _
from plover.machine.base import StenotypeBase
from plover.misc import boolean
from plover.oslayer.keyboardcontrol import KeyboardCapture
from plover.steno import Stroke


# i18n: Machine name.
_._("Keyboard")


@dataclass(slots=True)
class ChordSimulation:
    on_enter_state: list[Stroke]
    on_exit_state: list[Stroke]
    delay_s: float

    def __init__(self, on_enter_state: Sequence[str] | str = (), on_exit_state: Sequence[str] | str = (), delay: str = "0.2s"):
        if isinstance(on_enter_state, str):
            on_enter_state = [on_enter_state]
        if isinstance(on_exit_state, str):
            on_exit_state = [on_exit_state]
        self.on_enter_state = [Stroke.from_steno(s) for s in on_enter_state]
        self.on_exit_state = [Stroke.from_steno(s) for s in on_exit_state]
        self.delay_s = _parse_delay_s(delay)


def _parse_delay_s(delay: str) -> float:
    delay = delay.strip()
    if not delay.endswith("s"):
        raise ValueError(delay)
    return float(delay[:-1])


class Keyboard(StenotypeBase):
    """Standard stenotype interface for a computer keyboard.

    This class implements the three methods necessary for a standard
    stenotype interface: start_capture, stop_capture, and
    add_callback.

    """

    KEYS_LAYOUT = """
    Escape  F1 F2 F3 F4  F5 F6 F7 F8  F9 F10 F11 F12

      `  1  2  3  4  5  6  7  8  9  0  -  =  \\ BackSpace  Insert Home Page_Up
     Tab  q  w  e  r  t  y  u  i  o  p  [  ]               Delete End  Page_Down
           a  s  d  f  g  h  j  k  l  ;  '      Return
            z  x  c  v  b  n  m  ,  .  /                          Up
                     space                                   Left Down Right
    """
    ACTIONS = ("arpeggiate",)

    def __init__(self, params):
        """Monitor the keyboard's events."""
        super().__init__()
        self._arpeggiate = params["arpeggiate"]
        self._first_up_chord_send = params["first_up_chord_send"]
        self._chord_simulations: dict[Stroke, ChordSimulation] = {
            Stroke.from_steno(trigger): ChordSimulation(**cfg)
            for trigger, cfg in json.loads(params["chord_simulations"]).items()
        }
        self._state_index = 0
        self._hold_timer: Timer | None = None
        self._pending_release: list[Stroke] = []
        self._suppressed_stroke: Stroke | None = None
        if self._arpeggiate and self._first_up_chord_send:
            self._error()
            raise RuntimeError(
                "Arpeggiate and first-up chord send cannot both be enabled!"
            )
        self._is_suppressed = False
        # Currently held keys.
        self._down_keys: set[str] = set()
        if self._first_up_chord_send:
            # If this is True, the first key in a stroke has already been released
            # and subsequent key-up events should not send more strokes
            self._chord_already_sent = False
        else:
            # Collect the keys in the stroke, in case first_up_chord_send is False
            self._stroke_keys: set[str] = set()
        self._keyboard_capture: KeyboardCapture | None = None
        self._last_stroke_key_down_count = 0
        self._stroke_key_down_count = 0
        self._update_bindings()

    def _update_suppression(self) -> None:
        if self._keyboard_capture is None:
            return
        suppressed_keys = self._bindings.keys() if self._is_suppressed else ()
        self._keyboard_capture.suppress(suppressed_keys)

    def _update_bindings(self) -> None:
        self._arpeggiate_key = None
        self._bindings = dict(self.keymap.get_bindings())
        for key, mapping in list(self._bindings.items()):
            if "no-op" == mapping:
                self._bindings[key] = None
            elif "arpeggiate" == mapping:
                if self._arpeggiate:
                    self._bindings[key] = None
                    self._arpeggiate_key = key
                else:
                    # Don't suppress arpeggiate key if it's not used.
                    del self._bindings[key]
        self._update_suppression()

    def set_keymap(self, keymap):
        super().set_keymap(keymap)
        self._update_bindings()

    def start_capture(self) -> None:
        """Begin listening for output from the stenotype machine."""
        self._initializing()
        try:
            self._keyboard_capture = KeyboardCapture()
            self._keyboard_capture.key_down = self._key_down
            self._keyboard_capture.key_up = self._key_up
            self._keyboard_capture.start()
            self._update_suppression()
        except:
            self._error()
            raise
        self._ready()

    def stop_capture(self) -> None:
        """Stop listening for output from the stenotype machine."""
        if self._keyboard_capture is not None:
            self._is_suppressed = False
            self._update_suppression()
            self._keyboard_capture.cancel()
            self._keyboard_capture = None
        self._stopped()

    def set_suppression(self, enabled: bool) -> None:
        self._is_suppressed = enabled
        self._update_suppression()

    def suppress_last_stroke(self, send_backspaces: Callable[[int], None]) -> None:
        send_backspaces(self._last_stroke_key_down_count)
        self._last_stroke_key_down_count = 0

    def _cancel_hold_timer(self) -> None:
        if self._hold_timer is None:
            return
        self._hold_timer.cancel()
        self._hold_timer = None

    def _keys_to_stroke(self, keys: set[str]) -> Stroke:
        return Stroke.from_keys({self._bindings.get(k) for k in keys} - {None})

    def _emit_pending_release(self) -> None:
        if not self._pending_release:
            return
        for stroke in self._pending_release:
            self._notify(stroke.keys())
        self._pending_release = []

    def _check_chord_simulations(self) -> None:
        self._cancel_hold_timer()
        held_stroke = self._keys_to_stroke(self._down_keys)
        cfg = self._chord_simulations.get(held_stroke)
        if not cfg:
            return

        self._suppressed_stroke = held_stroke
        self._pending_release = cfg.on_exit_state

        index = self._state_index
        strokes_on_hold = cfg.on_enter_state
        delay_s = cfg.delay_s

        def fire():
            if self._state_index != index:
                return
            if self._keys_to_stroke(self._down_keys) != held_stroke:
                return
            for stroke in strokes_on_hold:
                self._notify(stroke.keys())

        self._hold_timer = Timer(delay_s, fire)
        self._hold_timer.start()

    def _key_down(self, key: str) -> None:
        """Called when a key is pressed."""
        assert key is not None
        self._cancel_hold_timer()
        self._emit_pending_release()
        self._stroke_key_down_count += 1
        self._down_keys.add(key)
        self._state_index += 1
        self._check_chord_simulations()
        if self._first_up_chord_send:
            self._chord_already_sent = False
        else:
            self._stroke_keys.add(key)

    def _key_up(self, key: str) -> None:
        """Called when a key is released."""
        assert key is not None

        self._cancel_hold_timer()
        self._emit_pending_release()
        self._down_keys.discard(key)
        self._state_index += 1
        self._check_chord_simulations()

        if self._first_up_chord_send:
            if self._chord_already_sent:
                return
        else:
            # A stroke is complete if all pressed keys have been released,
            # and — when arpeggiate mode is enabled — the arpeggiate key
            # is part of it.
            if (
                self._down_keys
                or not self._stroke_keys
                or (self._arpeggiate and self._arpeggiate_key not in self._stroke_keys)
            ):
                return

        self._last_stroke_key_down_count = self._stroke_key_down_count
        if self._first_up_chord_send:
            steno_keys = {self._bindings.get(k) for k in self._down_keys | {key}}
            self._chord_already_sent = True
        else:
            steno_keys = {self._bindings.get(k) for k in self._stroke_keys}
            self._stroke_keys.clear()
        steno_keys -= {None}
        if steno_keys:
            stroke = Stroke.from_keys(steno_keys)
            if self._suppressed_stroke is None or stroke != self._suppressed_stroke:
                self._notify(steno_keys)
        self._stroke_key_down_count = 0
        if not self._down_keys:
            self._suppressed_stroke = None

    @classmethod
    def get_option_info(cls):
        return {
            "arpeggiate": (False, boolean),
            "first_up_chord_send": (False, boolean),
            "chord_simulations": ("{}", str),
        }
