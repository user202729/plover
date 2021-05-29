``plover.steno_dictionary`` -- Steno dictionary
===============================================

.. py:module:: plover.steno_dictionary

This module handles *dictionaries*, which Plover uses to look up translations
for input steno strokes. Plover's steno engine uses a :class:`StenoDictionaryCollection`
to look up possible translations across multiple dictionaries, which can be
configured by the user.

.. autodata:: Outline
.. autodata:: FilterFunction

.. autoclass:: StenoDictionary
   
    .. automethod:: create
    .. automethod:: load
    .. automethod:: save
    .. autoattribute:: enabled
    .. autoattribute:: readonly
    .. autoattribute:: timestamp
    .. autoattribute:: path
    .. automethod:: clear
    .. automethod:: items
    .. automethod:: update

    .. autoattribute:: filters
    .. autoattribute:: _dict
    .. autoattribute:: _longest_key_length
    .. autoattribute:: _longest_listener_callbacks

    The following methods are available to perform various lookup functionality:

    .. automethod:: __iter__
    .. automethod:: __len__
    .. automethod:: __getitem__
    .. automethod:: __setitem__
    .. automethod:: __delitem__
    .. automethod:: __contains__
    .. automethod:: get
    .. autoattribute:: reverse
    .. autoattribute:: casereverse
    .. automethod:: reverse_lookup
    .. automethod:: casereverse_lookup

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


.. autoclass:: StenoDictionaryCollection([dicts=None])
    :private-members: _lookup, _lookup_from_all

    .. autoattribute:: dicts


    .. automethod:: set_dicts
    .. automethod:: first_writable
    .. automethod:: set
    .. automethod:: save
    .. automethod:: __getitem__
    .. automethod:: get

    :class:`StenoDictionaryCollection` supports *filters*, to remove words that
    satisfy certain criteria from lookup results. The interface to work with
    them is as follows:

    .. autoattribute:: filters


    .. automethod:: add_filter
    .. automethod:: remove_filter

    To look up dictionary entries, the interface is similar to
    :class:`StenoDictionary`:

    .. automethod:: lookup
    .. automethod:: raw_lookup
    .. automethod:: lookup_from_all
    .. automethod:: raw_lookup_from_all
    .. automethod:: reverse_lookup
    .. automethod:: casereverse_lookup
    .. autoattribute:: longest_key_callbacks


    .. automethod:: add_longest_key_listener
    .. automethod:: remove_longest_key_listener
