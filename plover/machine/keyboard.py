# -*- coding: utf-8 -*-
# Copyright (c) 2010 Joshua Harlan Lifton.
# See LICENSE.txt for details.

"For use with a computer keyboard (preferably NKRO) as a steno machine."

from plover.machine.base import StenotypeBase
from plover.misc import boolean
from plover.oslayer.keyboardcontrol import KeyboardCapture


class Keyboard(StenotypeBase):
    """Standard stenotype interface for a computer keyboard.

    This class implements the three methods necessary for a standard
    stenotype interface: start_capture, stop_capture, and
    add_callback.

    """

    KEYS_LAYOUT = KeyboardCapture.SUPPORTED_KEYS_LAYOUT
    ACTIONS = ('arpeggiate',)

    def __init__(self, params):
        """Monitor the keyboard's events."""
        super().__init__()
        # Warning: arpeggiate currently doesn't work with first-up chord send
        self._arpeggiate = params['arpeggiate']
        self._is_suppressed = False
        # Currently held keys.
        self._down_keys = set()
        self._keyboard_capture = None
        # Number of key down events since the last recognized chord.
        self._last_stroke_key_down_count = 0
        self._stroke_key_down_count = 0
        self._update_bindings()
        self._ignore = False

    def _suppress(self):
        if self._keyboard_capture is None:
            return
        suppressed_keys = self._bindings.keys() if self._is_suppressed else ()
        self._keyboard_capture.suppress_keyboard(suppressed_keys)

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
        self._suppress()

    def set_keymap(self, keymap):
        super().set_keymap(keymap)
        self._update_bindings()

    def start_capture(self):
        """Begin listening for output from the stenotype machine."""
        self._initializing()
        try:
            self._keyboard_capture = KeyboardCapture()
            self._keyboard_capture.key_down = self._key_down
            self._keyboard_capture.key_up = self._key_up
            self._suppress()
            self._keyboard_capture.start()
        except:
            self._error()
            raise
        self._ready()

    def stop_capture(self):
        """Stop listening for output from the stenotype machine."""
        if self._keyboard_capture is not None:
            self._is_suppressed = False
            self._suppress()
            self._keyboard_capture.cancel()
            self._keyboard_capture = None
        self._stopped()

    def set_suppression(self, enabled):
        self._is_suppressed = enabled
        self._suppress()

    def suppress_last_stroke(self, send_backspaces):
        send_backspaces(self._last_stroke_key_down_count)
        self._last_stroke_key_down_count = 0

    def _key_down(self, key):
        """Called when a key is pressed."""
        assert key is not None
        self._stroke_key_down_count += 1
        if key not in self._down_keys:
            self._down_keys.add(key)
            self._ignore = False

    def _key_up(self, key):
        """Called when a key is released."""
        assert key is not None
        if self._ignore:
            self._down_keys.discard(key)
            return
        self._last_stroke_key_down_count = self._stroke_key_down_count
        steno_keys = {self._bindings.get(k) for k in self._down_keys}
        steno_keys -= {None}
        if steno_keys:
            self._notify(steno_keys)
        self._down_keys.discard(key)
        self._stroke_key_down_count = 0
        self._ignore = True

    @classmethod
    def get_option_info(cls):
        return {
            'arpeggiate': (False, boolean),
        }
