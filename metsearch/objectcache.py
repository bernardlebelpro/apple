import logging
import json
from PySide6 import QtCore, QtNetwork
import requests
from typing import Dict, List, Union

from metsearch.contants import Endpoints, Requests
from metsearch.timer import Timer


logger = logging.getLogger(__name__)


class Request:
    def __init__(self, key: int, url: str):
        self._key = key
        self._url = url

    @property
    def key(self) -> int:
        return self._key

    @property
    def url(self) -> str:
        return self._url


class ObjectCache(QtCore.QObject):
    """Object documents database.

    Handles the fetching and caching of documents in an async way.
    """

    # Emitted after the cache has been updated.
    # An update happens after every request that returns.
    # This allows updating the model iteratively, in a non-blocking way.
    cache_updated = QtCore.Signal(str)

    # Emitted when a "batch" of requests have completed.
    # Since requests run asynchronously, it's a way of know when they
    # all have finished.
    # This allows invalidating the proxy model's filter,
    # so that rows can be resorted and hidden if there are documents.
    # Without it, the rows for which there is no document remain visible
    # until the next time the queue is processed, which is usually
    # every minute, IF there are new requests.
    requests_finished = QtCore.Signal()

    # Emitted every second.
    timer_progress = QtCore.Signal(int)

    def __init__(self, proxy_model):
        """Initialize the object cache.

        Args:
            proxy_model (ObjectsProxyModel): The proxy model of the list view.
        """
        super().__init__()

        self._bad_urls: List[str] = []
        self._last_index: int = -1
        self._network_manager = QtNetwork.QNetworkAccessManager(self)
        self._urls: List[str] = []
        self._objects: Dict[str, Dict] = {}
        self._proxy_model = proxy_model
        self._queue: List[List[Request]] = []
        self._requested_urls: List[str] = []

        self._processed_requests: Dict[int, Dict] = {
            0: {
                "count": 0,
                "total": 0
            }
        }

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
    def processed_requests(self) -> Dict[int, Dict]:
        """The internal map of process requests.

        Returns:
            dict[int, dict]: Keys are ints (an identifier for a batch of
            requests. Values are a dict with "count" and "total" keys.
            "count" represents the number of requests that have been processed
            for the key. "total" represents the total number of requests
            for the key.

            Ex:
                {
                    3: {
                        "count": 3,
                        "total": 10
                    }
                }
        """
        return self._processed_requests

    @property
    def proxy_model(self):
        return self._proxy_model

    @property
    def queue(self) -> List[List[Request]]:
        return self._queue

    @property
    def requested_urls(self) -> List[str]:
        """Get the list of object URLs that have been requested.

        Note that this list does not automatically mean that the objects
        have had their documents cached, it *literally* just mean that the
        we the URLs have been requested.

        Returns:
            list[str]
        """
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

    def extend_queue(self, urls: List[str]):
        """Extend the queue with a list of object URLs to request.

        Args:
            urls (list[str]): A list of object URLs to request.
        """
        key = max(self.processed_requests) + 1
        self.processed_requests[key] = {
            "count": 0,
            "total": len(urls)
        }

        self.requested_urls.extend(urls)
        requests = [Request(key=key, url=url) for url in urls]
        self.queue.append(requests)

    def cache_object(
            self,
            reply: QtNetwork.QNetworkReply,
            key: Union[int, None] = None
    ):
        """Cache the object document.

        Args:
            reply (QtNetwork.QNetworkReply): The reply from the network request.
            key (int|None): A key for the request in the processed_requests
                dict. If not None, will increment the count of process requests
                by one for this key.
        """
        url = reply.url().toString()

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
                self._objects[url] = document
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

        if key is None:
            return

        requests = self.processed_requests[key]
        requests["count"] += 1
        if requests["count"] == requests["total"]:
            self.requests_finished.emit()

    def execute_request(self, url: str, key: Union[int, None] = None):
        """Initiate a network request for an object URL.

        Args:
            url (str): The requested object's URL.
            key (int|None): A key for the request in the processed_requests
                dict. If not None, will increment the count of process requests
                by one for this key when the request completes.
        """
        request = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
        request.setRawHeader(b"Content-Type", b"application/json")
        request.setRawHeader(b"Accept", b"application/json")
        request.setRawHeader(b"Accept-Language", b"en-US,en;q=0.9")

        reply = self.network_manager.get(request)
        reply.finished.connect(
            lambda: self.cache_object(reply, key=key)
        )

    def get_object(self, url: str) -> Dict:
        """Get the object document for the given URL.

        Returns:
            dict: Object document if there is one, otherwise an empty dict.
            There may not be a document if either the request for the URL
            hasn't been processed yet, or if the service didn't return one.
        """
        return self._objects.get(url, {})

    def populate(self, search_term: Union[str, None] = None):
        """Populate cache with the initial search results.

        After getting the initial search results, launches a queue that is
        evaluated every minute for new requested objects.

        Args:
            search_term (str|None): A search string (e.g. "apple", "cat", etc).
        """

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
            self._objects[url] = {}

        logger.info("Total object count: %s", len(self.urls))

        # Get the first 80 objects.

        urls = self.urls[:Requests.MAX_RESULTS]
        self.extend_queue(urls)
        self.last_index += len(urls)
        self.process_queue()

    def process_queue(self):
        """Process the queue of requests.

        Calling this method starts an infinite loop of sorts.
        This is what we want.
        """
        logger.debug(
            "Processing queue, currently has a total of %s items...",
            sum(len(requests) for requests in self.queue)
        )

        if self.queue:
            requests = self.queue.pop(0)
            logger.debug("Processing %s requests...", len(requests))
            for request in requests:
                self.execute_request(url=request.url, key=request.key)

        logger.debug("Finished processing queue.")

        self.timer.start()
        logger.debug(
            "Waiting %s seconds for next cycle of requests...",
            Requests.SECONDS
        )

    def reset(self):
        """Reset the cache in its initial state.

        Well, not entirely. It only resets the attributes relevant to the
        the current search.
        """
        self._urls = []
        self.last_index = -1

    @QtCore.Slot()
    def timer_timeout(self):
        """Evaluate the state of the timer at every second."""
        if self.timer.count == Requests.SECONDS:
            self.timer.stop()
            self.process_queue()
        else:
            self.timer.count += 1

        self.timer_progress.emit(Requests.SECONDS - self.timer.count)
