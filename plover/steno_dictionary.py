# Copyright (c) 2013 Hesky Fisher.
# See LICENSE.txt for details.

"""StenoDictionary class and related functions.

A steno dictionary maps sequences of steno strokes to translations.

"""

import collections
import os
import typing

if typing.TYPE_CHECKING:
    from typing import Iterable, Tuple, Optional, Dict

from plover.resource import ASSET_SCHEME, resource_filename, resource_timestamp, resource_update


class StenoDictionary:
    """A steno dictionary.

    This dictionary maps immutable sequences to translations and tracks the
    length of the longest key.

    Attributes:
        timestamp (int): The Unix timestamp in seconds when the file was last loaded or saved,
            used to detect external changes.
        path (Optional[str]): The path to the dictionary file.

            Except in testing, this attribute can be assumed to be not ``None``.
        reverse (Dict[str, List[Tuple[str, ...]]]):
            A dictionary mapping translations to possible steno outlines.
        casereverse (Dict[str, List[Tuple[str, ...]]]):
            A case-insensitive version of :attr:`reverse`.
        enabled (bool):
            ``True`` if the dictionary is enabled, which means Plover can use it to
            look up translations, ``False`` otherwise.
        _dict (Dict[Tuple[str, ...], str]):
            The internal storage of dictionary items.

            It's recommended to use :meth:`__getitem__` and similar methods instead of
            accessing this attribute directly.
    """

    readonly = False
    """
    ``True`` if the dictionary is read-only, either because the dictionary
    class does not support it or the file itself is read-only.
    For most dictionaries this will be ``False``.
    """

    def __init__(self):
        """
        Constructor.

        Normally this should not be used directly, instead :meth:`create` or :meth:`load` of a subclass
        should be used (in that case :attr:`path` will not be ``None``)
        """
        self._dict = {}
        self._longest_key_length = 0
        self._longest_listener_callbacks = set()
        self.reverse = collections.defaultdict(list)
        # Case-insensitive reverse dict
        self.casereverse = collections.defaultdict(list)
        self.filters = []
        self.timestamp = 0
        self.readonly = False
        self.enabled = True
        self.path = None

    def __str__(self):
        return '%s(%r)' % (self.__class__.__name__, self.path)

    def __repr__(self):
        return str(self)

    @classmethod
    def create(cls, resource):
        # type: (str) -> StenoDictionary
        """
        Creates a new empty steno dictionary, saved at the path `resource`.
        If `resource` refers to an :ref:`asset path<asset_paths>` or the
        dictionary class is read-only (i.e. :attr:`readonly` is true), this
        call will fail.
        """
        assert not resource.startswith(ASSET_SCHEME)
        if cls.readonly:
            raise ValueError('%s does not support creation' % cls.__name__)
        d = cls()
        d.path = resource
        return d

    @classmethod
    def load(cls, resource):
        # type: (str) -> StenoDictionary
        """
        Loads a dictionary from the file at `resource` and returns the
        dictionary object. If `resource` refers to an `:ref:`asset path<asset_paths>`
        or the file is not writable by the user, the dictionary will be
        read-only.
        """
        filename = resource_filename(resource)
        timestamp = resource_timestamp(filename)
        d = cls()
        d._load(filename)
        if resource.startswith(ASSET_SCHEME) or \
           not os.access(filename, os.W_OK):
            d.readonly = True
        d.path = resource
        d.timestamp = timestamp
        return d

    def save(self):
        """
        Saves the contents of the dictionary to the file it was loaded from.
        This may need to be called after adding dictionary entries.
        """
        assert not self.readonly
        with resource_update(self.path) as temp_path:
            self._save(temp_path)
        self.timestamp = resource_timestamp(self.path)

    def _load(self, filename):
        """
        Reads the dictionary at `filename` and loads its contents into
        the current dictionary. This is only called when the dictionary is
        first initialized so it is guaranteed to be empty.
        """
        raise NotImplementedError()

    def _save(self, filename):
        """
        Writes the contents of the dictionary to `filename`.
        """
        raise NotImplementedError()

    @property
    def longest_key(self):
        # type: () -> int
        """The number of strokes in the longest key in this dictionary. """
        return self._longest_key

    def __len__(self):
        # type: () -> int
        """
        """
        return self._dict.__len__()

    def __iter__(self):
        # type: () -> Iterable[Tuple[Tuple[str, ...], str]]
        """
        """
        return self._dict.__iter__()

    def __getitem__(self, key):
        # type: (Tuple[str, ...]) -> str
        """
        Returns the translation for the steno outline `key`, or raises a
        ``KeyError`` if it is not in the dictionary.
        """
        return self._dict.__getitem__(key)

    def clear(self):
        """
        Removes all entries in the dictionary.
        """
        self._dict.clear()
        self.reverse.clear()
        self.casereverse.clear()
        self._longest_key = 0

    def items(self):
        # type: () -> Iterable[Tuple[Tuple[str, ...], str]]
        """
        Returns the list of items in the dictionary.
        """
        return self._dict.items()

    def update(self, *args, **kwargs):
        # type: (*Iterable[Tuple[Tuple[str, ...], str]], **Tuple[Tuple[str, ...], str]) -> None
        """
        Adds the entries provided in `args` and `kwargs` to the dictionary.
        Each item in `args` is an iterable containing steno entries (perhaps
        batch-loaded from other dictionaries); each key-value pair in `kwargs`
        corresponds to one steno entry.
        """
        assert not self.readonly
        iterable_list = [
            a.items() if isinstance(a, (dict, StenoDictionary))
            else a for a in args
        ]
        if kwargs:
            iterable_list.append(kwargs.items())
        if not self._dict:
            reverse = self.reverse
            casereverse = self.casereverse
            longest_key = self._longest_key
            assert not (reverse or casereverse or longest_key)
            self._dict = dict(*iterable_list)
            for key, value in self._dict.items():
                reverse[value].append(key)
                casereverse[value.lower()].append(value)
                key_len = len(key)
                if key_len > longest_key:
                    longest_key = key_len
            self._longest_key = longest_key
        else:
            for iterable in iterable_list:
                for key, value in iterable:
                    self[key] = value

    def __setitem__(self, key, value):
        # type (Tuple[str, ...]) -> str
        """
        Sets the translation for the steno outline `key` to `value`.
        Fails if the dictionary is read-only.
        """
        assert not self.readonly
        if key in self:
            del self[key]
        self._longest_key = max(self._longest_key, len(key))
        self._dict[key] = value
        self.reverse[value].append(key)
        self.casereverse[value.lower()].append(value)

    def get(self, key, fallback=None):
        # type: (Tuple[str, ...], Optional[str]) -> Optional[str]
        """
        Returns the translation for the steno outline `key`, or `fallback` if
        it is not in the dictionary.
        """
        return self._dict.get(key, fallback)

    def __delitem__(self, key):
        # type: (Tuple[str, ...]) -> None
        """
        Deletes the translation for the steno outline `key`.
        Fails if the dictionary is read-only.
        """
        assert not self.readonly
        value = self._dict.pop(key)
        self.reverse[value].remove(key)
        self.casereverse[value.lower()].remove(value)
        if len(key) == self.longest_key:
            if self._dict:
                self._longest_key = max(len(x) for x in self._dict)
            else:
                self._longest_key = 0

    def __contains__(self, key):
        # type: (Tuple[str, ...]) -> bool
        """
        Returns ``True`` if the dictionary contains a translation for the
        steno outline `key`.
        """
        return self.get(key) is not None

    def reverse_lookup(self, value):
        return set(self.reverse[value])

    def casereverse_lookup(self, value):
        return set(self.casereverse[value])

    @property
    def _longest_key(self):
        return self._longest_key_length

    @_longest_key.setter
    def _longest_key(self, longest_key):
        if longest_key == self._longest_key_length:
            return
        self._longest_key_length = longest_key
        for callback in self._longest_listener_callbacks:
            callback(longest_key)

    def add_longest_key_listener(self, callback):
        """
        Adds a `callback` that gets called when the :attr:`longest_key` in a
        dictionary changes, such as when entries are added or removed.
        `callback` is called with the new longest key as a parameter.
        """
        self._longest_listener_callbacks.add(callback)

    def remove_longest_key_listener(self, callback):
        """
        Removes `callback` if it has been registered as a callback for
        changes to :attr:`longest_key`. `callback` is called with the new
        longest key as a parameter.
        """
        self._longest_listener_callbacks.remove(callback)


class StenoDictionaryCollection:

    def __init__(self, dicts=[]):
        self.dicts = []
        self.filters = []
        self.longest_key = 0
        self.longest_key_callbacks = set()
        self.set_dicts(dicts)

    def set_dicts(self, dicts):
        for d in self.dicts:
            d.remove_longest_key_listener(self._longest_key_listener)
        self.dicts = dicts[:]
        for d in self.dicts:
            d.add_longest_key_listener(self._longest_key_listener)
        self._longest_key_listener()

    def _lookup(self, key, dicts=None, filters=()):
        if dicts is None:
            dicts = self.dicts
        key_len = len(key)
        if key_len > self.longest_key:
            return None
        for d in dicts:
            if not d.enabled:
                continue
            if key_len > d.longest_key:
                continue
            value = d.get(key)
            if value:
                if not any(f(key, value) for f in filters):
                    return value

    def _lookup_from_all(self, key, dicts=None, filters=()):
        ''' Key lookup from all dictionaries

        Returns list of (value, dictionary) tuples
        '''
        if dicts is None:
            dicts = self.dicts
        key_len = len(key)
        if key_len > self.longest_key:
            return None
        values = []
        for d in dicts:
            if not d.enabled:
                continue
            if key_len > d.longest_key:
                continue
            value = d.get(key)
            if value:
                if not any(f(key, value) for f in filters):
                    values.append((value, d))
        return values

    def __str__(self):
        return 'StenoDictionaryCollection' + repr(tuple(self.dicts))

    def __repr__(self):
        return str(self)

    def lookup(self, key):
        return self._lookup(key, filters=self.filters)

    def raw_lookup(self, key):
        return self._lookup(key)

    def lookup_from_all(self, key):
        return self._lookup_from_all(key, filters=self.filters)

    def raw_lookup_from_all(self, key):
        return self._lookup_from_all(key)

    def reverse_lookup(self, value):
        keys = set()
        for n, d in enumerate(self.dicts):
            if not d.enabled:
                continue
            # Ignore key if it's overridden by a higher priority dictionary.
            keys.update(k for k in d.reverse_lookup(value)
                        if self._lookup(k, dicts=self.dicts[:n]) is None)
        return keys

    def casereverse_lookup(self, value):
        keys = set()
        for d in self.dicts:
            if not d.enabled:
                continue
            keys.update(d.casereverse_lookup(value))
        return keys

    def first_writable(self):
        '''Return the first writable dictionary.'''
        for d in self.dicts:
            if not d.readonly:
                return d
        raise KeyError('no writable dictionary')

    def set(self, key, value, path=None):
        if path is None:
            d = self.first_writable()
        else:
            d = self[path]
        d[key] = value

    def save(self, path_list=None):
        '''Save the dictionaries in <path_list>.

        If <path_list> is None, all writable dictionaries are saved'''
        if path_list is None:
            dict_list = [d for d in self if not d.readonly]
        else:
            dict_list = [self[path] for path in path_list]
        for d in dict_list:
            assert not d.readonly
            d.save()

    def get(self, path):
        for d in self.dicts:
            if d.path == path:
                return d

    def __getitem__(self, path):
        d = self.get(path)
        if d is None:
            raise KeyError(repr(path))
        return d

    def __iter__(self):
        for d in self.dicts:
            yield d.path

    def add_filter(self, f):
        self.filters.append(f)

    def remove_filter(self, f):
        self.filters.remove(f)

    def add_longest_key_listener(self, callback):
        self.longest_key_callbacks.add(callback)

    def remove_longest_key_listener(self, callback):
        self.longest_key_callbacks.remove(callback)
    
    def _longest_key_listener(self, ignored=None):
        if self.dicts:
            new_longest_key = max(d.longest_key for d in self.dicts)
        else:
            new_longest_key = 0
        if new_longest_key != self.longest_key:
            self.longest_key = new_longest_key
            for c in self.longest_key_callbacks:
                c(new_longest_key)
