from PySide6 import QtCore

from metsearch.contants import Requests


class Timer(QtCore.QTimer):
    progress = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._count = 0
        self.setInterval(Requests.INTERVAL)

    @property
    def count(self) -> int:
        return self._count

    @count.setter
    def count(self, value: int):
        self._count = value

    def start(self):
        self._count = 0
        super().start()

    def stop(self):
        self._count = 0
        super().stop()
