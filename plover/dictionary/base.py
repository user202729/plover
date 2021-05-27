# Copyright (c) 2013 Hesky Fisher
# See LICENSE.txt for details.

# TODO: maybe move this code into the StenoDictionary itself. The current saver 
# structure is odd and awkward.
# TODO: write tests for this file

"""Common elements to all dictionary formats."""

from os.path import splitext
import functools
import threading
import typing

from plover.registry import registry


def _get_dictionary_class(filename):
    # type: (str) -> type
    """
    Get the class of a dictionary format given the file name.
    """
    extension = splitext(filename)[1].lower()[1:]
    try:
        dict_module = registry.get_plugin('dictionary', extension).obj
    except KeyError:
        raise ValueError(
            'Unsupported extension: %s. Supported extensions: %s' %
            (extension, ', '.join(plugin.name for plugin in
                                  registry.list_plugins('dictionary'))))
    return dict_module

def _locked(fn):
    # type: (typing.Callable) -> typing.Callable
    """
    Wrap a function so that it cannot be called while that function is running (in another thread).

    Usually used on a :func:`_threaded` function.
    """
    lock = threading.Lock()
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with lock:
            fn(*args, **kwargs)
    return wrapper

def _threaded(fn):
    # type: (typing.Callable) -> typing.Callable
    """
    Wrap a function so that it is spawned in a different thread, and the execution flow
    in the current thread is returned to the callee immediately.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=fn, args=args, kwargs=kwargs)
        t.start()
    return wrapper

def create_dictionary(resource, threaded_save=True):
    # type: (str, bool) -> StenoDictionary
    '''Create a new dictionary.

    The format is inferred from the extension.

    Note: the file is not created! The resulting dictionary
    :meth:`~plover.steno_dictionary.StenoDictionary.save`
    method must be called to finalize the creation on disk.

    Arguments:
        resource: the file name.
        threaded_save: override the resulting dictionary's
            :meth:`~plover.steno_dictionary.StenoDictionary.save` method to
            save the dictionary in a different thread, with a lock.

            Uses :func:`_threaded` and :func:`_locked` internally. See the
            documentation of those functions for more details.
        
    '''
    d = _get_dictionary_class(resource).create(resource)
    if threaded_save:
        d.save = _threaded(_locked(d.save))
    return d

def load_dictionary(resource, threaded_save=True):
    # type: (str, bool) -> StenoDictionary
    '''Load a dictionary from a file.

    The format is inferred from the extension.

    Arguments:
        resource: the file name.
        threaded_save: See the description of the ``threaded_save`` parameter
            of :func:`create_dictionary` function.
    '''
    d = _get_dictionary_class(resource).load(resource)
    if not d.readonly and threaded_save:
        d.save = _threaded(_locked(d.save))
    return d
