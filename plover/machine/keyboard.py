# -*- coding: utf-8 -*-
# Copyright (c) 2010 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"For use with a computer keyboard (preferably NKRO) as a steno machine."

import enum
from collections import OrderedDict
from pathlib import Path
from threading import Thread, Lock
from queue import Queue
import json
import asyncio

from plover import _
from plover.machine.base import StenotypeBase
from plover.misc import boolean
from plover.oslayer.keyboardcontrol import KeyboardCapture
from plover.steno import Stroke
from plover.oslayer.config import CONFIG_DIR


# i18n: Machine name.
_._('Keyboard')


class KeyboardMode(str, enum.Enum):
    DISABLED = "Disabled"
    HYBRID = "Hybrid"
    STENO = "Steno"

    def __str__(self):
        return self.value


class KeyboardModeDict(OrderedDict):
    """
    Subclass of OrderedDict that makes string representation equal to JSON dump,
    to make it easy to pass to configuration.
    """
    def __str__(self):
        return json.dumps(OrderedDict((k, str(v)) for k, v in self.items()), sort_keys=True)


def keyboard_modes_dict(value):
    """
    Convert a configuration value to a dict of {keyboard name: keyboard mode}.
    """
    if isinstance(value, KeyboardModeDict):
        return value
    if isinstance(value, str):
        return KeyboardModeDict((k, KeyboardMode(v)) for k, v in json.loads(value).items())
    raise ValueError(value)


class Keyboard(StenotypeBase):
    """Standard stenotype interface for a computer keyboard.

    This class implements the three methods necessary for a standard
    stenotype interface: start_capture, stop_capture, and
    add_callback.

    """

    KEYS_LAYOUT = '''
    Escape  F1 F2 F3 F4  F5 F6 F7 F8  F9 F10 F11 F12

      `  1  2  3  4  5  6  7  8  9  0  -  =  \\ BackSpace  Insert Home Page_Up
     Tab  q  w  e  r  t  y  u  i  o  p  [  ]               Delete End  Page_Down
           a  s  d  f  g  h  j  k  l  ;  '      Return
            z  x  c  v  b  n  m  ,  .  /                          Up
                     space                                   Left Down Right
    '''
    ACTIONS = ('arpeggiate',)

    def __init__(self, params):
        """Monitor the keyboard's events."""
        super().__init__()
        self._arpeggiate = params['arpeggiate']
        self._first_up_chord_send = params['first_up_chord_send']
        if self._arpeggiate and self._first_up_chord_send:
            self._error()
            raise RuntimeError("Arpeggiate and first-up chord send cannot both be enabled!")
        self._is_suppressed = False
        # Currently held keys.
        self._down_keys = set()
        if self._first_up_chord_send:
            # If this is True, the first key in a stroke has already been released
            # and subsequent key-up events should not send more strokes
            self._chord_already_sent = False
        else:
            # Collect the keys in the stroke, in case first_up_chord_send is False
            self._stroke_keys = set()
        self._keyboard_capture = None
        self._update_bindings()

    def _update_suppression(self):
        if self._keyboard_capture is None:
            return
        suppressed_keys = self._bindings.keys() if self._is_suppressed else ()
        self._keyboard_capture.suppress(suppressed_keys)

    def _update_bindings(self):
        self._arpeggiate_key = None
        self._bindings = dict(self.keymap.get_bindings())
        for key, mapping in list(self._bindings.items()):
            if 'no-op' == mapping:
                self._bindings[key] = None
            elif 'arpeggiate' == mapping:
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

    async def _send_stroke(self, index: int, stroke_on_hold, stroke_on_release):
        #print("hi from task")
        await asyncio.sleep(0.2)
        okay = False
        with self._lock:
            if self._current_state_index == index:
                okay = True
                self._stroke_on_release = stroke_on_release
            #else:
                #print("Not sending stroke", stroke_on_hold, "because state changed with index", self._current_state_index, "vs", index)
        if okay:
            print("Sending stroke", stroke_on_hold)
            self._notify(stroke_on_hold.keys())

    def _thread_fn(self):
        #print("running the loop")
        self._loop.run_forever()
        #print("thread returned")

    def start_capture(self):
        """Begin listening for output from the stenotype machine."""
        self._initializing()
        self._current_state_index = 0
        self._current_state = None
        self._current_task = None
        self._loop = asyncio.new_event_loop()
        self._stroke_on_release = None
        self._events = Queue()
        self._lock = Lock()
        self._thread_object = Thread(target=self._thread_fn)
        self._thread_object.start()

        # idea: hold TPWHR for holding shift etc.
        self._special_actions = {}
        import itertools
        for i in itertools.product(
                (Stroke(0), Stroke("T")),
                (Stroke(0), Stroke("K")),
                (Stroke(0), Stroke("A")),
                (Stroke(0), Stroke("O")),
                ):
            s=sum(i, Stroke("PWR*"))
            self._special_actions[s] = (s|Stroke("-FBLSD"), s|Stroke("-RPGTZ"))

        try:
            self._keyboard_capture = KeyboardCapture(self._ready, self._error)
            self._keyboard_capture.key_down = self._key_down
            self._keyboard_capture.key_up = self._key_up
            if self._keyboard_capture.start():
                self._ready()
            else:
                self._error()
            self._update_suppression()
        except:
            self._error()
            raise

    def stop_capture(self):
        """Stop listening for output from the stenotype machine."""
        self._unhold()
        self._events.put(None)
        self._thread_object.join(timeout=1)
        if self._keyboard_capture is not None:
            self._is_suppressed = False
            self._update_suppression()
            self._keyboard_capture.cancel()
            self._keyboard_capture = None
        self._stopped()

    def set_suppression(self, enabled):
        self._is_suppressed = enabled
        self._update_suppression()

    def suppress_last_stroke(self, send_backspaces):
        pass

    def _unhold(self):
        if self._stroke_on_release is not None:
            print("Release --- Sending stroke", self._stroke_on_release)
            self._notify(self._stroke_on_release.keys())
            self._stroke_on_release = None

    def _keys_to_stroke(self, keys):
        return Stroke({self._bindings.get(k) for k in keys} - {None})

    def _key_down(self, key):
        """Called when a key is pressed."""
        assert key is not None

        if key in self._down_keys:
            return

        self._unhold()
        with self._lock:
            self._current_state_index += 1
            self._down_keys.add(key)

            if self._keys_to_stroke(self._down_keys) in self._special_actions:
                stroke_on_hold, stroke_on_release=self._special_actions[self._keys_to_stroke(self._down_keys)]
                #print("notice state change", self._keys_to_stroke(self._down_keys))
                if self._current_task is not None:
                    self._current_task.cancel()
                self._current_task = asyncio.run_coroutine_threadsafe(
                        (self._send_stroke(self._current_state_index, stroke_on_hold, stroke_on_release)),
                        self._loop)
                #print("task created", self._current_task)

        if self._first_up_chord_send:
            self._chord_already_sent = False
        else:
            self._stroke_keys.add(key)

    def _key_up(self, key):
        """Called when a key is released."""
        assert key is not None
        self._unhold()
        self._current_state_index += 1

        self._down_keys.discard(key)

        if self._first_up_chord_send:
            if self._chord_already_sent:
                return
        else:
            # A stroke is complete if all pressed keys have been released,
            # and — when arpeggiate mode is enabled — the arpeggiate key
            # is part of it.
            if (
                self._down_keys or
                not self._stroke_keys or
                (self._arpeggiate and self._arpeggiate_key not in self._stroke_keys)
            ):
                return

        if self._first_up_chord_send:
            steno_keys = {self._bindings.get(k) for k in self._down_keys | {key}}
            self._chord_already_sent = True
        else:
            steno_keys = {self._bindings.get(k) for k in self._stroke_keys}
            self._stroke_keys.clear()
        steno_keys -= {None}
        if steno_keys:
            self._notify(steno_keys)

    @classmethod
    def get_option_info(cls):
        return {
            'arpeggiate': (False, boolean),
            'first_up_chord_send': (False, boolean),
            'keyboard_default_mode': (KeyboardMode.HYBRID, KeyboardMode),
            'keyboard_modes': (KeyboardModeDict(), keyboard_modes_dict),
        }
