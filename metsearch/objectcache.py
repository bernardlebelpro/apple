import logging
import json
from PySide6 import QtCore, QtGui, QtNetwork, QtWidgets
import requests
from typing import Dict, List, Tuple, Union

from metsearch.contants import Endpoints, Requests
from metsearch.timer import Timer


logger = logging.getLogger(__name__)


class ObjectsCache(QtCore.QObject):
    """Object documents database.

    Handles the fetching and caching of documents in an async way.
    """

    # Emitted after the cache has been updated.
    cache_updated = QtCore.Signal(str)

    timer_progress = QtCore.Signal(int)

    def __init__(self, proxy_model):
        super().__init__()

        self._bad_urls: List[str] = []
        self._counter: int = 0
        self._last_index: int = -1
        self._network_manager = QtNetwork.QNetworkAccessManager(self)
        self._urls: List[str] = []
        self._objects: Dict[str, Dict] = {}
        self._processed_urls: List[str] = []
        self._proxy_model = proxy_model
        self._queue: List[str] = []
        self._requested_urls: List[str] = []

        self._timer = Timer(parent=self)
        self._timer.timeout.connect(self.timer_timeout)

    # -------------------------------------------------------------------------
    # PROPERTIES
    # -------------------------------------------------------------------------

    @property
    def bad_urls(self) -> List[str]:
        """Get the list of object IDs that failed to fetch.

        Returns:
            list[int]
        """
        return self._bad_urls

    @property
    def counter(self) -> int:
        return self._counter

    @counter.setter
    def counter(self, value: int):
        self._counter = value

    @property
    def last_index(self) -> int:
        """Get the index of the last object ID we fetched.

        Keep track of where we are in the list of object IDs by
        recording the index of the last object we fetched.
        To be clear, this is the index of an element in the list,
        NOT an actual object ID from the MET service.

        Returns:
            int
        """
        return self._last_index

    @last_index.setter
    def last_index(self, value: int):
        self._last_index = value

    @property
    def network_manager(self) -> QtNetwork.QNetworkAccessManager:
        return self._network_manager

    @property
    def objects(self) -> Dict[str, Dict]:
        """All the object documents we fetched by the last search."""
        return self._objects

    @property
    def processed_urls(self) -> List[str]:
        return self._processed_urls

    @property
    def proxy_model(self):
        return self._proxy_model

    @property
    def queue(self) -> List[str]:
        return self._queue

    @property
    def requested_urls(self) -> List[str]:
        return self._requested_urls

    @property
    def timer(self) -> QtCore.QTimer:
        return self._timer

    @property
    def urls(self) -> List[str]:
        """All the object IDs we fetched by the last search.

        Returns:
            list[int]
        """
        return self._urls

    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------

    def cache_object(self, reply: QtNetwork.QNetworkReply):
        """Cache the object document."""
        url = reply.url().toString()
        self.processed_urls.append(url)

        byte_array = reply.readAll()
        reply.deleteLater()

        errors = (
            reply.NetworkError.ContentNotFoundError,
            reply.NetworkError.ContentAccessDenied
        )
        error = reply.error()

        if error == reply.NetworkError.NoError:
            if byte_array:
                logger.debug("Getting URL: Success [%s]", url)
                document = json.loads(str(byte_array.data(), "utf-8"))
                self.objects[url] = document
                self.cache_updated.emit(url)
            else:
                # It's highly unlikely that we'll get an empty document
                # while not running into an error, but we're handling
                # it anyway to cover our bases.
                logger.debug("Getting URL: FAILURE [%s]", url)
                self.bad_urls.append(url)
                self.cache_updated.emit(url)
        elif error in errors or not byte_array:
            logger.debug("Getting URL: FAILURE [%s] %s", url, error)
            self.bad_urls.append(url)
            self.cache_updated.emit(url)
        else:
            logger.debug(
                "Getting URL: FAILURE [%s] %s: %s",
                url,
                error,
                str(byte_array.data(), "utf-8")
            )
            self.bad_urls.append(url)
            self.cache_updated.emit(url)

    def execute_request(self, url: str):
        request = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
        request.setRawHeader(b"Content-Type", b"application/json")
        request.setRawHeader(b"Accept", b"application/json")

        reply = self.network_manager.get(request)
        reply.finished.connect(
            lambda: self.cache_object(reply)
        )

    def get_object(self, url: str) -> Dict:
        """Get the object document from the cache or download it."""

        if url in self._requested_urls:
            return self.objects[url]

        self._requested_urls.append(url)
        self.execute_request(url)

        return {}

        # request = QtNetwork.QNetworkRequest(url)
        # request.setRawHeader(b"Accept", b"image/webp,image/apng,image/*,*/*;q=0.8")
        # request.setRawHeader(b"Accept-Encoding", b"gzip, deflate, br")
        # request.setRawHeader(b"Accept-Language", b"en-US,en;q=0.9")

    def populate(self, search_term: Union[str, None] = None):
        # Get all the object IDs for the search term.

        url = f"{Endpoints.BASE}{Endpoints.SEARCH}"
        params = {"q": search_term}

        response = requests.get(url, params=params)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(str(e))
            return

        object_ids = response.json()["objectIDs"]
        if not object_ids:
            logger.info("No results found for search term '%s'.", search_term)
            return

        for object_id in object_ids:
            url = f"{Endpoints.BASE}{Endpoints.OBJECTS}/{object_id}"
            self.urls.append(url)
            self.objects[url] = {}

        logger.info("Total object count: %s", len(self.urls))

        # Get the first 80 objects.

        urls = self.urls[:Requests.MAX_RESULTS]
        self.queue.extend(urls)
        self.last_index += len(urls)
        self.process_queue()

    def process_queue(self):
        logger.debug(
            "Processing queue, currently has %s items...",
            len(self.queue)
        )

        self.counter = 0
        while self.counter < Requests.MAX_RESULTS and self.queue:
            url = self.queue.pop(0)
            self.get_object(url)
            self.counter += 1

        logger.debug(
            "Finished processing queue, has %s items left.",
            len(self.queue)
        )

        self.proxy_model.invalidate()

        self.timer.start()
        logger.debug(
            "Waiting %s seconds for next cycle of requests...",
            Requests.SECONDS
        )

    def reset(self):
        self._urls = []
        self.last_index = -1

    def timer_timeout(self, *args):
        if self.timer.count == Requests.SECONDS:
            self.timer.stop()
            self.process_queue()
        else:
            self.timer.count += 1

        self.timer_progress.emit(Requests.SECONDS - self.timer.count)
