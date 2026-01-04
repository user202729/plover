class Capture:
    """Keyboard capture interface."""

    # Callbacks for keyboard press/release events.
    def key_down(key):
        return None

    def key_up(key):
        return None

    # Callbacks for keyboard ready/error events.
    # These 2 functions will only be called strictly after start() finishes if the status needs to be changed.
    on_ready = lambda: None
    on_error = lambda: None

    def start(self):
        """
        Start capturing key events.

        Return a bool: whether it finds a keyboard. Will start "capturing" nevertheless.
        If initially there's no keyboard, on_ready() will be called when it finds one.

        As mentioned before, on_ready() or on_error() will not be called before this function returns.
        """
        raise NotImplementedError()

    def cancel(self):
        """Stop capturing key events."""
        raise NotImplementedError()

    def suppress(self, suppressed_keys=()):
        """Setup suppression."""
        raise NotImplementedError()
