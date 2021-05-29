``plover.engine`` -- Steno engine
==================================

.. py:module:: plover.engine

The steno engine is the core of Plover; it handles communication between the
machine and the translation and formatting subsystems, and manages configuration
and dictionaries.

.. autoclass:: StenoEngine(config, keyboard_emulation)
    :members: __init__
    :private-members: _config

    .. autoattribute:: HOOKS
    .. autoattribute:: machine_state
    .. autoattribute:: output
    .. autoattribute:: translator_state
    .. autoattribute:: starting_stroke_state
    .. autoattribute:: dictionaries
    .. automethod:: _in_engine_thread
    .. automethod:: join
    .. automethod:: load_config
    .. automethod:: reset_machine
    .. automethod:: send_backspaces
    .. automethod:: send_string
    .. automethod:: send_key_combination
    .. automethod:: send_engine_command
    .. automethod:: toggle_output
    .. automethod:: set_output
    .. automethod:: __getitem__
    .. automethod:: __setitem__
    .. automethod:: get_suggestions
    .. automethod:: clear_translator_state
    .. automethod:: hook_connect
    .. automethod:: hook_disconnect

    The following methods simply provide a way to access the underlying
    :class:`~plover.steno_dictionary.StenoDictionaryCollection`.
    See the documentation there for more complete information.

    .. automethod:: lookup
    .. automethod:: raw_lookup
    .. automethod:: lookup_from_all
    .. automethod:: raw_lookup_from_all
    .. automethod:: reverse_lookup
    .. automethod:: casereverse_lookup
    .. automethod:: add_dictionary_filter
    .. automethod:: remove_dictionary_filter
    .. automethod:: add_translation

.. class:: StartingStrokeState(attach, capitalize)

    An object representing the starting state of the formatter before any
    strokes are input.

    .. attribute:: attach

        Whether to delete the space before the translation when the initial
        stroke is translated.

    .. attribute:: capitalize

        Whether to capitalize the translation when the initial stroke is
        translated.

.. class:: MachineParams(type, options, keymap)

    An object representing the current state of the machine.

    .. attribute:: type

        The name of the machine. This is the same as the name of the plugin
        that provides the machine's functionality. ``Keyboard`` by default.

    .. attribute:: options

        A dictionary of machine specific options. See :mod:`plover.config`
        for more information.

    .. attribute:: keymap

        A :class:`~plover.machine.keymap.Keymap` mapping the current
        system to this machine.

.. class:: ErroredDictionary(path, exception)

    A placeholder class for a dictionary that failed to load. This is a subclass
    of :class:`~plover.steno_dictionary.StenoDictionary`.

    :param path: The path to the dictionary file.
    :param exception: The exception that caused the dictionary loading to fail.

.. _engine_hooks:

Engine Hooks
------------

Plover uses engine hooks to allow plugins to listen to engine events. By
calling :meth:`engine.hook_connect<StenoEngine.hook_connect>` and passing the
name of one of the hooks below and a function, you can write handlers that are
called when Plover hooks get triggered.

.. py:currentmodule:: None

.. py:function:: stroked(steno_keys)

    The user just sent a stroke. 

    :param List[str] steno_keys: a list of steno keys, for example ``['K-', 'A-', '-T']``.

.. py:function:: translated(old, new)

    The :class:`~plover.formatting.Formatter` has just formatted a sequence of
    :class:`~plover.translation.Translation` objects
    (with :meth:`~plover.formatting.Formatter.format`) and is about to send the output.
   
    :param List[_Action] old: The list of old actions to be undone.
    :param List[_Action] new: The list of new actions to be done.

.. py:function:: machine_state_changed(machine_type, machine_state)

    Either the machine type was changed by the user, or the connection state
    of the machine changed.

    :param str machine_type: the name of the machine (e.g. ``Gemini PR``)
    :param str machine_state: one of ``stopped``, ``initializing``, ``connected`` or ``disconnected``.

.. py:function:: output_changed(enabled)

    The user requested to either enable or disable steno output. 

    :param bool enabled: ``True`` if output is enabled, ``False`` otherwise.

.. py:function:: config_changed(config)

    The configuration was changed, or it was loaded for the first time.

    Call the hook function with the
    :attr:`plover.engine.StenoEngine.config`
    to initialize your plugin based on the full configuration.

    :param Dict[] config: a dictionary containing *only* the changed fields.


.. py:function:: dictionaries_loaded(dictionaries)

    The dictionaries were loaded, either when Plover starts up or the system
    is changed or when the engine is reset.

    :param plover.steno_dictionary.StenoDictionaryCollection dictionaries: the dictionary collection.

.. py:function:: send_string(s)

    Plover just sent the string `s` over keyboard output.

    :param str s:

.. py:function:: send_backspaces(b)

    Plover just sent backspaces over keyboard output. 

    :param int b: the number of backspaces sent.

.. py:function:: send_key_combination(c)

    Plover just sent a keyboard combination over keyboard output.

    :param str c: a string representing the keyboard combination, for example ``Alt_L(Tab)``.

.. py:function:: add_translation()

    The Add Translation command was activated -- open the Add Translation tool.

.. py:function:: focus()

    The Show command was activated -- reopen Plover's main window and bring it
    to the front.

.. py:function:: configure()

    The Configure command was activated -- open the configuration window.

.. py:function:: lookup()

    The Lookup command was activated -- open the Lookup tool.

.. py:function:: quit()

    The Quit command was activated -- wrap up any pending tasks and quit Plover.
