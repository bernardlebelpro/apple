from contextlib import contextmanager
import logging
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt
import traceback
from typing import Any, Union

from metsearch.contants import ObjectFields, Requests
from metsearch.objectcache import ObjectCache


logger = logging.getLogger(__name__)


class ObjectsProxyModel(QtCore.QSortFilterProxyModel):
    """Proxy model that filters the results."""

    def __init__(self, main_window) -> None:
        """Initialize the proxy model.

        Args:
            main_window (metsearch.mainwindow.MainWindow): The app's main
                window.
        """
        super().__init__(main_window.ui)
        self._main_window = main_window
        self._sort_order = QtCore.Qt.SortOrder.AscendingOrder

        self.setSortRole(QtCore.Qt.ItemDataRole.DisplayRole)
        self.setSortCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.setDynamicSortFilter(False)

        self._image_only: bool = False

    # -------------------------------------------------------------------------
    # PROPERTIES
    # -------------------------------------------------------------------------

    @property
    def image_only(self) -> bool:
        """Get the image-only filter state.

        Returns:
            bool
        """
        return self._image_only

    @property
    def main_window(self):
        """The app's main window.

        Returns:
            metsearch.mainwindow.MainWindow
        """
        return self._main_window

    @property
    def sort_order(self) -> QtCore.Qt.SortOrder:
        """Get the current sort order.

        Returns:
            QtCore.Qt.SortOrder:
        """
        return self._sort_order

    @sort_order.setter
    def sort_order(self, value: QtCore.Qt.SortOrder):
        """Update the current sort order.

        NOTE: This causes a sort to occur.

        Args:
            value (QtCore.Qt.SortOrder): The new sort order.
        """
        self._sort_order = value
        self.sort(0, value)

    # -------------------------------------------------------------------------
    # RE-IMPLEMENTED METHODS
    # -------------------------------------------------------------------------

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()):
        return 1

    def filterAcceptsRow(
            self,
            source_row: int,
            source_parent: QtCore.QModelIndex
    ) -> bool:
        # This is called only when the model's row count changes,
        # or when invalidate() and invalidateFilter() are called.
        # This means we can't rely on this method to hide the row
        # when we know if the requested url returns a good object.

        model = self.sourceModel()
        url = model.cache.urls[source_row]

        # This is only moderately reliable,
        # it will be accurate only for urls that that been processed.
        # For fresh new rows, we may not know yet if the url is bad.
        if url in model.cache.bad_urls:
            return False

        document = model.cache.get_object(url)
        if (
                document and
                self.image_only and
                not document[ObjectFields.PRIMARY_IMAGE]
        ):
            return False

        return super().filterAcceptsRow(source_row, source_parent)

    def invalidateFilter(self):
        """Ensure the selected row remains selected after filtering.

        If the initial proxy index is no longer visible after the filtering,
        then nothing is selected.
        """
        index = None
        selection_model = self.main_window.ui.results_view.selectionModel()
        selected = selection_model.selectedIndexes()
        if selected:
            proxy_index = selected[0]
            index = self.mapToSource(proxy_index)

        super().invalidateFilter()
        self.sort(0, self.sort_order)

        if index is not None:
            proxy_index = self.mapFromSource(index)
            if proxy_index.isValid():
                selection_model.setCurrentIndex(
                    proxy_index,
                    selection_model.SelectionFlag.ClearAndSelect
                )

                self.main_window.selected_row_changed(
                    selection_model.selection(),
                    QtCore.QItemSelection()
                )

    def set_image_only(self, value: bool):
        """Record the new state for the image-only filter, update the model.

        Args:
            value (bool): The new image-only filter state.
        """
        self._image_only = value
        self.invalidateFilter()


class ObjectsModel(QtCore.QAbstractItemModel):
    """Model that holds the search result indices and object documents."""

    timer_progress = QtCore.Signal(int)

    def __init__(
            self,
            proxy_model: ObjectsProxyModel,
            parent: Union[QtWidgets.QWidget, None] = None
    ) -> None:
        super().__init__(parent)

        self._cache = ObjectCache(proxy_model)
        self._proxy_model = proxy_model

    # -------------------------------------------------------------------------
    # PROPERTIES
    # -------------------------------------------------------------------------

    @property
    def cache(self) -> ObjectCache:
        """Get the internal object cache.

        Returns:
            metsearch.objectcache.ObjectCache:
        """
        return self._cache

    @property
    def proxy_model(self) -> ObjectsProxyModel:
        """Get the proxy model that uses this model.

        Returns:
            metsearch.model.ObjectsProxyModel:
        """
        return self._proxy_model

    # -------------------------------------------------------------------------
    # SETUP METHODS
    # -------------------------------------------------------------------------

    def connect_signals(self):
        """Connect signals and slots."""
        self.cache.cache_updated.connect(self.cache_updated)
        self.cache.timer_progress.connect(self.update_countdown)

    # -------------------------------------------------------------------------
    # RE-IMPLEMENTED METHODS
    # -------------------------------------------------------------------------

    def canFetchMore(
            self,
            parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> bool:
        if parent.isValid():
            return False
        return self.cache.last_index+1 < len(self.cache.urls)

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
        url = self.cache.urls[row]

        if role == Qt.ItemDataRole.DisplayRole:
            document = self.cache.get_object(url)
            if ObjectFields.TITLE in document:
                return document[ObjectFields.TITLE]

    def fetchMore(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()):
        if parent.isValid():
            return

        first = self.cache.last_index + 1
        if first == len(self.cache.urls):
            return

        remaining = len(self.cache.urls) - first
        if remaining > Requests.MAX_RESULTS:
            last = first + Requests.MAX_RESULTS
        else:
            last = first + remaining
        count = last - first
        urls = self.cache.urls[first:last]

        logger.debug("Begin inserting rows %s-%s (%s items)...",
            first,
            last-1,
            count
        )
        self.cache.last_index += len(urls)
        self.beginInsertRows(parent, first, last-1)

        self.cache.extend_queue(urls)
        self.cache.last_index += len(urls)

        logger.debug("Finishing inserting rows...")
        # CRASHING... :[
        self.endInsertRows()
        logger.debug("Finished inserting rows.")

    def index(
            self,
            row: int,
            column: int,
            parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        url = self.cache.urls[row]
        return self.createIndex(row, column, url)

    def parent(
            self,
            child: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> QtCore.QModelIndex:
        return QtCore.QModelIndex()

    def rowCount(
            self,
            parent: QtCore.QModelIndex = QtCore.QModelIndex()
    ) -> int:
        if parent.isValid():
            return 0
        return self.cache.last_index + 1

    # -------------------------------------------------------------------------
    # SLOT METHODS
    # -------------------------------------------------------------------------

    @QtCore.Slot(str)
    def cache_updated(self, url: str):
        """Called when the document cache has changed, relay that to the views.

        Args:
            url (str): The object URL that has been updated in the cache.
        """
        index = self.index(row=self.cache.urls.index(url), column=0)
        self.dataChanged.emit(index, index)

    @QtCore.Slot(int)
    def update_countdown(self, seconds: int):
        """Re-emits the timer progress signal.

        This causes the countdown in the main window to be updated.

        Args:
            seconds (int): The number of seconds elapsed since the
                timer started.
        """
        self.timer_progress.emit(seconds)

    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------

    @contextmanager
    def reset(self):
        """Reset this model so that a new search can be performed."""
        self.beginResetModel()
        try:
            self.cache.reset()
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

            self.cache.populate(search_term)
            self.proxy_model.sort(0, self.proxy_model.sort_order)
