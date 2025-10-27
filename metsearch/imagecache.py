import logging
from PySide6 import QtCore, QtGui, QtNetwork
from typing import Dict, List

from metsearch.classproperty import classproperty


logger = logging.getLogger(__name__)


WIDTH = 512
HEIGHT = 512


class ImageCache(QtCore.QObject):
    """Thumbnail database."""

    # Emitted after the cache has been updated.
    # An update happens after every request that returns.
    # This allows blocker the UI for images that take time to download..
    image_updated = QtCore.Signal(QtGui.QPixmap, str)

    _default_pixmap = None

    def __init__(self):
        super().__init__()

        self._bad_urls = []
        self._images: Dict[str, QtGui.QPixmap] = {}
        self._network_manager = QtNetwork.QNetworkAccessManager(self)
        self._requested_images = []

    # -------------------------------------------------------------------------
    # PROPERTIES
    # -------------------------------------------------------------------------

    @property
    def bad_urls(self) -> List[str]:
        """Get the list of images that failed to fetch."""
        return self._bad_urls

    @classproperty
    def default_pixmap(cls) -> QtGui.QPixmap:
        """Define a default pixmap.

        Note that reading this property before the main window has been
        initialized will cause an error.

        Returns:
            QtGui.QPixmap
        """
        if cls._default_pixmap is None:
            cls._default_pixmap = QtGui.QPixmap(QtCore.QSize(48, 48))
            cls._default_pixmap.fill(QtGui.QColorConstants.Transparent)
        return cls._default_pixmap

    @property
    def images(self) -> Dict[str, QtGui.QPixmap]:
        """The internal database of images.

        Returns:
            dict[str, QtGui.QPixmap]: Pixmap mapped to its image URL.
        """
        return self._images

    @property
    def network_manager(self) -> QtNetwork.QNetworkAccessManager:
        return self._network_manager

    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------

    def cache_pixmap(
            self,
            reply: QtNetwork.QNetworkReply,
            default_pixmap: QtGui.QPixmap
    ):
        """Cache the image data.

        Args:
            reply (QtNetwork.QNetworkReply): The reply from the network request.
            default_pixmap (QtGui.QPixmap): The default pixmap to use if the
                service doesn't return an image.
        """
        url = reply.url().toString()
        byte_array = reply.readAll()
        reply.deleteLater()

        errors = (
            reply.NetworkError.ContentNotFoundError,
            reply.NetworkError.ContentAccessDenied,
            reply.NetworkError.UnknownContentError
        )
        error = reply.error()

        if error == reply.NetworkError.NoError:
            if byte_array:
                logger.debug("Getting URL: Success [%s]", url)
                pixmap = QtGui.QPixmap()
                pixmap.loadFromData(byte_array)
                pixmap = pixmap.scaled(
                    WIDTH,
                    HEIGHT,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation
                )
                self._images[url] = pixmap
                self.image_updated.emit(pixmap, url)
            else:
                # It's highly unlikely that we'll get an empty document
                # while not running into an error, but we're handling
                # it anyway to cover our bases.
                logger.debug("Getting URL: FAILURE [%s]", url)
                self.handle_failure(url, default_pixmap)
        elif error in errors or not byte_array:
            logger.debug("Getting URL: FAILURE [%s] %s", url, error)
            self.handle_failure(url, default_pixmap)
        else:
            logger.debug(
                "Getting URL: FAILURE [%s] %s: %s",
                url,
                error,
                str(byte_array.data(), "utf-8")
            )
            self.handle_failure(url, default_pixmap)

    def get_pixmap(self, url: str):
        """Get a pixmap for an image URL.

        Args:
            url (str): The image URL.

        Returns:
            QtGui.QPixmap: A pixmap. If the object has an image URL,
            and that the image is good to use, return a pixmap with the image.
            Otherwise, return the default pixmap.
        """
        if url in self._requested_images:
            return self._images.get(url, self.default_pixmap)
        else:
            self._requested_images.append(url)

            request = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
            reply = self.network_manager.get(request)
            reply.finished.connect(
                lambda: self.cache_pixmap(reply, self.default_pixmap)
            )

            return self.default_pixmap

    def handle_failure(self, url: str, default_pixmap: QtGui.QPixmap):
        """Handle a failed request.

        Args:
            url (str): The URL that failed.
            default_pixmap (QtGui.QPixmap): A pixmap to use in place of the
                one we didn't get from the request.
        """
        self.bad_urls.append(url)
        self._images[url] = default_pixmap
