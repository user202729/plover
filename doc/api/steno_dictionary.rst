``plover.steno_dictionary`` -- Steno dictionary
===============================================

.. py:module:: plover.steno_dictionary

This module handles *dictionaries*, which Plover uses to look up translations
for input steno strokes. Plover's steno engine uses a :class:`StenoDictionaryCollection`
to look up possible translations across multiple dictionaries, which can be
configured by the user.

.. autoclass:: StenoDictionary

   
    .. automethod:: create
    .. automethod:: load
    .. automethod:: save
    .. automethod:: clear
    .. automethod:: items
    .. automethod:: update

    The following methods are available to perform various lookup functionality:

    .. automethod:: __iter__
    .. automethod:: __len__
    .. automethod:: __getitem__
    .. automethod:: __setitem__
    .. automethod:: __delitem__
    .. automethod:: __contains__
    .. automethod:: get
    
    .. method:: reverse_lookup(value)

        Returns the list of steno outlines that translate to `value`.

        :type value: str
        :rtype: List[Tuple[str]]

    .. method:: casereverse_lookup(value)

        Like :meth:`reverse_lookup`, but performs a case-insensitive lookup.

    The dictionary provides the following interface to access the longest key
    in the dictionary, to be used to automatically filter out some dictionaries
    to speed up lookups.

    .. autoproperty:: longest_key
    .. automethod:: add_longest_key_listener
    .. automethod:: remove_longest_key_listener


    In addition, dictionary implementors *should* implement the following
    methods for reading and writing to dictionary files:

    .. automethod:: _load
    .. automethod:: _save


.. class:: StenoDictionaryCollection([dicts=None])

    A collection of steno dictionaries for the same steno system. Plover would
    typically look up outlines in these dictionaries in order until it can
    find a translation, but the interface also allows you to access translations
    from all dictionaries.

    .. attribute:: dicts

        A list of :class:`StenoDictionary` objects, in decreasing order of
        priority.

    .. method:: set_dicts(dicts)

        Sets the list of dictionaries to `dicts`.

    .. method:: first_writable()

        Returns the first dictionary that is writable, or raises ``KeyError``
        if none of the dictionaries are writable.

    .. method:: set(key, value[, path=None])

        Adds a dictionary entry mapping the steno outline `key` to the
        translation `value`. If `path` is specified, the entry is added there,
        otherwise, it is added to the first writable dictionary.

    .. method:: save([path_list=None])

        Saves all of the dictionaries whose paths are in `path_list`.
        If `path_list` is not specified, all writable dictionaries are saved.
        Fails if any of the dictionaries are read-only.

    .. method:: __getitem__(path)

        Returns the dictionary at the specified path, or raises a ``KeyError``
        if that dictionary is not part of this collection.

    .. method:: get(path)

        Returns the dictionary at the specified path, or ``None`` if it is not
        part of this collection.

    :class:`StenoDictionaryCollection` supports *filters*, to remove words that
    satisfy certain criteria from lookup results. The interface to work with
    them is as follows:

    .. attribute:: filters

        The list of filters currently active. Each filter is a function that
        takes a steno outline and a translation and returns a Boolean value.
        If a filter returns ``True``, the corresponding entry is **removed**
        from lookup results.

        :type: List[Function[(Tuple[str], str), bool]]

    .. method:: add_filter(f)

        Adds `f` to the list of filters.

    .. method:: remove_filter(f)

        Removes `f` from the list of filters.

    To look up dictionary entries, the interface is similar to
    :class:`StenoDictionary`:

    .. method:: lookup(key)

        Returns the first available translation for the steno outline `key`
        from the highest-priority dictionary that is not filtered out by
        :attr:`filters`. If none of the dictionaries have an entry for this
        outline, returns ``None``.

        :type key: Tuple[str]
        :rtype: str | None

    .. method:: raw_lookup(key)

        Like :meth:`lookup`, but returns *all* results, including the ones that
        have been filtered out by :attr:`filters`.

    .. method:: lookup_from_all(key)

        Returns the list of translations for the steno outline `key` from
        *all* dictionaries, except those that are filtered out by :attr:`filters`.
        Each translation is of the format `(translation, dictionary)`.

        :type key: Tuple[str]
        :rtype: List[Tuple[str, :class:`StenoDictionary`]]

    .. method:: raw_lookup_from_all(key)

        Like :meth:`lookup`, but returns *all* results, including the ones that
        have been filtered out by :attr:`filters`.

    .. method:: reverse_lookup(value)

        Returns the list of steno outlines from all dictionaries that translate
        to `value`.

        :rtype: List[Tuple[str]]

    .. method:: casereverse_lookup(value)

        Like :meth:`reverse_lookup`, but performs a case-insensitive lookup.

    You can also access the longest key across all dictionaries:

    .. attribute:: longest_key_callbacks

        The list of functions that get called when the longest key changes.
        Callbacks are called with the new longest key.

        :type: List[Function[(int)]]

    .. method:: add_longest_key_listener(callback)

        Adds `callback` to the list of longest key callbacks.

    .. method:: remove_longest_key_listener(callback)

        Removes `callback` from the list of longest key callbacks.
