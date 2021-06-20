# Copyright (c) 2010-2011 Joshua Harlan Lifton.
# See LICENSE.txt for details.

# TODO: unit test this file

"""Generic stenography data models.

This module contains the following class:

Stroke -- A data model class that encapsulates a sequence of steno keys.

"""

import re

from plover import system

import typing
try:
    __sphinx_build__
except NameError:
    __sphinx_build__ = False

if typing.TYPE_CHECKING or __sphinx_build__:
    from typing import List
    from plover.steno_dictionary import Outline


STROKE_DELIMITER = '/'
"""
The character used to separate successive strokes.
This is equivalent to ``/``.
"""


_NUMBERS = set('0123456789')
_IMPLICIT_NUMBER_RX = re.compile('(^|[1-4])([6-9])')

def normalize_stroke(stroke):
    # type: (str) -> str
    """
    Return the :ref:`canonical<canonical>` steno notation for the stroke.

    Arguments:
        stroke: Steno notation for a stroke.
    """
    letters = set(stroke)
    if letters & _NUMBERS:
        if system.NUMBER_KEY in letters:
            stroke = stroke.replace(system.NUMBER_KEY, '')
        # Insert dash when dealing with 'explicit' numbers
        m = _IMPLICIT_NUMBER_RX.search(stroke)
        if m is not None:
            start = m.start(2)
            return stroke[:start] + '-' + stroke[start:]
    if '-' in letters:
        if stroke.endswith('-'):
            stroke = stroke[:-1]
        elif letters & system.IMPLICIT_HYPHENS:
            stroke = stroke.replace('-', '')
    return stroke

def normalize_steno(strokes_string):
    # type: (str) -> Outline
    """
    Return the :ref:`canonical<canonical>` steno notation for the outline.
    This simply splits the string into individual strokes and calls
    :func:`normalize_stroke` on them.

    Parameters:
        strokes_string: Steno notation for an outline.

    Return:
        A tuple consisting of the canonical steno notation for each stroke.
    """
    if not strokes_string:
        return ()
    return tuple(normalize_stroke(stroke) for stroke
                 in strokes_string.split(STROKE_DELIMITER))

def sort_steno_keys(steno_keys):
    # type: (List[str]) -> List[str]
    """
    Return a new list of steno keys, sorted based on the current system's
    steno order.

    Parameters:
        steno_keys: A list of steno keys, not necessarily in steno order.
    """
    return sorted(steno_keys, key=lambda x: system.KEY_ORDER.get(x, -1))

def sort_steno_strokes(strokes_list):
    # type: (List[Outline]) -> List[Outline]
    '''
    Return a new list of outlines sorted by the number of strokes first, and
    then the length of each stroke (number of keys).
    
    Parameters:
        strokes_list: A list of tuples representing outlines in steno notation.
    '''
    return sorted(strokes_list, key=lambda x: (len(x), sum(map(len, x))))


class Stroke:
    """A standardized data model for stenotype machine strokes.

    This class standardizes the representation of a stenotype chord. A stenotype
    chord can be any sequence of stenotype keys that can be simultaneously
    pressed. Nearly all stenotype machines offer the same set of keys that can
    be combined into a chord, though some variation exists due to duplicate
    keys. This class accounts for such duplication, imposes the standard
    stenographic ordering on the keys, and combines the keys into a single
    string (called RTFCRE for historical reasons).

    """

    def __init__(self, steno_keys):
        # type: (List[str]) -> None
        """Create a steno stroke by formatting steno keys.

        Arguments:

            steno_keys: A sequence of pressed keys.

        """
        # Remove duplicate keys and save local versions of the input 
        # parameters.
        steno_keys_set = set(steno_keys)
        if not steno_keys_set:
            self.steno_keys = []
            self.rtfcre = ''  # type: str
            """
            The normalized (or `canonical`) steno notation for this stroke.

            .. _canonical:

            The canonical steno notation for a stroke has the following properties:

              * All of the keys are in steno order

              * There is a hyphen *only if* at least one key on the right bank is
                pressed *and* this key is not an implicit separator

              * Number keys are written as numbers rather than using the number
                key (for example, ``-8`` rather than ``#-L``)
            """
            return
        steno_keys = list(sort_steno_keys(steno_keys_set))  # type: List[str]
        """
        A *sorted* list of the steno keys that compose this stroke.
        """

        # Convert strokes involving the number bar to numbers.
        if system.NUMBER_KEY in steno_keys:
            numeral = False
            for i, e in enumerate(steno_keys):
                if e in system.NUMBERS:
                    steno_keys[i] = system.NUMBERS[e]
                    steno_keys_set.remove(e)
                    steno_keys_set.add(steno_keys[i])
                    numeral = True
            if numeral:
                steno_keys.remove(system.NUMBER_KEY)
                steno_keys_set.remove(system.NUMBER_KEY)

        if steno_keys_set & system.IMPLICIT_HYPHEN_KEYS:
            self.rtfcre = ''.join(key.strip('-') for key in steno_keys)
        else:
            pre = ''.join(k.strip('-') for k in steno_keys if k[-1] == '-' or 
                          k == system.NUMBER_KEY)
            post = ''.join(k.strip('-') for k in steno_keys if k[0] == '-')
            self.rtfcre = '-'.join([pre, post]) if post else pre

        self.steno_keys = steno_keys

        self.is_correction = (self.rtfcre == system.UNDO_STROKE_STENO)  # type: bool
        """
        Whether this stroke is a `correction` stroke, and can be used to undo
        the previous stroke.
        """

    def __hash__(self):
        return hash(self.rtfcre)

    def __str__(self):
        if self.is_correction:
            prefix = '*'
        else:
            prefix = ''
        return '%sStroke(%s : %s)' % (prefix, self.rtfcre, self.steno_keys)

    def __eq__(self, other):
        return (isinstance(other, Stroke)
                and self.steno_keys == other.steno_keys)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return str(self)

