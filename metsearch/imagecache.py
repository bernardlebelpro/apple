import logging
from PySide6 import QtCore, QtGui
import requests
from typing import Dict

from metsearch.classproperty import classproperty


logger = logging.getLogger(__name__)


class ImageCache:
    """Thumbnail database."""

    _default_pixmap = None

    def __init__(self):
        self._images: Dict[str, QtGui.QPixmap] = {}

    # -------------------------------------------------------------------------
    # PROPERTIES
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------

    def get_pixmap(self, url: str):
        """Get a pixmap for an image URL.

        Args:
            url (str): The image URL.

        Returns:
            QtGui.QPixmap: A pixmap. If the object has an image URL,
            and that the image is good to use, return a pixmap with the image.
            Otherwise, return the default pixmap.
        """
        if url not in self._images:
            response = requests.get(url)

            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                logger.error("Couldn't get image at url %s.,", str(e))
                self.images[url] = self.default_pixmap

            else:
                pixmap = QtGui.QPixmap()
                pixmap.loadFromData(response.content)
                pixmap = pixmap.scaled(
                    256,
                    256,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation
                )
                self.images[url] = pixmap

        return self.images[url]
