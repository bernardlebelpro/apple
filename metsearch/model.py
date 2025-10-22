from contextlib import contextmanager
import logging
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
import requests
import traceback
from typing import Any, Dict, List, Union

from metsearch.contants import MAX_RESULTS, Endpoints, ObjectFields


logger = logging.getLogger(__name__)


class ObjectsProxyModel(QtCore.QSortFilterProxyModel):
    """Proxy model that filters the results."""

    def __init__(self, parent: Union[QtWidgets.QWidget, None] = None) -> None:
        super().__init__(parent)
        self.setSortRole(QtCore.Qt.ItemDataRole.DisplayRole)
        self.setSortCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.setDynamicSortFilter(True)

    def filterAcceptsRow(
            self,
            source_row: int,
            source_parent: QtCore.QModelIndex
    ) -> bool:
        model = self.sourceModel()
        object_id = model.object_ids[source_row]
        if object_id in model.bad_object_ids:
            return False
        if not object_id in model.objects:
            return False
        return True


class ObjectsModel(QtCore.QAbstractItemModel):
    """Model that holds the search result indices and object documents."""

    def __init__(
            self,
            proxy_model: ObjectsProxyModel,
            parent: Union[QtWidgets.QWidget, None] = None
    ) -> None:
        super().__init__(parent)

        self._bad_object_ids: List[int] = []
        self._last_index: int = -1
        self._object_ids: List[int] = []
        self._objects: Dict[int, Dict] = {}
        self._proxy_model = proxy_model
        self._sort_order = QtCore.Qt.SortOrder.AscendingOrder

    # -------------------------------------------------------------------------
    # PROPERTIES
    # -------------------------------------------------------------------------

    @property
    def bad_object_ids(self) -> List[int]:
        """Get the list of object IDs that failed to fetch.

        Returns:
            list[int]
        """
        return self._bad_object_ids

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
    def object_ids(self) -> List[int]:
        """All the object IDs we fetched by the last search.

        Returns:
            list[int]
        """
        return self._object_ids

    @object_ids.setter
    def object_ids(self, value: List[int]):
        self._object_ids = value

    @property
    def objects(self) -> Dict[int, Dict]:
        """The internal repository of all fetched object documents.

        Returns:
            dict[int, dict]: The object payload mapped to its ID.
        """
        return self._objects

    @property
    def proxy_model(self) -> ObjectsProxyModel:
        return self._proxy_model

    @property
    def sort_order(self) -> QtCore.Qt.SortOrder:
        return self._sort_order

    @sort_order.setter
    def sort_order(self, value: QtCore.Qt.SortOrder):
        self._sort_order = value
        self.proxy_model.sort(0, value)

    # -------------------------------------------------------------------------
    # RE-IMPLEMENTED METHODS
    # -------------------------------------------------------------------------

    def canFetchMore(self, parent: QtCore.QModelIndex) -> bool:
        """Check if there are more object documents to fetch.

        Args:
            parent (QtCore.QModelIndex): a parent with items to fetch
                underneath.

        Returns:
            bool
        """
        return self._last_index+1 < (
                len(self.object_ids) - len(self.bad_object_ids)
        )

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()):
        return 1

    def data(
            self,
            index: QtCore.QModelIndex,
            role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if not index.isValid():
            return

        row = index.row()
        object_id = self.object_ids[row]
        document = self.objects[object_id]

        if role == Qt.ItemDataRole.DisplayRole:
            return document[ObjectFields.TITLE]

    def fetchMore(self, parent: QtCore.QModelIndex):
        """Fetch the next page of object documents.

        Args:
            parent (QtCore.QModelIndex): the parent with child models to
                fetch.
        """
        objects = self.get_objects()

        self.beginInsertRows(
            parent,
            self._last_index+1,
            self._last_index + len(objects)
        )

        self.objects.update(objects)
        self.last_index += len(objects)

        self.endInsertRows()
        self.proxy_model.sort(0, self.sort_order)

    def index(
            self,
            row: int,
            column: int,
            parent: Union[QtCore.QModelIndex, None] = None
    ) -> QtCore.QModelIndex:
        if row < len(self.object_ids):
            object_id = self.object_ids[row]
            if object_id in self.objects:
                return self.createIndex(row, column, self.objects[object_id])
        return QtCore.QModelIndex()

    def parent(self) -> QtCore.QModelIndex:
        return QtCore.QModelIndex()

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()):
        return len(self._object_ids)

    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------

    def get_objects(self) -> Dict[int, Dict]:
        """Get the object documents for the given indices."""
        if len(self._object_ids) <= MAX_RESULTS:
            object_ids = self.object_ids[:]
        else:
            object_ids = self.object_ids[
                self.last_index+1 :
                self.last_index+1 + MAX_RESULTS
            ]

        objects = {}

        for i, object_id in enumerate(object_ids):
            url = f"{Endpoints.BASE}{Endpoints.OBJECTS}/{object_id}"
            response = requests.get(url)

            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                # Sometimes we get a 403 (forbidden) for no obvious reason,
                # just skip those.
                logger.info(
                    "Failed to get object for ID %s with error '%s'",
                    object_id,
                    response.content.decode().strip()
                )

                self.bad_object_ids.append(object_id)
                continue

            objects[object_id] = response.json()

        return objects

    @contextmanager
    def reset(self):
        """Reset this model so that a new search can be performed."""
        self.beginResetModel()
        try:
            self._object_ids = []
            self._last_index = -1
            yield
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(str(e))
        finally:
            self.endResetModel()

    def search(self, search_term: Union[str, None] = None):
        """Perform a new search against the MET service.

        Args:
            search_term (str|None): A search string (e.g. "apple", "cat", etc).
                If None or empty, no search is performed and the model
                is reset.
        """
        with self.reset():
            if not search_term:
                return

            url = f"{Endpoints.BASE}{Endpoints.SEARCH}"
            params = {"q": search_term}

            response = requests.get(url, params=params)
            response.raise_for_status()

            self.object_ids = response.json()["objectIDs"]
            logger.info("Object ID count: %s", len(self.object_ids))

            objects = self.get_objects()
            self.objects.update(objects)
            self.last_index += len(objects)
            self.proxy_model.sort(0, self.sort_order)
