import os
from PySide6 import QtCore, QtUiTools, QtWidgets
import sys
from typing import Union

for p in sorted(sys.path):
    print(p)

from .model import ResultsModel, ResultsProxyModel




UI_FILEPATH = os.path.join(os.path.dirname(__file__), "metsearch.ui")
HEIGHT = 900
WIDTH = 600

class MetSearch(QtCore.QObject):
    """The main application object."""

    def __init__(self, parent: Union[QtWidgets.QWidget, None] = None):
        super().__init__(parent)

        self._ui: Union[QtWidgets.QMainWindow, None] = None
        self._model = ResultsModel(parent=self.ui)
        self._proxy_model = ResultsProxyModel(parent=self.ui)
        self._proxy_model.setSourceModel(self._model)
        self._results_view = QtWidgets.QListView(parent=self.ui)
        self._results_view.setModel(self._proxy_model)

        self.setup_ui()
        self.connect_signals()

    # -------------------------------------------------------------------------
    # PROPERTIES
    # -------------------------------------------------------------------------

    @property
    def model(self) -> ResultsModel:
        return self._model

    @property
    def proxy_model(self) -> ResultsProxyModel:
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

        self.ui.searchtext_lineedit.textChanged.connect(
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
    def search_text_changed(self, new_value: str):
        pass

    @QtCore.Slot()
    def sort_changed(self, *args):
        if self.ui.sortasc_radio.isChecked():
            order = QtCore.Qt.SortOrder.AscendingOrder
        else:
            order = QtCore.Qt.SortOrder.DescendingOrder
        print(order)

        self.proxy_model.sort(order)

    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------

    def get_classifications(self):
        pass


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MetSearch()
    window.ui.show()
    app.exec()