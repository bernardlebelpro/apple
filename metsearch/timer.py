from PySide6 import QtCore

from metsearch.contants import Requests


class Timer(QtCore.QTimer):
    """Basic timer that emits a progress signal every second.

    Also keeps track of how long (in seconds) it has been running.
    """

    progress = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._count = 0
        self.setInterval(Requests.INTERVAL)

    # -------------------------------------------------------------------------
    # PROPERTIES
    # -------------------------------------------------------------------------

    @property
    def count(self) -> int:
        """Get the number of seconds the timer has been running.

        Returns:
            int
        """
        return self._count

    @count.setter
    def count(self, value: int):
        self._count = value

    # -------------------------------------------------------------------------
    # RE-IMPLEMENTED METHODS
    # -------------------------------------------------------------------------

    def start(self):
        """Start the timer."""
        self._count = 0
        super().start()

    def stop(self):
        """Stop the timer."""
        self._count = 0
        super().stop()
