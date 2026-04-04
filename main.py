#!/usr/bin/env python3
# ============================================================
# PAMS — main.py
# Paragon Apartment Management System — Entry Point (PySide6)
#
# Run:  python main.py
# Requires: Python 3.10-3.13, PySide6
# ============================================================
from __future__ import annotations
import sys, os
import importlib.util

if sys.version_info >= (3, 14):
    print(
        "PAMS startup blocked: Python 3.14 is not supported for this UI build.\n"
        "Use Python 3.10-3.13 and recreate the virtual environment."
    )
    raise SystemExit(1)

# ── Make sure the project root is on sys.path ──
sys.path.insert(0, os.path.dirname(__file__))


def _configure_qt_plugin_paths() -> None:
    """Remove plugin-path overrides so Qt uses PySide6 defaults."""
    for env_key in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
        os.environ.pop(env_key, None)


_configure_qt_plugin_paths()

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from pams import database as db
from pams.theme import PALETTE as P, get_global_qss, cycle_theme


class PAMSApp(QMainWindow):
    """Root QMainWindow — owns the full lifecycle."""

    APP_TITLE  = "Paragon Apartment Management System"
    MIN_WIDTH  = 1440
    MIN_HEIGHT = 860

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.APP_TITLE)
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)

        # ── Scale to 85 % of screen or minimum ──
        screen = QApplication.primaryScreen().availableGeometry()
        w = max(self.MIN_WIDTH, int(screen.width() * 0.85))
        h = max(self.MIN_HEIGHT, int(screen.height() * 0.85))
        x = (screen.width() - w) // 2
        y = (screen.height() - h) // 2
        self.setGeometry(x, y, w, h)

        # ── Init DB ──
        db.init_db()
        self._current_user: dict | None = None

        # ── Central stacked widget for view switching ──
        self._stack = QStackedWidget()
        self._stack.setObjectName("centralWidget")
        self.setCentralWidget(self._stack)

        self._show_login()

    # ──────────────────────────────────────────────────────
    # FRAME SWITCHING  (QStackedWidget replaces Tk's _swap)
    # ──────────────────────────────────────────────────────
    def _clear_stack(self):
        """Remove all pages from the stack."""
        while self._stack.count():
            w = self._stack.widget(0)
            self._stack.removeWidget(w)
            w.deleteLater()

    def _show_login(self):
        from pams.login_view import LoginView
        self._clear_stack()
        login = LoginView(on_login=self._on_login)
        login.theme_requested.connect(self._on_theme_switch_login)
        self._stack.addWidget(login)
        self._stack.setCurrentWidget(login)
        self.setWindowTitle(self.APP_TITLE)

    def _on_login(self, user: dict):
        self._current_user = user
        from pams.main_app import MainApp
        self._clear_stack()
        app_view = MainApp(user=user, on_logout=self._show_login)
        app_view.theme_requested.connect(self._on_theme_switch)
        self._stack.addWidget(app_view)
        self._stack.setCurrentWidget(app_view)
        self.setWindowTitle(
            f"{self.APP_TITLE}  —  {user['full_name']}  [{user['role']}]")

    def _on_theme_switch(self):
        # Save current active page before rebuilding
        current_page = "dashboard"
        if self._stack.count():
            curr = self._stack.currentWidget()
            if hasattr(curr, '_sidebar'):
                current_page = curr._sidebar._active_key

        name = cycle_theme()
        QApplication.instance().setStyleSheet(get_global_qss())

        from pams.main_app import MainApp
        self._clear_stack()
        app_view = MainApp(user=self._current_user, on_logout=self._show_login,
                           initial_page=current_page)
        app_view.theme_requested.connect(self._on_theme_switch)
        self._stack.addWidget(app_view)
        self._stack.setCurrentWidget(app_view)
        self.setWindowTitle(
            f"{self.APP_TITLE}  —  {self._current_user['full_name']}  [{self._current_user['role']}]  │  {name}")

    def _on_theme_switch_login(self):
        name = cycle_theme()
        QApplication.instance().setStyleSheet(get_global_qss())
        self._show_login()


# ──────────────────────────────────────────────────────────
# ENTRY
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    # High-DPI awareness
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(get_global_qss())

    window = PAMSApp()
    window.show()
    sys.exit(app.exec())
