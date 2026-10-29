"""Hauptfenster: Serien öffnen, 2D- und 3D-Ansicht, Strukturen, Infofeld, Export.

Das Hauptfenster stellt den Modulen die Sitzung und die aktuelle 3D-Ansicht
bereit (ToolContext und ExportContext). Werkzeuge und Exporter erscheinen
automatisch im Menü, sobald sie in ihrer Registry angemeldet sind.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from akicheast3d import __version__
from akicheast3d.core import Session, exporters, segmenters, tools
from akicheast3d.loading import SeriesInfo, scan
from akicheast3d.ui.disclaimer import show_disclaimer
from akicheast3d.ui.info_panel import InfoPanel
from akicheast3d.ui.open_series import OpenedSeries, open_series
from akicheast3d.ui.series_dialog import SeriesDialog
from akicheast3d.ui.structure_panel import StructurePanel
from akicheast3d.ui.tasks import TaskThread
from akicheast3d.ui.viewer_2d import Viewer2D
from akicheast3d.ui.viewer_3d import Viewer3D

APP_TITLE = "AKICHEAST 3D"
SIDEBAR_WIDTH = 300


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1400, 900)
        self._session: Session | None = None
        self._task: TaskThread | None = None

        self.viewer_3d = Viewer3D()
        self.viewer_2d = Viewer2D()
        self.info_panel = InfoPanel()
        self.structure_panel = StructurePanel()
        self.structure_panel.changed.connect(self.viewer_3d.update_structure)

        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.addWidget(self.info_panel)
        sidebar_layout.addWidget(self.structure_panel)
        sidebar_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidget(sidebar)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(SIDEBAR_WIDTH)

        views = QSplitter(Qt.Orientation.Vertical)
        views.addWidget(self.viewer_3d)
        views.addWidget(self.viewer_2d)
        views.setSizes([550, 350])

        main = QSplitter(Qt.Orientation.Horizontal)
        main.addWidget(scroll)
        main.addWidget(views)
        main.setStretchFactor(1, 1)
        self.setCentralWidget(main)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setMaximumWidth(260)
        self.progress.hide()
        self.statusBar().addPermanentWidget(self.progress)
        self.statusBar().showMessage("Datei > Ordner öffnen, um eine Serie zu laden.")

        self._create_menus()
        self._set_session_actions_enabled(False)

    # Kontext für Module (ToolContext und ExportContext)

    @property
    def session(self) -> Session | None:
        return self._session

    def request_redraw(self) -> None:
        for structure in self._session.structures if self._session else []:
            self.viewer_3d.update_structure(structure)
        for view in self.viewer_2d.views.values():
            view.update()

    def render_image(self) -> np.ndarray:
        return self.viewer_3d.render_image()

    # Menüs

    def _create_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&Datei")
        self.open_folder_action = QAction("&Ordner öffnen ...", self)
        self.open_folder_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_folder_action.triggered.connect(self.choose_folder)
        file_menu.addAction(self.open_folder_action)
        self.open_dicomdir_action = QAction("&DICOMDIR öffnen ...", self)
        self.open_dicomdir_action.triggered.connect(self.choose_dicomdir)
        file_menu.addAction(self.open_dicomdir_action)

        file_menu.addSeparator()
        export_menu = file_menu.addMenu("&Exportieren")
        self.export_actions = []
        for name in exporters.names():
            action = QAction(f"{name} ...", self)
            action.triggered.connect(lambda _=False, n=name: self.export(n))
            export_menu.addAction(action)
            self.export_actions.append(action)

        file_menu.addSeparator()
        quit_action = QAction("&Beenden", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        self.tool_actions = []
        if tools.names():
            tools_menu = self.menuBar().addMenu("&Werkzeuge")
            for name in tools.names():
                action = QAction(name, self)
                action.triggered.connect(lambda _=False, n=name: self.open_tool(n))
                tools_menu.addAction(action)
                self.tool_actions.append(action)

        help_menu = self.menuBar().addMenu("&Hilfe")
        notice_action = QAction("Hinweis: keine Diagnose", self)
        notice_action.triggered.connect(lambda: show_disclaimer(self))
        help_menu.addAction(notice_action)
        about_action = QAction(f"Über {APP_TITLE}", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        toolbar = self.addToolBar("Hauptleiste")
        toolbar.setMovable(False)
        toolbar.addAction(self.open_folder_action)
        toolbar.addActions(self.export_actions)

    def _set_session_actions_enabled(self, enabled: bool) -> None:
        for action in self.export_actions + self.tool_actions:
            action.setEnabled(enabled)

    def _set_busy(self, busy: bool) -> None:
        self.open_folder_action.setEnabled(not busy)
        self.open_dicomdir_action.setEnabled(not busy)
        self.progress.setVisible(busy)

    # Öffnen

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "DICOM-Ordner wählen")
        if folder:
            self.scan_path(Path(folder))

    def choose_dicomdir(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "DICOMDIR wählen", "", "DICOMDIR (DICOMDIR);;Alle Dateien (*)"
        )
        if path:
            self.scan_path(Path(path))

    def scan_path(self, path: Path) -> None:
        self._run(
            lambda report: scan(path, lambda value: report(value, "Serien werden gesucht")),
            self._series_found,
        )

    def _series_found(self, series: list[SeriesInfo]) -> None:
        if not series:
            QMessageBox.information(self, APP_TITLE, "In diesem Ordner wurden keine DICOM-Serien gefunden.")
            return
        dialog = SeriesDialog(series, self)
        if dialog.exec() and dialog.selected_series() is not None:
            self.load(dialog.selected_series())

    def load(self, series: SeriesInfo) -> None:
        segmenter = segmenters.create(segmenters.names()[0])
        self._run(lambda report: open_series(series, segmenter, report), self._show_series)

    def _show_series(self, opened: OpenedSeries) -> None:
        self._session = opened.session
        self.viewer_2d.set_volume(opened.session.volume)
        self.viewer_3d.set_surfaces(opened.surfaces)
        self.structure_panel.set_structures(opened.session.structures)
        self.info_panel.set_session(opened.session)
        self._set_session_actions_enabled(True)
        self.statusBar().showMessage("Serie geladen.", 5000)

    def _run(self, function, on_success) -> None:
        self._set_busy(True)
        self._task = TaskThread(function, self)
        self._task.progress.connect(self._show_progress)
        self._task.succeeded.connect(on_success)
        self._task.failed.connect(self._show_error)
        self._task.finished.connect(lambda: self._set_busy(False))
        self._task.start()

    def _show_progress(self, value: float, text: str) -> None:
        self.progress.setValue(round(value * 100))
        self.statusBar().showMessage(text)

    def _show_error(self, message: str) -> None:
        self.statusBar().clearMessage()
        QMessageBox.warning(self, APP_TITLE, message)

    # Werkzeuge und Export

    def open_tool(self, name: str) -> None:
        tool = tools.create(name)
        dock = QDockWidget(name, self)
        dock.setWidget(tool.create_panel(self))
        dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dock.destroyed.connect(lambda *_: tool.close())
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def export(self, name: str, path: Path | None = None) -> None:
        exporter = exporters.create(name)
        if path is None:
            chosen, _ = QFileDialog.getSaveFileName(self, name, "akicheast3d", exporter.file_filter)
            if not chosen:
                return
            path = Path(chosen)
        try:
            exporter.export(self, path)
        except Exception as error:  # noqa: BLE001
            QMessageBox.warning(self, APP_TITLE, f"Export fehlgeschlagen: {error}")
        else:
            self.statusBar().showMessage(f"Gespeichert: {path}", 5000)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"Über {APP_TITLE}",
            f"<b>{APP_TITLE}</b> {__version__}<br>Autor: Mihailo Obradovic<br><br>"
            "Anschauungs- und Gesprächswerkzeug, kein Medizinprodukt.",
        )

    def closeEvent(self, event) -> None:
        if self._task is not None and self._task.isRunning():
            self._task.wait()
        self.viewer_3d.close_viewer()
        super().closeEvent(event)
