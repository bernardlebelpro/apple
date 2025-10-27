from contextlib import contextmanager
import logging
import os
from PySide6 import QtCore, QtUiTools, QtWidgets, QtGui
from typing import Union

from metsearch.contants import DisplayFields, ObjectFields
from metsearch.imagecache import ImageCache
from metsearch.model import ObjectsModel, ObjectsProxyModel


logger = logging.getLogger(__name__)


UI_FILEPATH = os.path.join(os.path.dirname(__file__), "metsearch.ui")
HEIGHT = 800
WIDTH = 1200

class MainWindow(QtCore.QObject):
    """The main application object."""

    def __init__(self, parent: Union[QtWidgets.QWidget, None] = None):
        super().__init__(parent)

        self._images = ImageCache()
        self._model: Union[ObjectsModel, None] = None
        self._proxy_model: Union[ObjectsProxyModel, None] = None
        self._selection_model: Union[QtCore.QItemSelectionModel, None] = None
        self._ui: Union[QtWidgets.QMainWindow, None] = None

        self.setup_ui()
        self.connect_signals()

    # -------------------------------------------------------------------------
    # PROPERTIES
    # -------------------------------------------------------------------------

    @property
    def images(self) -> ImageCache:
        """The cache of images.

        Returns:
            metsearch.imagecache.ImageCache:
        """
        return self._images

    @property
    def model(self) -> ObjectsModel:
        """The model for the list view.

        Returns:
            metsearch.model.ObjectsModel
        """
        return self._model

    @property
    def proxy_model(self) -> ObjectsProxyModel:
        """The proxy model for the list view.

        Returns:
            metsearch.model.ObjectsProxyModel
        """
        return self._proxy_model

    @property
    def selection_model(self) -> QtCore.QItemSelectionModel:
        """The selection model for the list view.

        Returns:
            QtCore.QItemSelectionModel
        """
        return self._selection_model

    @property
    def ui(self) -> QtWidgets.QMainWindow:
        """Get the main window from Loading the UI file.

        Returns:
            QtCore.QMainWindow
        """
        return self._ui

    # -------------------------------------------------------------------------
    # SETUP METHODS
    # -------------------------------------------------------------------------

    def connect_signals(self):
        """Connect signals and slots."""
        self.images.image_updated.connect(self.set_image)

        self.model.cache.requests_finished.connect(
            self.proxy_model.invalidateFilter
        )

        self.model.cache.timer_progress.connect(self.update_countdown)

        self.ui.imageonly_checkbox.stateChanged.connect(
            self.proxy_model.set_image_only
        )

        self.ui.reset_button.clicked.connect(self.reset_clicked)

        self.ui.searchtext_lineedit.editingFinished.connect(
            self.search_text_changed
        )

        self.ui.sortasc_radio.toggled.connect(
            self.sort_changed
        )

        self.ui.sortdesc_radio.toggled.connect(
            self.sort_changed
        )

        self.selection_model.selectionChanged.connect(
            self.selected_row_changed
        )

    def setup_ui(self):
        """Assemble and configure the UI."""
        loader = QtUiTools.QUiLoader()
        self._ui = loader.load(UI_FILEPATH, parentWidget=None)

        # ------
        # Models

        self._proxy_model = ObjectsProxyModel(main_window=self)
        self._model = ObjectsModel(
            proxy_model=self.proxy_model,
            parent=self.ui
        )
        self._proxy_model.setSourceModel(self.model)
        self._selection_model = QtCore.QItemSelectionModel(self.proxy_model)

        # ---------
        # Actual UI

        self.ui.setWindowTitle("MET Search")
        self.ui.setGeometry(
            100,
            100,
            WIDTH,
            HEIGHT
        )  # x, y, width, height

        self.ui.results_view.setSelectionMode(
            self.ui.results_view.SelectionMode.SingleSelection
        )
        self.ui.results_view.setModel(self._proxy_model)
        self.ui.results_view.setSelectionModel(self.selection_model)

        self.set_image()

        form_layout = self.ui.metadata_widget.layout()
        for display_name in DisplayFields.FIELDS:
            form_layout.addRow(
                QtWidgets.QLabel(display_name),
                QtWidgets.QLabel("")
            )

    # -------------------------------------------------------------------------
    # SLOT METHODS
    # -------------------------------------------------------------------------

    @QtCore.Slot()
    def reset_clicked(self):
        """Reset the search widgets to their default state."""
        widgets = (
            self.ui.searchtext_lineedit,
            self.ui.classification_combox,
            self.ui.imageonly_checkbox,
            self.ui.sortasc_radio
        )

        with self.block_signals(*widgets):
            self.ui.searchtext_lineedit.setText("")
            self.ui.classification_combox.clear()
            self.ui.classification_combox.addItem("")
            self.ui.classification_combox.setCurrentIndex(0)
            self.ui.imageonly_checkbox.setChecked(False)
            self.ui.sortasc_radio.setChecked(True)
            self.model.reset()
            self.clear_metadata()

        self.proxy_model.invalidate()

    @QtCore.Slot()
    def search_text_changed(self):
        """Update the UI when the search text has changed."""
        self.clear_metadata()
        text = self.ui.searchtext_lineedit.text()
        self.model.search(search_term=text)

    @QtCore.Slot()
    def selected_row_changed(
            self,
            selected: QtCore.QItemSelection,
            deselected: QtCore.QItemSelection
    ):
        """Update the right-side widgets when an object is selected in the list.

        Args:
            selected (QtCore.QItemSelection): The selected items.
            deselected (QtCore.QItemSelection): The deselected items.
                Since our selection mode is SingleSelect, this will always
                be empty.
        """
        self.set_image()

        indices = selected.indexes()
        if indices:
            proxy_index = indices[0]
            index = self.proxy_model.mapToSource(proxy_index)
            row = index.row()
            object_url = self.model.cache.urls[row]
            document = self.model.cache.get_object(object_url)

            # ---------
            # Thumbnail

            image_url = document.get(ObjectFields.PRIMARY_IMAGE)
            if image_url:
                pixmap = self.images.get_pixmap(image_url)
                self.set_image(pixmap)

            # --------
            # Metadata

            layout = self.ui.metadata_widget.layout()

            for i in range(layout.rowCount()):
                display_name = layout.itemAt(
                    i,
                    layout.ItemRole.LabelRole
                ).widget().text()

                label = layout.itemAt(
                    i,
                    layout.ItemRole.FieldRole
                ).widget()

                key = DisplayFields.FIELDS_TO_OBJECT_FIELDS[display_name]
                value = document.get(key, "")
                label.setText(str(value))
        else:
            self.clear_metadata()

    @QtCore.Slot()
    def sort_changed(self, *args):
        """Update the proxy model after the user has changed the sort order."""
        if self.ui.sortasc_radio.isChecked():
            order = QtCore.Qt.SortOrder.AscendingOrder
        else:
            order = QtCore.Qt.SortOrder.DescendingOrder

        self.model.sort_order = order

    @QtCore.Slot(int)
    def update_countdown(self, seconds: int):
        """Update the countdown label with the new number of seconds.

        Args:
            seconds (int): The number of seconds remaining for the timer.
        """
        self.ui.countdown_label.setText(str(seconds))

    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------

    @contextmanager
    def block_signals(*widgets: QtWidgets.QWidget):
        """Temporarily block all signals from being emitted by a widget.

        Args:
            widgets (list[QtWidgets.Widget]): The widget with the signals to be
                blocked.
        """
        blocked_widgets = []

        try:
            for widget in widgets:
                widget.blockSignals(True)
                blocked_widgets.append(widget)
            yield
        finally:
            widget = None
            try:
                for widget in blocked_widgets:
                    widget.blockSignals(False)
            except Exception as e:
                logger.error(
                    "Failed to unblock signals on widget '%s', error:\n%s",
                    widget,
                    str(e)
                )

    def clear_metadata(self):
        """Clear all metadata values."""
        layout = self.ui.metadata_widget.layout()
        for i in range(layout.rowCount()):
            layout.itemAt(
                i,
                layout.ItemRole.FieldRole
            ).widget().setText("")

    def get_selected_url(self) -> Union[str, None]:
        """Get the selected row's URL.

        Returns:
            str|None: The selected row's URL, or None if no row is selected.
        """
        selection_model = self.ui.results_view.selectionModel()
        selected = selection_model.selectedIndexes()
        if not selected:
            return

        proxy_index = selected[0]
        index = self.proxy_model.mapToSource(proxy_index)
        row = index.row()
        url = self.model.cache.urls[row]
        return url

    def set_image(
            self,
            pixmap: Union[QtGui.QPixmap, None] = None,
            url: Union[str, None] = None
    ):
        """Update the image label with a pixmap.

        Args:
            pixmap (QtGui.QPixmap|None): The pixmap to display. If None,
                the default pixmap is used.
            url (str): An object URL corresponding to the image we
                are setting. If not None, ensure that the the image is
                set only if the object is selected in the list.
                This is to prevents long running image requests from
                randomly updating the image while looking at a different
                document.
        """
        pixmap = pixmap or self.images.default_pixmap

        if url:
            selected_url = self.get_selected_url()
            if selected_url == url:
                pixmap = self.images.get_pixmap(url)

        self.ui.image_label.setPixmap(pixmap)
