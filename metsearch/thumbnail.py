from PySide6 import QtCore, QtGui, QtNetwork, QtWidgets
from typing import Union


class Thumbnails(QtCore.QObject):
    """Thumbnails database."""

    def __init__(self, parent: Union[QtWidgets.QWidget, None] = None) -> None:
        super().__init__(parent)
        self._network_manager = QtNetwork.QNetworkAccessManager(self)

    @property
    def network_manager(self) -> QtNetwork.QNetworkAccessManager:
        return self._network_manager

    def get_thumbnail(self, url: QtCore.QUrl) -> Union[bytes, None]:
        """Get thumbnail from cache or download it."""

        request = QtNetwork.QNetworkRequest(url)
        request.setRawHeader(b"Accept", b"image/webp,image/apng,image/*,*/*;q=0.8")
        request.setRawHeader(b"Accept-Encoding", b"gzip, deflate, br")
        request.setRawHeader(b"Accept-Language", b"en-US,en;q=0.9")