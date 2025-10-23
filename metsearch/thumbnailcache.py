from PySide6 import QtCore


class ObjectsCache(QtCore.QObject):
    def __init__(self):
        super().__init__()

        # Emitted after the cache has been updated.
        cache_updated = QtCore.Signal(str)