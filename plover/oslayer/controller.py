"""
This module provides a method to communicate with the Plover process.

It's used to ensure that there's only one instance of Plover running,
and to send commands to the existing Plover instance.
"""

from multiprocessing import connection
from threading import Thread
import errno
import os
import tempfile
import typing

from plover import log
from plover.oslayer.config import PLATFORM


class Controller:
    """
    The controller object.

    Uses ``multiprocessing.connection`` internally.

    To use this object:

    * Create a :class:`Controller` instance.
    * Call :meth:`__enter__` (usually with a ``with`` statement)
    * Check for the value of the :attr:`is_owner` attribute.
    * If it's ``False``, there's an existing process listening, or that process exited
      abnormally. :meth:`force_cleanup` can be called in the latter case.
    * If it's ``True``, call :meth:`start`.
    
    See the source code of ``plover.scripts.main`` for an example.

    There can be at most one message sent for each connection.

    Parameters:
        instance: Any identification string. It's used as a part of the connection address.
        authkey: Authentication key for ``multiprocessing.connection``.
    """

    def __init__(self, instance='plover', authkey=b'plover'):
        # type: (str, bytes) -> None
        if PLATFORM == 'win':
            self._address = r'\\.\pipe' + '\\' + instance
            self._family = 'AF_PIPE'
        else:
            self._address = os.path.join(tempfile.gettempdir(), instance + '_socket')
            self._family = 'AF_UNIX'
        self._authkey = authkey
        self._listen = None
        self._thread = None
        self._message_cb = None

    @property
    def is_owner(self):
        # type: () -> bool
        """
        Return a ``bool`` value.

        (**TODO** why Sphinx doesn't recognize return type in type comment?)
        """
        return self._listen is not None

    def force_cleanup(self):
        # type: () -> bool
        """
        Return:
            whether the cleanup is successful.
        """
        assert not self.is_owner
        if PLATFORM != 'win' and os.path.exists(self._address):
            os.unlink(self._address)
            return True
        return False

    def __enter__(self):
        # type: () -> Controller
        """
        Initialize the object.

        Return:
            this controller object.
        """
        assert self._listen is None
        try:
            self._listen = connection.Listener(self._address, self._family,
                                               authkey=self._authkey)
        except Exception as e:
            if PLATFORM == 'win':
                if not isinstance(e, PermissionError):
                    raise
            else:
                if not isinstance(e, OSError) or e.errno != errno.EADDRINUSE:
                    raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        """
        if self.is_owner:
            self._listen.close()

    def _accept(self):
        # type: () -> bool
        """
        Internal method.

        Run inside the :meth:`_run` loop, to accept one connection.

        Return:
            Whether the listener thread should stop.
        """
        conn = self._listen.accept()
        try:
            msg = conn.recv()
            if msg is None:
                return True
            self._message_cb(msg)
        finally:
            conn.close()
        return False

    def _run(self):
        # type: () -> None
        """
        Internal method.

        Run in a separate thread to listen for incoming connections.
        """
        while True:
            try:
                if self._accept():
                    break
            except Exception as e:
                log.error('handling client failed', exc_info=True)

    def _send_message(self, msg):
        # type: (typing.Any) -> None
        """
        Internal method. Send a message to the listener.

        Parameters:
            msg: The message. Can be any object.

                If the value is ``None``, the listener thread is stopped.
        """
        conn = connection.Client(self._address, self._family, authkey=self._authkey)
        try:
            conn.send(msg)
        finally:
            conn.close()

    def send_command(self, command):
        # type: (str) -> None
        """
        Send a command to the existing Plover instance.

        The message format is ``('command', <command>)``.
        """
        self._send_message(('command', command))

    def start(self, message_cb):
        # type: (str) -> None
        """
        Start listening on the given address.

        Can only be called after :meth:`__enter__` is called.

        There can be at most one process listen at a time. If there's already
        another process listens on the same address, the function will return
        silently and :attr:`is_owner` is ``False``.

        Parameters:
            message_cb: A callable that will be called with any incoming message.

                It should take exactly one argument, the message. (unless the sent
                message is ``None``, in which case the listener thread stops)

                See :meth:`send_command` for the message format.
        """
        assert self.is_owner
        if self._thread is not None:
            return
        self._message_cb = message_cb
        self._thread = Thread(target=self._run)
        self._thread.start()

    def stop(self):
        """
        Stop listening. See :meth:`start`.
        """
        assert self.is_owner
        if self._thread is None:
            return
        self._send_message(None)
        self._thread.join()
        self._thread = None
