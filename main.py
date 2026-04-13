#!/usr/bin/env python3
# ============================================================
# PAMS — main.py
# Paragon Apartment Management System — Entry Point (PySide6)
#
# Run:  python main.py
# Requires: Python 3.10-3.13, PySide6
#
# Contributors (UI):
#   Chouaib Hakim       — Student ID: 24018717
#   Sinoli Rodrigo      — Student ID: 24055025
# ============================================================
from __future__ import annotations  # enables postponed evaluation of type hints so we can use 'dict | None' notation in older Python
import sys, os                       # sys gives us access to the Python version and exit calls; os lets us build file paths
import importlib.util                # gives access to import utilities (imported for potential dynamic module checks)

if sys.version_info >= (3, 14):      # checks whether the running Python version is 3.14 or newer
    print(                           # prints a human-readable error message explaining why the app won't start
        "PAMS startup blocked: Python 3.14 is not supported for this UI build.\n"
        "Use Python 3.10-3.13 and recreate the virtual environment."
    )
    raise SystemExit(1)              # immediately terminates the process with exit code 1 (error) before Qt is even imported

# ── Make sure the project root is on sys.path ──
sys.path.insert(0, os.path.dirname(__file__))  # inserts the folder containing main.py at the front of the module search path so all 'pams' imports work


def _configure_qt_plugin_paths() -> None:
    """Remove plugin-path overrides so Qt uses PySide6 defaults."""
    for env_key in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):  # loops through both Qt plugin environment variable names
        os.environ.pop(env_key, None)   # removes the variable from the environment if it exists; None prevents a KeyError if it's missing


_configure_qt_plugin_paths()  # calls the function immediately so Qt plugin paths are clean before any Qt import happens

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget  # imports the main Qt application class, the top-level window, and the view-switching widget
from PySide6.QtCore import Qt                                             # imports the Qt namespace for constants like alignment flags and cursor types
from PySide6.QtGui import QFont                                           # imports QFont so we can set the default application-wide font
from PySide6.QtGui import QFont, QFontDatabase                            # re-imports both QFont and QFontDatabase (QFontDatabase lets us list installed fonts for fallback logic)

from pams import database as db                                           # imports the database module that handles all SQLite operations; aliased as 'db' for brevity
from pams.theme import PALETTE as P, get_global_qss, cycle_theme          # imports the colour palette (P), the QSS stylesheet builder, and the theme-cycling function


class PAMSApp(QMainWindow):
    """Root QMainWindow — owns the full lifecycle."""

    APP_TITLE  = "Paragon Apartment Management System"  # sets the text shown in the window title bar
    MIN_WIDTH  = 1440   # sets the minimum allowed window width in pixels so the layout never becomes unusably narrow
    MIN_HEIGHT = 860    # sets the minimum allowed window height in pixels so the layout never becomes unusably short

    def __init__(self):
        super().__init__()                              # calls QMainWindow's __init__ to set up the base Qt window infrastructure
        self.setWindowTitle(self.APP_TITLE)             # puts the 'Paragon Apartment Management System' text into the OS title bar
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)  # prevents the user from resizing the window below 1440x860

        # ── Scale to 85 % of screen or minimum ──
        screen = QApplication.primaryScreen().availableGeometry()  # gets the usable screen area (excluding taskbar) as a QRect
        w = max(self.MIN_WIDTH, int(screen.width() * 0.85))        # calculates the initial width as 85% of screen width, but no less than 1440
        h = max(self.MIN_HEIGHT, int(screen.height() * 0.85))      # calculates the initial height as 85% of screen height, but no less than 860
        x = (screen.width() - w) // 2                              # calculates the left edge x position to horizontally centre the window
        y = (screen.height() - h) // 2                             # calculates the top edge y position to vertically centre the window
        self.setGeometry(x, y, w, h)                               # sets the window's position and size on screen all at once

        # ── Init DB ──
        db.init_db()                        # creates all database tables and seeds demo data if the database is brand new
        self._current_user: dict | None = None  # stores the currently logged-in user dict; starts as None (nobody logged in yet)

        # ── Central stacked widget for view switching ──
        self._stack = QStackedWidget()              # creates a stacked widget that acts like a tab system — only one page visible at a time
        self._stack.setObjectName("centralWidget")  # names this widget "centralWidget" so QSS rules can target it by name
        self.setCentralWidget(self._stack)           # tells QMainWindow to use our stack as the main content area

        self._show_login()  # navigates to the login screen as the first visible page when the app opens

    # ──────────────────────────────────────────────────────
    # FRAME SWITCHING  (QStackedWidget replaces Tk's _swap)
    # ──────────────────────────────────────────────────────
    def _clear_stack(self):
        """Remove all pages from the stack."""
        while self._stack.count():              # loops as long as there is at least one widget in the stack
            w = self._stack.widget(0)           # grabs the first widget currently sitting in slot 0 of the stack
            self._stack.removeWidget(w)         # removes that widget from the stack so it's no longer displayed
            w.deleteLater()                     # schedules the widget for deletion after the current event is processed, freeing memory

    def _show_login(self):
        from pams.login_view import LoginView           # lazily imports LoginView here to avoid circular imports at module level
        self._clear_stack()                             # removes any previously shown page (e.g. the main dashboard) from the stack
        login = LoginView(on_login=self._on_login)      # creates the login form widget and passes _on_login as the callback for a successful sign-in
        login.theme_requested.connect(self._on_theme_switch_login)  # connects the login page's 'change theme' button to the theme-switching handler
        self._stack.addWidget(login)                    # adds the login page to the stack so it can be displayed
        self._stack.setCurrentWidget(login)             # makes the login page the visible (active) page in the stack
        self.setWindowTitle(self.APP_TITLE)             # resets the title bar to just the app name (removes any logged-in user info)

    def _on_login(self, user: dict):
        self._current_user = user                                   # stores the authenticated user's data dict so other methods can read it
        from pams.main_app import MainApp                           # lazily imports the main application shell to avoid circular imports
        self._clear_stack()                                         # removes the login page from the stack
        app_view = MainApp(user=user, on_logout=self._show_login)   # creates the full dashboard/sidebar interface, passing logout callback
        app_view.theme_requested.connect(self._on_theme_switch)     # connects the sidebar's theme button to the theme handler
        self._stack.addWidget(app_view)                             # adds the main app view to the stack
        self._stack.setCurrentWidget(app_view)                      # switches the visible page to the main dashboard
        self.setWindowTitle(                                        # updates the title bar to show the user's name and role, e.g. "PAMS — Alice Morrison  [Administrator]"
            f"{self.APP_TITLE}  —  {user['full_name']}  [{user['role']}]")

    def _on_theme_switch(self):
        # Save current active page before rebuilding
        current_page = "dashboard"                   # defaults to 'dashboard' in case we can't detect the current page
        if self._stack.count():                      # checks that there is at least one page in the stack before reading it
            curr = self._stack.currentWidget()       # gets the widget (MainApp) currently visible in the stack
            if hasattr(curr, '_sidebar'):            # checks if the MainApp has a _sidebar attribute before trying to read its active key
                current_page = curr._sidebar._active_key  # reads which sidebar item is currently highlighted, e.g. 'tenants'

        name = cycle_theme()                          # advances to the next theme (Light → Dark → Light …) and mutates PALETTE in place, returning the new theme name
        QApplication.instance().setStyleSheet(get_global_qss())  # rebuilds the QSS stylesheet from the updated PALETTE and applies it to every widget in the app instantly

        from pams.main_app import MainApp             # lazily imports MainApp to avoid circular imports at the top of the file
        self._clear_stack()                           # removes the old main app widget from the stack (needed after a palette change so new colours take effect)
        app_view = MainApp(user=self._current_user, on_logout=self._show_login,
                           initial_page=current_page)   # recreates the entire dashboard shell with the new theme, returning to whichever page the user was on
        app_view.theme_requested.connect(self._on_theme_switch)   # reconnects the theme button signal on the new widget
        self._stack.addWidget(app_view)               # adds the freshly themed app view to the stack
        self._stack.setCurrentWidget(app_view)        # makes the new app view the visible page
        self.setWindowTitle(                           # updates the title bar to include the new theme name, e.g. "PAMS — Alice Morrison  [Administrator]  │  🌙  Dark"
            f"{self.APP_TITLE}  —  {self._current_user['full_name']}  [{self._current_user['role']}]  │  {name}")

    def _on_theme_switch_login(self):
        name = cycle_theme()                                       # advances the theme cycle and mutates PALETTE so new colours take effect immediately
        QApplication.instance().setStyleSheet(get_global_qss())   # applies the updated QSS stylesheet globally so the login page refreshes its colours
        self._show_login()                                         # rebuilds the entire login screen from scratch so all widgets pick up the new theme colours


# ──────────────────────────────────────────────────────────
# ENTRY
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    # High-DPI awareness
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)  # tells Qt to use the exact fractional DPI scale factor rather than rounding it, giving sharper UI on 125%/150% screens

    app = QApplication(sys.argv)  # creates the Qt application object; sys.argv passes any command-line arguments (required even if none are used)
    # Force Qt's cross-platform Fusion renderer so QSS is properly applied to
    # all widgets including native dialogs (QMessageBox, QInputDialog, etc.).
    # Without this, Windows native rendering overrides stylesheet colours.
    app.setStyle("Fusion")   # switches to Qt's own Fusion style engine — makes QSS rules apply consistently on every platform
    # "Segoe UI" is Windows-only; resolve a cross-platform substitute before
    # any widget is created so every QFont("Segoe UI", ...) call silently maps
    # to the correct font automatically (eliminates the 50 ms alias warning).
    import sys as _sys, platform as _platform  # re-imports sys and platform under private names for use in the font fallback block
    # Pick the first installed font from the preference list.
    _families = set(QFontDatabase.families())  # retrieves the set of all font family names installed on this machine
    _fallback = next(                           # finds the first font from the preference list that is actually installed on this system
        (f for f in ("Helvetica Neue", "Arial", "Trebuchet MS",
                     "Liberation Sans", "DejaVu Sans")
         if f in _families),
        None,                                   # uses None as the default if none of the listed fonts are installed
    )
    if _fallback:                                                     # only set the font substitution if we actually found an available fallback font
        QFont.insertSubstitution("Segoe UI", _fallback)              # tells Qt to silently replace every "Segoe UI" font request with _fallback on non-Windows systems
    app.setFont(QFont("Segoe UI", 10))                               # sets the default application font to 'Segoe UI' at size 10 for all widgets that don't specify their own font
    app.setStyleSheet(get_global_qss())                              # applies the initial global QSS stylesheet (light theme by default) to every widget in the application

    window = PAMSApp()   # creates the main window, which initialises the database, builds the stacked widget, and shows the login screen
    window.show()        # makes the main window visible on screen
    sys.exit(app.exec()) # starts the Qt event loop (blocking); sys.exit ensures the OS gets the app's exit code when the window is closed
