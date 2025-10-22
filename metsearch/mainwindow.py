from contextlib import contextmanager
import logging
import os
from PySide6 import QtCore, QtUiTools, QtWidgets
import sys
from typing import Union

from metsearch.model import ObjectsModel, ObjectsProxyModel


logger = logging.getLogger(__name__)


UI_FILEPATH = os.path.join(os.path.dirname(__file__), "metsearch.ui")
HEIGHT = 600
WIDTH = 600

class MetSearch(QtCore.QObject):
    """The main application object."""

    def __init__(self, parent: Union[QtWidgets.QWidget, None] = None):
        super().__init__(parent)

        self._ui: Union[QtWidgets.QMainWindow, None] = None
        self._proxy_model = ObjectsProxyModel(parent=self.ui)
        self._model = ObjectsModel(
            proxy_model=self._proxy_model,
            parent=self.ui
        )
        self._proxy_model.setSourceModel(self._model)

        self.setup_ui()
        self.connect_signals()

        self._ui.results_view.setModel(self._proxy_model)

    # -------------------------------------------------------------------------
    # PROPERTIES
    # -------------------------------------------------------------------------

    @property
    def model(self) -> ObjectsModel:
        return self._model

    @property
    def proxy_model(self) -> ObjectsProxyModel:
        return self._proxy_model

    @property
    def ui(self) -> QtWidgets.QMainWindow:
        """Get the main window from Loading the UI file.

        Returns:
            QtCore.QMainWindow: The main window.
        """
        return self._ui

    # -------------------------------------------------------------------------
    # SETUP METHODS
    # -------------------------------------------------------------------------

    def connect_signals(self):
        self.ui.classification_combox.currentTextChanged.connect(
            self.classification_changed
        )

        self.ui.imageonly_checkbox.stateChanged.connect(
            self.image_only_changed
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

    def setup_ui(self):
        loader = QtUiTools.QUiLoader()
        self._ui = loader.load(UI_FILEPATH, parentWidget=None)

        self.ui.setWindowTitle("MET Search")
        self.ui.setGeometry(
            100,
            100,
            WIDTH,
            HEIGHT
        )  # x, y, width, height

    # -------------------------------------------------------------------------
    # SLOT METHODS
    # -------------------------------------------------------------------------

    @QtCore.Slot()
    def classification_changed(self, new_value: str):
        pass

    @QtCore.Slot()
    def image_only_changed(self, new_value: bool):
        pass

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

    @QtCore.Slot()
    def search_text_changed(self):
        """Update the model after the user has edited the search text."""
        new_value = self.ui.searchtext_lineedit.text()
        self.model.search(new_value)

    @QtCore.Slot()
    def sort_changed(self, *args):
        """Update the proxy model after the user has changed the sort order."""
        if self.ui.sortasc_radio.isChecked():
            order = QtCore.Qt.SortOrder.AscendingOrder
        else:
            order = QtCore.Qt.SortOrder.DescendingOrder

        self.model.sort_order = order

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

    def get_classifications(self):
        pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    app = QtWidgets.QApplication(sys.argv)
    window = MetSearch()
    window.ui.show()
    app.exec()