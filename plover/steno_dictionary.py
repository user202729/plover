# Copyright (c) 2013 Hesky Fisher.
# See LICENSE.txt for details.

"""StenoDictionary class and related functions.

A steno dictionary maps sequences of steno strokes to translations.

"""

import collections
import os
import typing

try:
    __sphinx_build__
except NameError:
    __sphinx_build__ = False

if typing.TYPE_CHECKING or __sphinx_build__:
    from typing import Iterable, Tuple, Optional, Dict, List, Set, Sequence, Callable

    Outline = typing.Tuple[str, ...]
    """
    An outline.
    """

    FilterFunction = Callable[[Outline, str], bool]
    """
    A filter function.

    Each filter is a function that
    takes a steno outline (:class:`Outline`) and a translation (``str``)
    and returns a Boolean value.
    If a filter returns ``True``, the corresponding entry is **removed**
    from lookup results.
    """

    

from plover.resource import ASSET_SCHEME, resource_filename, resource_timestamp, resource_update


class StenoDictionary:
    """A steno dictionary.

    This dictionary maps immutable sequences to translations and tracks the
    length of the longest key.
    """

    readonly = False  # type: bool
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

        self._dict = {}  # type: Dict[Outline, str]
        """
        The internal storage of dictionary items.

        It's recommended to use :meth:`__getitem__`, :meth:`__setitem__`, :meth:`update` or
        :meth:`__delitem__` instead of accessing this attribute directly.
        """

        self._longest_key_length = 0  # type: int
        """
		The internal storage for the longest key length.

		It's recommended to use :attr:`_longest_key` (for subclasses), or :attr:`longest_key`
		(outside the class) (which triggers the :attr:`_longest_listener_callbacks`)
        """

        self._longest_listener_callbacks = set()  # type: Set[Callable]
        """
		Internal storage for the function that will be called when :attr:`longest_key` changes.
		
		Do not use this directly, instead use :meth:`add_longest_key_listener`
		and :meth:`remove_longest_key_listener`.
        """


        self.reverse = collections.defaultdict(list)  # type: Dict[str, List[Outline]]
        """
        A dictionary mapping translations to possible steno outlines.
        """

        # Case-insensitive reverse dict
        self.casereverse = collections.defaultdict(list)  # type: Dict[str, List[Outline]]
        """
        A case-insensitive version of :attr:`reverse`.
        """

        self.filters = []  # type: List[FilterFunction]
        """
        """
        

        self.timestamp = 0 # type: int
        """
        The Unix timestamp in seconds when the file was last loaded or saved,
        used to detect external changes.
        """

        self.readonly = False

        self.enabled = True  # type: bool
        """
        ``True`` if the dictionary is enabled, which means Plover can use it to
        look up translations, ``False`` otherwise.
        """

        self.path = None  # type: Optional[str]
        """
        The path to the dictionary file.

        Except in testing, this attribute can be assumed to be not ``None``.
        """




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
        dictionary object. If `resource` refers to an :ref:`asset path<asset_paths>`
        or the file is not writable by the user, the dictionary will be
        read-only.

        This should be called from a subclass, such as
        :class:`~plover.dictionary.json_dict.JsonDictionary`.

        See also: :meth:`_load`.
        """
        filename = resource_filename(resource)
        timestamp = resource_timestamp(filename)
        d = cls()
        d._load(filename)
        if (cls.readonly or
            resource.startswith(ASSET_SCHEME) or
            not os.access(filename, os.W_OK)):
            d.readonly = True
        d.path = resource
        d.timestamp = timestamp
        return d

    def save(self):
        """
        Saves the contents of the dictionary to the file it was loaded from.
        This may need to be called after adding dictionary entries.

        See also: :meth:`_save`.
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

        Subclasses (such as :class:`~plover.dictionary.json_dict.JsonDictionary`)
        should override this method to support specific dictionary formats.
        """
        raise NotImplementedError()

    def _save(self, filename):
        """
        Writes the contents of the dictionary to `filename`.

        Subclasses (such as :class:`~plover.dictionary.json_dict.JsonDictionary`)
        should override this method to support specific dictionary formats.
        """
        raise NotImplementedError()

    @property
    def longest_key(self):
        # type: () -> int
        """The number of strokes in the longest key in this dictionary. 
		
		This property is read-only. Subclasses can modify the value of :attr:`_longest_key`.
		"""
        return self._longest_key

    def __len__(self):
        # type: () -> int
        """
        """
        return self._dict.__len__()

    def __iter__(self):
        # type: () -> Iterable[Tuple[Outline, str]]
        """
        """
        return self._dict.__iter__()

    def __getitem__(self, key):
        # type: (Outline) -> str
        """
        Returns the translation for the steno outline `key`, or raises a
        ``KeyError`` if it is not in the dictionary.
        """
        return self._dict.__getitem__(key)

    def clear(self):
        """
        Removes all entries in the dictionary.
        """
        assert not self.readonly
        self._dict.clear()
        self.reverse.clear()
        self.casereverse.clear()
        self._longest_key = 0

    def items(self):
        # type: () -> Iterable[Tuple[Outline, str]]
        """
        Returns the list of items in the dictionary.
        """
        return self._dict.items()

    def update(self, *args, **kwargs):
        # type: (*Iterable[Tuple[Outline, str]], **Tuple[Outline, str]) -> None
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
        # type: (Outline, str) -> None
        """
        Sets the translation for the steno outline `key` to `value`.
        Fails if the dictionary is read-only.

        Automatically update the value of :attr:`_longest_key`.
        """
        assert not self.readonly
        if key in self:
            del self[key]
        self._longest_key = max(self._longest_key, len(key))
        self._dict[key] = value
        self.reverse[value].append(key)
        self.casereverse[value.lower()].append(value)

    def get(self, key, fallback=None):
        # type: (Outline, Optional[str]) -> Optional[str]
        """
        Returns the translation for the steno outline `key`, or `fallback` if
        it is not in the dictionary.
        """
        return self._dict.get(key, fallback)

    def __delitem__(self, key):
        # type: (Outline) -> None
        """
        Deletes the translation for the steno outline `key`.
        Fails if the dictionary is read-only.

        Automatically update the value of :attr:`_longest_key`.
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
        # type: (Outline) -> bool
        """
        Returns ``True`` if the dictionary contains a translation for the
        steno outline `key`.
        """
        return self.get(key) is not None

    def reverse_lookup(self, value):
        # type: (str) -> Set[Outline]
        """
        Returns the list of steno outlines that translate to `value`.
        """
        return set(self.reverse.get(value, ()))

    def casereverse_lookup(self, value):
        # type: (str) -> Set[Outline]
        """
        Like :meth:`reverse_lookup`, but performs a case-insensitive lookup.
        """
        return set(self.casereverse.get(value, ()))

    @property
    def _longest_key(self):
        """
        """
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
    """
    A collection of steno dictionaries for the same steno system. Plover would
    typically look up outlines in these dictionaries in order until it can
    find a translation, but the interface also allows you to access translations
    from all dictionaries.
    """
    

    def __init__(self, dicts=[]):
        self.dicts = []  # type: List[StenoDictionary]
        """
        A list of :class:`StenoDictionary` objects, in decreasing order of
        priority.
        """

        self.filters = []  # type: List[FilterFunction]
        """
        The list of filters currently active.

        See :class:`FilterFunction` for more details.
        """

        self.longest_key = 0  # type: int
        """
        The number of strokes in the longest key in this dictionary.
        """

        self.longest_key_callbacks = set()  # type: List[Callable[[int], None]]
        """
        The list of functions that get called when the longest key changes.
        Callbacks are called with the new longest key.
        """
        
        self.set_dicts(dicts)

    def set_dicts(self, dicts):
        # type: (List[StenoDictionary]) -> None
        """
        Sets the list of dictionaries to `dicts`.
        """
        self.dicts = []
        for d in self.dicts:
            d.remove_longest_key_listener(self._longest_key_listener)
        self.dicts = dicts[:]
        for d in self.dicts:
            d.add_longest_key_listener(self._longest_key_listener)
        self._longest_key_listener()

    def _lookup(self, key, dicts=None, filters=()):
        # type: (Outline, Optional[List[StenoDictionary]], Sequence[FilterFunction]) -> Optional[str]
        """
        """
        
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
        # type: (Outline, Optional[List[StenoDictionary]], Sequence[FilterFunction]) -> List[Tuple[str, StenoDictionary]]
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
        # type: (Outline) -> Optional[str]
        """
        Returns the first available translation for the steno outline `key`
        from the highest-priority dictionary that is not filtered out by
        :attr:`filters`. If none of the dictionaries have an entry for this
        outline, returns ``None``.
        """
        return self._lookup(key, filters=self.filters)

    def raw_lookup(self, key):
        # type: (Outline) -> Optional[str]
        """
        Like :meth:`lookup`, but does not use :attr:`filters` to filter out results.
        """
        return self._lookup(key)

    def lookup_from_all(self, key):
        # type: (Outline) -> List[Tuple[str, StenoDictionary]]
        """
        Returns the list of translations for the steno outline `key` from
        *all* dictionaries, except those that are filtered out by :attr:`filters`.
        Each translation is of the format `(translation, dictionary)`.
        """
        return self._lookup_from_all(key, filters=self.filters)

    def raw_lookup_from_all(self, key):
        # type: (Outline) -> List[Tuple[str, StenoDictionary]]
        """
        Like :meth:`lookup_from_all`, but returns *all* results, including the ones that
        have been filtered out by :attr:`filters`.
        """
        return self._lookup_from_all(key)

    def reverse_lookup(self, value):
        # type: (str) -> Set[Outline]
        """
        Returns the list of steno outlines from all dictionaries that translate
        to `value`.
        """
        keys = set()  # type: Set[Outline]
        for n, d in enumerate(self.dicts):
            if not d.enabled:
                continue
            # Ignore key if it's overridden by a higher priority dictionary.
            keys.update(k for k in d.reverse_lookup(value)
                        if self._lookup(k, dicts=self.dicts[:n]) is None)
        return keys

    def casereverse_lookup(self, value):
        # type: (str) -> Set[Outline]
        """
        Like :meth:`reverse_lookup`, but performs a case-insensitive lookup.
        You can also access the longest key across all dictionaries:
        """
        keys = set()
        for d in self.dicts:
            if not d.enabled:
                continue
            keys.update(d.casereverse_lookup(value))
        return keys

    def first_writable(self):
        # type: () -> StenoDictionary
        """
        Returns the first dictionary that is writable, or raises ``KeyError``
        if none of the dictionaries are writable.
        """
        for d in self.dicts:
            if not d.readonly:
                return d
        raise KeyError('no writable dictionary')

    def set(self, key, value, path=None):
        # type: (Outline, str, Optional[str]) -> None
        """
        Adds a dictionary entry mapping the steno outline `key` to the
        translation `value`. If `path` is specified, the entry is added there,
        otherwise, it is added to the first writable dictionary.
        """
        if path is None:
            d = self.first_writable()
        else:
            d = self[path]
        d[key] = value

    def save(self, path_list=None):
        """
        Saves all of the dictionaries whose paths are in `path_list`.
        If `path_list` is not specified, all writable dictionaries are saved.
        Fails if any of the dictionaries are read-only.
        """
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
        """
        Returns the dictionary at the specified path, or ``None`` if it is not
        part of this collection.
        """
        for d in self.dicts:
            if d.path == path:
                return d

    def __getitem__(self, path):
        """
        Returns the dictionary at the specified path, or raises a ``KeyError``
        if that dictionary is not part of this collection.
        """
        d = self.get(path)
        if d is None:
            raise KeyError(repr(path))
        return d

    def __iter__(self):
        for d in self.dicts:
            yield d.path

    def add_filter(self, f):
        """
        Adds `f` to the list of filters.
        """
        self.filters.append(f)

    def remove_filter(self, f):
        """
        Removes `f` from the list of filters.
        """
        self.filters.remove(f)

    def add_longest_key_listener(self, callback):
        """
        Adds `callback` to the list of longest key callbacks.
        """
        self.longest_key_callbacks.add(callback)

    def remove_longest_key_listener(self, callback):
        """
        Removes `callback` from the list of longest key callbacks.
        """
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
