# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Joshua Harlan Lifton.
# See LICENSE.txt for details.
#
# keyboardcontrol.py - capturing and injecting X keyboard events
#
# This code requires the X Window System with the 'XInput2' and 'XTest'
# extensions and python-xlib with support for said extensions.

"""Keyboard capture and control using Xlib.

This module provides an interface for basic keyboard event capture and
emulation. Set the key_up and key_down functions of the
KeyboardCapture class to capture keyboard input. Call the send_string
and send_backspaces functions of the KeyboardEmulation class to
emulate keyboard input.

For an explanation of keycodes, keysyms, and modifiers, see:
http://tronche.com/gui/x/xlib/input/keyboard-encoding.html

"""

import os
import select
import threading
import subprocess
from time import sleep

from Xlib import X, XK
from Xlib.display import Display
from Xlib.ext import xinput, xtest
from Xlib.ext.ge import GenericEventCode

from plover import log
from plover.key_combo import add_modifiers_aliases, parse_key_combo
from plover.machine.keyboard_capture import Capture
from plover.output.keyboard import GenericKeyboardEmulation


# Enable support for media keys.
XK.load_keysym_group('xf86')
# Load non-us keyboard related keysyms.
XK.load_keysym_group('xkb')

# Create case insensitive mapping of keyname to keysym.
KEY_TO_KEYSYM = {}
for symbol in sorted(dir(XK)): # Sorted so XK_a is preferred over XK_A.
    if not symbol.startswith('XK_'):
        continue
    name = symbol[3:].lower()
    keysym = getattr(XK, symbol)
    KEY_TO_KEYSYM[name] = keysym
    # Add aliases for `XF86_` keys.
    if name.startswith('xf86_'):
        alias = name[5:]
        if alias not in KEY_TO_KEYSYM:
            KEY_TO_KEYSYM[alias] = keysym
add_modifiers_aliases(KEY_TO_KEYSYM)

XINPUT_DEVICE_ID = xinput.AllDevices
XINPUT_EVENT_MASK = xinput.KeyPressMask | xinput.KeyReleaseMask

KEYCODE_TO_KEY = {
    # Function row.
    67: "F1",
    68: "F2",
    69: "F3",
    70: "F4",
    71: "F5",
    72: "F6",
    73: "F7",
    74: "F8",
    75: "F9",
    76: "F10",
    95: "F11",
    96: "F12",
    # Number row.
    49: "`",
    10: "1",
    11: "2",
    12: "3",
    13: "4",
    14: "5",
    15: "6",
    16: "7",
    17: "8",
    18: "9",
    19: "0",
    20: "-",
    21: "=",
    51: "\\",
    # Upper row.
    24: "q",
    25: "w",
    26: "e",
    27: "r",
    28: "t",
    29: "y",
    30: "u",
    31: "i",
    32: "o",
    33: "p",
    34: "[",
    35: "]",
    # Home row.
    38: "a",
    39: "s",
    40: "d",
    41: "f",
    42: "g",
    43: "h",
    44: "j",
    45: "k",
    46: "l",
    47: ";",
    48: "'",
    # Bottom row.
    52: "z",
    53: "x",
    54: "c",
    55: "v",
    56: "b",
    57: "n",
    58: "m",
    59: ",",
    60: ".",
    61: "/",
    # Other keys.
    22 : "BackSpace",
    119: "Delete",
    116: "Down",
    115: "End",
    9  : "Escape",
    110: "Home",
    118: "Insert",
    113: "Left",
    117: "Page_Down",
    112: "Page_Up",
    36 : "Return",
    114: "Right",
    23 : "Tab",
    111: "Up",
    65 : "space",
}

KEY_TO_KEYCODE = dict(zip(KEYCODE_TO_KEY.values(), KEYCODE_TO_KEY.keys()))

class XEventLoop:

    def __init__(self, on_event, name='XEventLoop'):
        self._on_event = on_event
        self._lock = threading.Lock()
        self._display = Display()
        def error_handler(e, z):
            import traceback
            traceback.print_stack()
            print("X protocol error:", e, z)
        self._display.set_error_handler(error_handler)
        self._thread = threading.Thread(name=name, target=self._run)
        self._pipe = os.pipe()
        self._readfds = (self._pipe[0], self._display.fileno())

    def __enter__(self):
        self._lock.__enter__()
        return self._display

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None and self._display is not None:
            self._display.sync()
        self._lock.__exit__(exc_type, exc_value, traceback)

    def _process_pending_events(self):
        for __ in range(self._display.pending_events()):
            self._on_event(self._display.next_event())

    def _run(self):
        while True:
            with self._lock:
                self._process_pending_events()
            # No more events: sleep until we get new data on the
            # display connection, or on the pipe used to signal
            # the end of the loop.
            rlist, wlist, xlist = select.select(self._readfds, (), ())
            assert not wlist
            assert not xlist
            if self._pipe[0] in rlist:
                break
            # If we're here, rlist should contains the display fd,
            # and the next iteration will find some pending events.

    def start(self):
        self._thread.start()

    def cancel(self):
        if self._thread.is_alive():
            # Wake up the capture thread...
            os.write(self._pipe[1], b'quit')
            # ...and wait for it to terminate.
            self._thread.join()
        for fd in self._pipe:
            os.close(fd)
        self._display.close()
        self._display = None


class KeyboardCapture(Capture):

    def __init__(self):
        super().__init__()
        self._event_loop = None
        self._window = None
        self._suppressed_keys = set()
        self._devices = []

    def _update_devices(self, display):
        # Find all keyboard devices.
        # At the same time also update the event selection to only receive event from that keyboard
        # (as well as events that a keyboard is added/removed)
        # Return bool: whether the keyboard is found or not.
        keyboard_devices = []
        for devinfo in display.xinput_query_device(xinput.AllDevices).devices:
            # Only keep slave devices.
            # Note: we look at pointer devices too, as some keyboards (like the
            # VicTop mechanical gaming keyboard) register 2 devices, including
            # a pointer device with a key class (to fully support NKRO).
            if devinfo.use not in (xinput.SlaveKeyboard, xinput.SlavePointer, xinput.FloatingSlave):
                continue
            if 'g Heavy Industries Georgi Keyboard' != devinfo.name:
                continue
            if devinfo.use != xinput.FloatingSlave:
                subprocess.run(["xinput", "--float", str(devinfo.deviceid)])
            # Ignore disabled devices.
            if not devinfo.enabled:
                continue
            # Check for the presence of a key class.
            for c in devinfo.classes:
                if c.type == xinput.KeyClass:
                    keyboard_devices.append(devinfo.deviceid)
                    break
        old_devices = self._devices
        if keyboard_devices:
            if XINPUT_DEVICE_ID == xinput.AllDevices:
                self._devices = keyboard_devices
            else:
                self._devices = [XINPUT_DEVICE_ID]
        else:
            self._devices = []

        if old_devices != self._devices:
            log.info('XInput devices: %s', ', '.join(map(str, self._devices)))
            self._window = display.screen().root
            self._window.xinput_select_events([
                (deviceid, XINPUT_EVENT_MASK)
                for deviceid in self._devices
                ] + [
                    (xinput.AllDevices, xinput.HierarchyChangedMask)
                    ])
            display.sync()

        return bool(keyboard_devices)

    def _on_event(self, event):
        if event.type != GenericEventCode:
            return
        if event.evtype == xinput.HierarchyChanged:
            if event.data.flags & (xinput.SlaveAdded | xinput.DeviceEnabled |
                    xinput.SlaveRemoved | xinput.DeviceDisabled
                    ):
                assert self._event_loop._lock.locked()
                if self._update_devices(self._event_loop._display):
                    self.on_ready()
                else:
                    self.on_error()
            return

        if event.evtype not in (xinput.KeyPress, xinput.KeyRelease):
            return
        assert event.data.sourceid in self._devices
        keycode = event.data.detail
        modifiers = event.data.mods.effective_mods & ~0b10000 & 0xFF
        key = KEYCODE_TO_KEY.get(keycode)
        if key is None:
            # Not a supported key, ignore...
            return
        # ...or pass it on to a callback method.
        if event.evtype == xinput.KeyPress:
            # Ignore event if a modifier is set.
            if modifiers == 0:
                self.key_down(key)
        elif event.evtype == xinput.KeyRelease:
            self.key_up(key)

    def start(self):
        self._event_loop = XEventLoop(self._on_event, name='KeyboardCapture')
        self._devices = None  # we need to set this to None because in _update_devices there's a check if
        # the list of devices changed, if it does then self._window.xinput_select_events is called to
        # listen to events, and even if the keyboard is disconnected at the start we still have to listen to
        # HierarchyChanged events. So, we force the lists to be different.
        with self._event_loop as display:
            if not display.has_extension('XInputExtension'):
                raise Exception('X11\'s XInput extension is required, but could not be found.')
            result = self._update_devices(display)
            self._event_loop.start()
        return result

    def cancel(self):
        if self._event_loop is None:
            return
        with self._event_loop:
            self._suppress_keys(())
        self._event_loop.cancel()

    def suppress(self, suppressed_keys=()):
        with self._event_loop:
            self._suppress_keys(suppressed_keys)

    def _suppress_keys(self, suppressed_keys):
        pass


# Keysym to Unicode conversion table.
# Taken from xterm/keysym2ucs.c
KEYSYM_TO_UCS = {}
UCS_TO_KEYSYM = {}

def is_latin1(code):
    return 0x20 <= code <= 0x7e or 0xa0 <= code <= 0xff

def uchr_to_keysym(char):
    code = ord(char)
    # Latin-1 characters: direct, 1:1 mapping.
    if is_latin1(code):
        return code
    if code == 0x09:
        return XK.XK_Tab
    if code in (0x0a, 0x0d):
        return XK.XK_Return
    return UCS_TO_KEYSYM.get(code, code | 0x01000000)

def keysym_to_string(keysym):
    # Latin-1 characters: direct, 1:1 mapping.
    if is_latin1(keysym):
        code = keysym
    elif (keysym & 0xff000000) == 0x01000000:
        code = keysym & 0x00ffffff
    else:
        code = KEYSYM_TO_UCS.get(keysym)
        if code is None:
            keysym_str = XK.keysym_to_string(keysym)
            if keysym_str is None:
                keysym_str = ''
            for c in keysym_str:
                if not c.isprintable():
                    keysym_str = ''
                    break
            return keysym_str
    return chr(code)


class KeyboardEmulation(GenericKeyboardEmulation):

    class Mapping:

        def __init__(self, keycode, modifiers, keysym, custom_mapping=None):
            self.keycode = keycode
            self.modifiers = modifiers
            self.keysym = keysym
            self.custom_mapping = custom_mapping

        def __str__(self):
            return '%u:%x=%x[%s]%s' % (
                self.keycode, self.modifiers,
                self.keysym, keysym_to_string(self.keysym),
                '' if self.custom_mapping is None else '*',
            )

    # We can use the first 2 entry of a X11 mapping:
    # keycode and keycode+shift. The 3rd entry is a
    # special keysym to mark the mapping.
    CUSTOM_MAPPING_LENGTH = 3
    # Special keysym to mark custom keyboard mappings.
    PLOVER_MAPPING_KEYSYM = 0x01ffffff
    # Free unused keysym.
    UNUSED_KEYSYM = 0xffffff # XK_VoidSymbol

    def __init__(self):
        super().__init__()
        self._display = Display()
        self._update_keymap()

    def _update_keymap(self):
        '''Analyse keymap, build a mapping of keysym to (keycode + modifiers),
        and find unused keycodes that can be used for unmapped keysyms.
        '''
        self._keymap = {}
        self._custom_mappings_queue = []
        # Analyse X11 keymap.
        keycode = self._display.display.info.min_keycode
        keycode_count = self._display.display.info.max_keycode - keycode + 1
        for mapping in self._display.get_keyboard_mapping(keycode, keycode_count):
            mapping = tuple(mapping)
            while mapping and X.NoSymbol == mapping[-1]:
                mapping = mapping[:-1]
            if not mapping:
                # Free never used before keycode.
                custom_mapping = [self.UNUSED_KEYSYM] * self.CUSTOM_MAPPING_LENGTH
                custom_mapping[-1] = self.PLOVER_MAPPING_KEYSYM
                mapping = custom_mapping
            elif self.CUSTOM_MAPPING_LENGTH == len(mapping) and \
                    self.PLOVER_MAPPING_KEYSYM == mapping[-1]:
                # Keycode was previously used by Plover.
                custom_mapping = list(mapping)
            else:
                # Used keycode.
                custom_mapping = None
            for keysym_index, keysym in enumerate(mapping):
                if keysym == self.PLOVER_MAPPING_KEYSYM:
                    continue
                if keysym_index not in (0, 1, 4, 5):
                    continue
                modifiers = 0
                if 1 == (keysym_index % 2):
                    # The keycode needs the Shift modifier.
                    modifiers |= X.ShiftMask
                if 4 <= keysym_index <= 5:
                    # 3rd (AltGr) level.
                    modifiers |= X.Mod5Mask
                mapping = self.Mapping(keycode, modifiers, keysym, custom_mapping)
                if keysym != X.NoSymbol and keysym != self.UNUSED_KEYSYM:
                    # Some keysym are mapped multiple times, prefer lower modifiers combos.
                    previous_mapping = self._keymap.get(keysym)
                    if previous_mapping is None or mapping.modifiers < previous_mapping.modifiers:
                        self._keymap[keysym] = mapping
                if custom_mapping is not None:
                    self._custom_mappings_queue.append(mapping)
            keycode += 1
        log.debug('keymap:')
        for mapping in sorted(self._keymap.values(), key=lambda m: (m.keycode, m.modifiers)):
            log.debug('%s', mapping)
        log.info('%u custom mappings(s)', len(self._custom_mappings_queue))
        # Determine the backspace mapping.
        backspace_keysym = XK.string_to_keysym('BackSpace')
        self._backspace_mapping = self._get_mapping(backspace_keysym)
        assert self._backspace_mapping is not None
        assert self._backspace_mapping.custom_mapping is None
        # Get modifier mapping.
        self.modifier_mapping = self._display.get_modifier_mapping()

    def send_backspaces(self, count):
        for x in self.with_delay(range(count)):
            self._send_keycode(self._backspace_mapping.keycode,
                               self._backspace_mapping.modifiers)
            self._display.sync()

    def send_string(self, string):
        for char in string:
            keysym = uchr_to_keysym(char)
            # TODO: can we find mappings for multiple keys at a time?
            mapping = self._get_mapping(keysym, automatically_map=False)
            mapping_changed = False
            if mapping is None:
                mapping = self._get_mapping(keysym, automatically_map=True)
                if mapping is None:
                    continue
                self._display.sync()
                self.half_delay()
                mapping_changed = True

            self._send_keycode(mapping.keycode,
                               mapping.modifiers)

            self._display.sync()
            if mapping_changed:
                self.half_delay()
            else:
                self.delay()

    def send_key_combination(self, combo):
        # Parse and validate combo.
        key_events = [
            (keycode, X.KeyPress if pressed else X.KeyRelease) for keycode, pressed
            in parse_key_combo(combo, self._get_keycode_from_keystring)
        ]
        # Emulate the key combination by sending key events.
        for keycode, event_type in self.with_delay(key_events):
            xtest.fake_input(self._display, event_type, keycode)
            self._display.sync()

    def _send_keycode(self, keycode, modifiers=0):
        """Emulate a key press and release.

        Arguments:

        keycode -- An integer in the inclusive range [8-255].

        modifiers -- An 8-bit bit mask indicating if the key
        pressed is modified by other keys, such as Shift, Capslock,
        Control, and Alt.

        """
        modifiers_list = [
            self.modifier_mapping[n][0]
            for n in range(8)
            if (modifiers & (1 << n))
        ]
        # Press modifiers.
        for mod_keycode in modifiers_list:
            xtest.fake_input(self._display, X.KeyPress, mod_keycode)
        # Press and release the base key.
        xtest.fake_input(self._display, X.KeyPress, keycode)
        xtest.fake_input(self._display, X.KeyRelease, keycode)
        # Release modifiers.
        for mod_keycode in reversed(modifiers_list):
            xtest.fake_input(self._display, X.KeyRelease, mod_keycode)

    def _get_keycode_from_keystring(self, keystring):
        '''Find the physical key <keystring> is mapped to.

        Return None of if keystring is not mapped.
        '''
        keysym = KEY_TO_KEYSYM.get(keystring)
        if keysym is None:
            return None
        mapping = self._get_mapping(keysym, automatically_map=False)
        if mapping is None:
            return None
        return mapping.keycode

    def _get_mapping(self, keysym, automatically_map=True):
        """Return a keycode and modifier mask pair that result in the keysym.

        There is a one-to-many mapping from keysyms to keycode and
        modifiers pairs; this function returns one of the possibly
        many valid mappings, or None if no mapping exists, and a
        new one cannot be added.

        Arguments:

        keysym -- A key symbol.

        """
        mapping = self._keymap.get(keysym)
        if mapping is None:
            # Automatically map?
            if not automatically_map:
                # No.
                return None
            # Can we map it?
            if 0 == len(self._custom_mappings_queue):
                # Nope...
                return None
            mapping = self._custom_mappings_queue.pop(0)
            previous_keysym = mapping.keysym
            keysym_index = mapping.custom_mapping.index(previous_keysym)
            # Update X11 keymap.
            mapping.custom_mapping[keysym_index] = keysym
            self._display.change_keyboard_mapping(mapping.keycode, [mapping.custom_mapping])
            # Update our keymap.
            if previous_keysym in self._keymap:
                del self._keymap[previous_keysym]
            mapping.keysym = keysym
            self._keymap[keysym] = mapping
            log.debug('new mapping: %s', mapping)
            # Move custom mapping back at the end of
            # the queue so we don't use it too soon.
            self._custom_mappings_queue.append(mapping)
        elif mapping.custom_mapping is not None:
            # Same as above; prevent mapping
            # from being reused to soon.
            self._custom_mappings_queue.remove(mapping)
            self._custom_mappings_queue.append(mapping)
        return mapping

