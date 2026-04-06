# ============================================================
# PAMS — login_view.py
# Modern split-panel animated login  (PySide6)
# ============================================================
from __future__ import annotations   # allows forward-reference type hints in Python 3.9 and earlier
import math, random   # math for sine/cosine used in animations; random for orb and star position generation
from typing import Callable   # imports Callable so the on_login parameter can be correctly type-hinted as a function

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,   # core layout and text widgets
    QPushButton, QFrame, QSizePolicy, QSpacerItem,           # button, decorative frame, and spacer items
)
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal   # Qt flags, animation timer, floating-point rectangles, and Signal for emitting events
from PySide6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QRadialGradient,   # fonts, colours, the painter, and gradient fill types
    QConicalGradient, QPen, QBrush, QIcon, QPixmap, QAction, QPainterPath,   # conical gradient for spinning ring, pen/brush, icon/pixmap types, QPainterPath for eye curve
)

from .theme import PALETTE as P, FONTS as F, DIMS as D, lerp_color, is_dark_theme   # imports design tokens: colours, fonts, dimensions, and theme helpers
from .widgets import qfont, styled_button, _blend, Toast   # imports shared widget utilities: font helper, button factory, colour blender, and toast notification
from . import theme as _theme   # imports the full theme module so cycle_theme() could be called if needed
from . import database as db   # imports the database layer to call db.login() for credential checking


def _make_eye_icon(visible: bool, color: str = "#9CA3AF") -> QIcon:
    """Create a clean eye / eye-slash icon as QIcon using QPainter."""
    size = 32   # icon canvas is 32×32 pixels
    pixmap = QPixmap(size, size)   # creates a 32×32 pixel canvas for drawing the icon
    pixmap.fill(Qt.transparent)   # fills the canvas with transparent pixels so the icon has no background
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)   # enables smooth anti-aliased lines for the eye shape curves
    pen = QPen(QColor(color), 1.8)   # creates a 1.8px pen in the specified colour (grey by default) for drawing the eye outline
    p.setPen(pen)

    cx, cy = size // 2, size // 2   # calculates the centre point of the icon (16, 16)

    # Eye shape — almond outline drawn as a cubic Bezier curve
    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    path.moveTo(4, cy)   # starts the eye shape at the left tip of the almond
    path.cubicTo(8, cy - 8, 24, cy - 8, 28, cy)   # draws the top curve of the almond shape from left to right
    path.cubicTo(24, cy + 8, 8, cy + 8, 4, cy)   # draws the bottom curve of the almond shape back to the left tip
    p.drawPath(path)   # renders the complete almond eye outline

    # Iris circle — drawn as a plain circle at the eye centre
    p.drawEllipse(QRectF(cx - 4, cy - 4, 8, 8))   # draws an 8×8 pixel circle for the iris

    # Pupil dot — filled solid circle at the exact centre of the iris
    p.setPen(Qt.NoPen)   # removes the outline pen so the pupil has no border
    p.setBrush(QColor(color))   # fills the pupil with the icon colour
    p.drawEllipse(QRectF(cx - 2, cy - 2, 4, 4))   # draws a 4×4 pixel filled circle for the pupil

    # Slash line when hidden — a diagonal line across the eye indicating password is hidden
    if not visible:
        pen.setWidth(2.2)   # uses a slightly thicker 2.2px line for the slash to make it prominent
        p.setPen(pen)
        p.drawLine(6, 6, 26, 26)   # draws a diagonal line from top-left to bottom-right across the icon

    p.end()
    return QIcon(pixmap)   # converts the finished pixmap drawing into a QIcon that can be assigned to a button action


class LoginView(QWidget):
    """
    Full-screen modern login.
    Left  : animated gradient panel — floating orbs + city skyline.
    Right : clean white form panel.
    """
    theme_requested = Signal()   # emitted when the user clicks the animated logo to toggle light/dark mode

    _GRAD_TOP   = "#040C1C"   # very dark navy colour for the top of the left panel background gradient
    _GRAD_MID   = "#0E2050"   # deep cobalt blue for the middle of the background gradient
    _GRAD_BOT   = "#020610"   # almost black for the bottom of the background gradient
    _ORB_COLORS = ["#4361EE", "#6366F1", "#3B49CC",
                    "#818CF8", "#4F5BD5", "#A5B4FC", "#8B5CF6",
                    "#7C3AED", "#6D28D9"]   # palette of blue/indigo/violet colours randomly assigned to floating orbs
    _ORB_COUNT  = 20   # total number of floating glowing orbs shown on the left panel

    DEMO_CREDS = [
        ("Admin",      "admin_bristol", "admin123"),    # quick-login chip for the Administrator role
        ("Manager",    "manager",       "manager123"),  # quick-login chip for the Manager role
        ("Front Desk", "frontdesk1",    "front123"),    # quick-login chip for the Front-Desk Staff role
        ("Finance",    "finance1",      "finance123"),  # quick-login chip for the Finance Manager role
        ("Maint.",     "maint1",        "maint123"),    # quick-login chip for the Maintenance Staff role
    ]   # list of demo credentials shown as clickable chips on the login form

    def __init__(self, on_login: Callable, parent=None):
        super().__init__(parent)
        self._on_login   = on_login   # stores the callback function to call once authentication succeeds
        self._pw_visible = False      # tracks whether the password field is showing plain text (True) or dots (False)
        self._logo_tick  = 0          # animation frame counter used to drive the orbiting logo and star twinkle on the left panel
        self._init_orbs()             # randomly generates the initial positions and velocities for all floating orbs

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)   # removes all padding so both panels fill the full window with no gap
        layout.setSpacing(0)   # removes the gap between the left and right panels

        # ── Left: animated canvas (56 %) ──
        self._left_panel = _AnimatedPanel(self)   # creates the animated gradient+skyline+orbs canvas
        layout.addWidget(self._left_panel, 56)   # gives the left panel 56% of the total window width

        # ── Right: form panel (44 %) ──
        right = QWidget()
        right.setStyleSheet(f"background-color: {P.bg_card};")   # sets the right panel background to the card colour (white in light mode)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addStretch(1)   # pushes the form down from the top so it appears vertically centred

        form = self._build_form()   # builds the complete login form (logo, fields, button, demo chips)
        right_layout.addWidget(form, 0, Qt.AlignCenter)   # centres the form horizontally in the right panel
        right_layout.addStretch(1)   # pushes the form up from the bottom so it appears vertically centred
        layout.addWidget(right, 44)   # gives the right panel the remaining 44% of the total window width

        # ── Start animation ──
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)   # connects the timer to the _tick method that moves the orbs each frame
        self._timer.start(45)   # fires every 45ms (~22fps) to animate the floating orbs on the left panel

    # ──────────────────────────────────────────────────────
    # ORB DATA
    # ──────────────────────────────────────────────────────
    def _init_orbs(self):
        random.seed()   # re-seeds the random number generator with the system clock so orb positions are different each launch
        self._orbs = []
        for _ in range(self._ORB_COUNT):
            self._orbs.append({
                "x": random.uniform(0.05, 0.93),     # starting horizontal position as a fraction of panel width (0–1)
                "y": random.uniform(0.04, 0.82),     # starting vertical position as a fraction of panel height (0–1)
                "r": random.randint(28, 88),          # radius in pixels: small orbs are 28px wide, large orbs are 88px wide
                "vx": random.uniform(-0.00035, 0.00035),  # horizontal velocity as fraction per tick (very slow drift left or right)
                "vy": random.uniform(-0.00028, 0.00028),  # vertical velocity as fraction per tick (very slow drift up or down)
                "col": random.choice(self._ORB_COLORS),   # randomly picks one of the blue/indigo/violet accent colours for this orb
            })

    def _tick(self):
        for orb in self._orbs:
            orb["x"] += orb["vx"]   # moves the orb horizontally by its velocity amount this frame
            orb["y"] += orb["vy"]   # moves the orb vertically by its velocity amount this frame
            if not 0.01 < orb["x"] < 0.99:
                orb["vx"] *= -1   # reverses horizontal direction when the orb reaches the 1% left or 99% right boundaries
            if not 0.01 < orb["y"] < 0.88:
                orb["vy"] *= -1   # reverses vertical direction when the orb reaches the 1% top or 88% bottom boundaries
        self._logo_tick += 1   # increments the frame counter that drives the logo spin and star twinkle animations
        self._left_panel.orbs = self._orbs   # passes the updated orb positions to the left panel so it can draw them
        self._left_panel.logo_tick = self._logo_tick   # passes the current frame count to the left panel for timed animations
        self._left_panel.update()   # requests a repaint of the left panel with the new orb positions

    # ──────────────────────────────────────────────────────
    # RIGHT PANEL — FORM
    # ──────────────────────────────────────────────────────
    def _build_form(self) -> QWidget:
        form = QWidget()
        form.setFixedWidth(400)   # locks the form column to exactly 400px wide so it doesn't stretch awkwardly on wide screens
        form.setStyleSheet(f"background-color: {P.bg_card};")   # gives the form the same card background as the right panel
        fl = QVBoxLayout(form)
        fl.setSpacing(5)   # puts 5px of space between each form element
        fl.setContentsMargins(14, 0, 14, 0)   # adds 14px left/right padding and no top/bottom margin inside the form

        # Logo + brand
        logo = _AnimatedLogoWidget()   # creates the spinning 3D sphere logo shown above the form title
        logo.clicked.connect(self.theme_requested.emit)   # emits the theme_requested signal when the user clicks the logo to toggle light/dark mode
        fl.addWidget(logo, 0, Qt.AlignCenter)

        title = QLabel("PARAGON")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))   # uses a large 22pt bold font to make the brand name prominent
        title.setStyleSheet(f"color: {P.accent2};")   # colours the brand name with the secondary accent colour (teal/violet)
        title.setAlignment(Qt.AlignCenter)
        fl.addWidget(title)

        sub = QLabel("Apartment Management System")
        sub.setFont(QFont("Segoe UI", 9))   # uses a small 9pt font for the subtitle so it doesn't compete with the brand name
        sub.setStyleSheet(f"color: {P.text_muted};")   # sets the subtitle to the muted grey colour so it reads as secondary info
        sub.setAlignment(Qt.AlignCenter)
        fl.addWidget(sub)

        # Accent bar
        bar = _GradientBar(P.accent, P.accent2)   # creates a thin horizontal bar that fades from the primary to secondary accent colour
        bar.setFixedHeight(4)   # locks the decorative bar to 4px tall
        fl.addWidget(bar)
        fl.addSpacing(10)   # adds 10px of extra space below the accent bar before the welcome text

        # Welcome text
        wel = QLabel("Welcome back")
        wel.setFont(QFont("Segoe UI", 20, QFont.Bold))   # uses a large 20pt bold font for the greeting heading
        wel.setStyleSheet(f"color: {P.text_primary};")
        wel.setAlignment(Qt.AlignCenter)
        fl.addWidget(wel)
        wel2 = QLabel("Sign in to continue to your dashboard")
        wel2.setFont(QFont("Segoe UI", 11))   # uses an 11pt font for the instruction text below the greeting
        wel2.setStyleSheet(f"color: {P.text_muted};")   # sets the instruction text to the muted grey colour
        wel2.setAlignment(Qt.AlignCenter)
        fl.addWidget(wel2)
        fl.addSpacing(16)   # adds 16px of space between the welcome text and the first input field

        # Username
        fl.addWidget(self._field_label("USERNAME"))   # adds the 'USERNAME' label above the input field
        self._user_entry = QLineEdit()
        self._user_entry.setPlaceholderText("Enter your username")   # shows a grey hint text inside the username field when it is empty
        self._user_entry.setFixedHeight(D.input_h)   # sets the input field to the standard input height from the design tokens
        fl.addWidget(self._user_entry)
        fl.addSpacing(6)   # adds 6px of space between the username field and the password label

        # Password — eye icon INSIDE the input field
        fl.addWidget(self._field_label("PASSWORD"))   # adds the 'PASSWORD' label above the password field
        self._pw_entry = QLineEdit()
        self._pw_entry.setPlaceholderText("Enter your password")   # shows a grey hint text inside the password field when it is empty
        self._pw_entry.setEchoMode(QLineEdit.Password)   # hides the typed characters as dots so the password is not visible by default
        self._pw_entry.setFixedHeight(D.input_h)   # sets the password field to the standard input height from the design tokens
        # Add eye toggle action inside the line edit (right side)
        eye_color = P.text_muted if not is_dark_theme() else "#8899B4"   # uses a lighter eye icon colour in dark mode so it is visible against the dark background
        self._eye_action = QAction(_make_eye_icon(False, eye_color), "", self._pw_entry)   # creates the eye icon action — starts as closed-eye (password hidden)
        self._eye_action.setToolTip("Show / hide password")   # shows a tooltip explaining the eye button when hovered
        self._pw_entry.addAction(self._eye_action, QLineEdit.TrailingPosition)   # places the eye icon at the right end of the password field
        self._eye_action.triggered.connect(self._toggle_pw)   # connects the eye button click to the toggle function that shows/hides the password
        # Extra right padding so text doesn't overlap the icon
        self._pw_entry.setStyleSheet(
            self._pw_entry.styleSheet() + f"padding-right: 38px;")   # adds 38px of extra right padding inside the password field so typed text doesn't slide under the eye icon
        fl.addWidget(self._pw_entry)

        # Error label
        self._err_lbl = QLabel("")   # creates an initially empty error message label below the password field
        self._err_lbl.setFont(QFont("Segoe UI", 10))
        self._err_lbl.setStyleSheet(f"color: {P.danger};")   # sets the error text colour to red so it is immediately noticeable
        self._err_lbl.setAlignment(Qt.AlignCenter)
        self._err_lbl.setWordWrap(True)   # allows the error message to wrap to multiple lines if it is too long
        fl.addWidget(self._err_lbl)

        # Sign in button — gradient style
        self._login_btn = QPushButton("SIGN IN")
        self._login_btn.setFont(QFont("Segoe UI", 14, QFont.Bold))   # uses large 14pt bold text on the main sign-in button
        self._login_btn.setCursor(Qt.PointingHandCursor)   # changes the cursor to a hand pointer when hovering over the button
        self._login_btn.setFixedHeight(50)   # locks the sign-in button to 50px tall so it is visually prominent
        self._login_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {P.accent}, stop:1 {_blend(P.accent, '#8B5CF6', 0.45)});
                color: #FFFFFF; border: none;
                border-radius: 14px; font-size: 14px; font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {P.accent_dim}, stop:1 {_blend(P.accent_dim, '#7C3AED', 0.45)});
            }}
            QPushButton:pressed {{
                background: {P.accent_dim};
            }}
        """)   # gives the sign-in button a left-to-right gradient from indigo accent to purple accent; darkens on hover and press
        self._login_btn.clicked.connect(self._attempt_login)   # connects the button click to the login attempt handler
        fl.addSpacing(10)   # adds 10px of space above the sign-in button
        fl.addWidget(self._login_btn)

        # Divider
        fl.addSpacing(6)
        div_row = QHBoxLayout()
        div_row.setContentsMargins(0, 0, 0, 0)
        sep1 = QFrame(); sep1.setFrameShape(QFrame.HLine)   # creates a horizontal line on the left of the 'or' divider
        sep1.setStyleSheet(f"color: {P.divider};")   # colours the left separator line with the theme divider colour
        sep1.setFixedHeight(1)   # forces the separator to exactly 1px tall
        div_row.addWidget(sep1, 1, Qt.AlignVCenter)
        or_lbl = QLabel("or")   # creates the 'or' text in the centre of the divider row
        or_lbl.setFont(qfont(F.caption))   # uses the tiny caption font so 'or' looks like a secondary separator, not a heading
        or_lbl.setStyleSheet(f"color: {P.text_muted};")   # sets the 'or' label to muted grey
        or_lbl.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        div_row.addWidget(or_lbl, 0, Qt.AlignVCenter)
        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)   # creates a horizontal line on the right of the 'or' divider
        sep2.setStyleSheet(f"color: {P.divider};")
        sep2.setFixedHeight(1)
        div_row.addWidget(sep2, 1, Qt.AlignVCenter)
        fl.addLayout(div_row)   # inserts the complete divider row (line + 'or' + line) into the form layout

        # Demo chips
        fl.addSpacing(4)
        demo_lbl = QLabel("QUICK DEMO LOGIN")
        demo_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))   # uses small 9pt bold caps so the label reads as a section header
        demo_lbl.setStyleSheet(f"color: {P.text_muted};")   # sets the demo label to muted grey so it doesn't overpower the chips
        demo_lbl.setAlignment(Qt.AlignCenter)
        fl.addWidget(demo_lbl)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)   # puts 6px gaps between each quick-demo role chip
        _dark = is_dark_theme()   # checks whether the app is currently in dark mode to pick the right chip colours
        # In dark mode, use brighter chip colors so ALL chips are clearly visible
        if _dark:
            role_colors = {
                "Admin": "#818CF8", "Manager": "#94A3B8", "Front Desk": "#34D399",
                "Finance": "#FBBF24", "Maint.": "#F87171",
            }   # brighter colours for dark mode so the chips glow against the dark background
        else:
            role_colors = {
                "Admin": P.accent, "Manager": "#475569", "Front Desk": P.success,
                "Finance": P.warning, "Maint.": P.danger,
            }   # standard theme colours for light mode: indigo, grey, green, amber, red
        for role, user, pw in self.DEMO_CREDS:
            color = role_colors.get(role, P.accent)   # picks the colour for this role, defaulting to the main accent colour
            chip = QPushButton(role)   # creates a clickable chip button labelled with the role name (e.g. "Admin")
            chip.setCursor(Qt.PointingHandCursor)   # changes the cursor to a hand pointer over the chip
            chip.setFont(QFont("Segoe UI", 10, QFont.Bold))   # uses 10pt bold for the chip label text
            if _dark:
                # Dark mode: semi-transparent background so chips glow
                bg = _blend(color, P.bg_card, 0.82)   # very light tint (82% blended with card background) for the chip fill
                bg_hover = _blend(color, P.bg_card, 0.68)   # slightly more opaque tint on hover to show interaction
                border_col = _blend(color, P.bg_card, 0.40)   # 40% blended border so the chip outline is visible but not harsh
            else:
                bg = _blend(color, P.bg_card, 0.89)   # very light tint for light mode chip background
                bg_hover = _blend(color, P.bg_card, 0.78)   # slightly more opaque tint on hover in light mode
                border_col = _blend(color, P.bg_card, 0.45)   # 45% blended border for the light mode chip outline
            chip.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg}; color: {color};
                    border: 1.5px solid {border_col};
                    border-radius: 10px; padding: 10px 8px;
                }}
                QPushButton:hover {{
                    background-color: {bg_hover};
                    border-color: {color};
                }}
            """)   # styles each chip with a lightly tinted background, coloured text, and a border that brightens on hover
            chip.clicked.connect(
                lambda checked=False, u=user, p=pw: self._quick_demo(u, p))   # connects the click to _quick_demo, pre-filling the username/password and triggering login
            chips_row.addWidget(chip)
        fl.addLayout(chips_row)   # adds the row of five role chips to the form layout

        # Enter key binding
        self._user_entry.returnPressed.connect(self._attempt_login)   # allows pressing Enter in the username field to submit the form
        self._pw_entry.returnPressed.connect(self._attempt_login)   # allows pressing Enter in the password field to submit the form

        return form   # returns the fully built form widget to the caller

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)   # creates a small all-caps label above an input field (e.g. "USERNAME")
        lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))   # uses small 9pt bold so it reads as a form field label, not a main heading
        lbl.setStyleSheet(f"color: {P.text_muted};")   # sets the label to muted grey so it is secondary to the input field itself
        return lbl

    # ──────────────────────────────────────────────────────
    # ACTIONS
    # ──────────────────────────────────────────────────────
    def _toggle_pw(self):
        self._pw_visible = not self._pw_visible   # flips the visibility flag: True = show password, False = hide as dots
        self._pw_entry.setEchoMode(
            QLineEdit.Normal if self._pw_visible else QLineEdit.Password)   # switches between plain text and masked dots based on the flag
        eye_color = P.text_muted if not is_dark_theme() else "#8899B4"   # adjusts the eye icon colour for the current theme
        self._eye_action.setIcon(_make_eye_icon(self._pw_visible, eye_color))   # redraws the eye icon — open eye when visible, eye-slash when hidden

    def _attempt_login(self):
        username = self._user_entry.text().strip()   # reads the username field and strips any leading/trailing whitespace
        password = self._pw_entry.text().strip()   # reads the password field and strips any leading/trailing whitespace
        if not username or not password:
            self._err_lbl.setText("Please fill in both fields.")   # shows an error if the user left either field empty
            return
        self._err_lbl.setText("")   # clears any previous error message when the form is valid
        self._login_btn.setText("Signing in...")   # changes the button label to a loading message while authentication runs
        self._login_btn.setEnabled(False)   # disables the button to prevent double-submission during the auth delay
        QTimer.singleShot(400, lambda: self._do_auth(username, password))   # waits 400ms (for UX feel) then runs the actual database credential check

    def _do_auth(self, username: str, password: str):
        user = db.login(username, password)   # calls the database login function which hashes the password and checks credentials
        if user:
            self._login_btn.setText("SUCCESS")   # briefly shows 'SUCCESS' on the button before transitioning to the dashboard
            QTimer.singleShot(300, lambda: self._on_login(user))   # waits 300ms then calls the on_login callback with the authenticated user dict
        else:
            self._login_btn.setText("SIGN IN")   # restores the button label after a failed login
            self._login_btn.setEnabled(True)   # re-enables the button so the user can try again
            self._err_lbl.setText("Invalid username or password.")   # shows the authentication error message in red
            self._pw_entry.clear()   # clears the password field after a failed attempt for security

    def _quick_demo(self, username: str, password: str):
        self._user_entry.setText(username)   # pre-fills the username field with the demo account's username
        self._pw_entry.setText(password)   # pre-fills the password field with the demo account's password
        self._err_lbl.setText("")   # clears any previous error message before the quick demo login
        QTimer.singleShot(80, self._attempt_login)   # waits 80ms so the user can see the fields filled in, then submits the form automatically

    def destroy(self):
        self._timer.stop()   # stops the orb animation timer when the login view is destroyed to prevent background activity


# ──────────────────────────────────────────────────────────
# ANIMATED LEFT PANEL  (QPainter-based)
# ──────────────────────────────────────────────────────────
class _AnimatedPanel(QWidget):
    """Left panel with gradient bg, floating orbs, star dots, city skyline, and brand text."""

    _GRAD_TOP = "#040C1C"   # near-black navy for the top of the left panel gradient
    _GRAD_MID = "#0E2050"   # deep blue for the middle of the gradient
    _GRAD_BOT = "#020610"   # almost black for the bottom of the gradient

    def __init__(self, parent=None):
        super().__init__(parent)
        self.orbs = []   # list of orb dicts updated every frame by LoginView._tick()
        self.logo_tick = 0   # current animation frame number used for timed effects like star twinkle
        self._buildings_rng = random.Random(99)  # fixed-seed RNG so window lights look the same every frame
        # Pre-generate star positions
        self._stars = []
        rng = random.Random(42)   # fixed seed 42 so stars appear in the same positions every time the panel is shown
        for _ in range(60):
            self._stars.append({
                "x": rng.uniform(0.02, 0.98),   # horizontal position as fraction of panel width
                "y": rng.uniform(0.02, 0.75),   # vertical position in the top 75% of the panel (above skyline)
                "r": rng.uniform(0.5, 2.0),     # radius between 0.5px (tiny) and 2.0px (small)
                "a": rng.randint(60, 200),       # base alpha value for this star (controls how bright it can get)
            })

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)   # enables smooth anti-aliased rendering for orbs and star dots
        w, h = self.width(), self.height()
        if w < 2:
            p.end(); return   # skips painting if the panel width is too small (prevents division-by-zero on startup)

        # ── Gradient background ──
        grad = QLinearGradient(0, 0, 0, h)   # creates a vertical gradient from top to bottom of the panel
        grad.setColorAt(0.0, QColor(self._GRAD_TOP))   # starts with near-black navy at the top
        grad.setColorAt(0.50, QColor(self._GRAD_MID))  # transitions to deep cobalt blue in the middle
        grad.setColorAt(1.0, QColor(self._GRAD_BOT))   # ends with near-black at the bottom
        p.fillRect(0, 0, w, h, grad)   # paints the entire panel background with the night-sky gradient

        # ── Star dots ──
        for star in self._stars:
            sx = int(star["x"] * w)   # converts the 0–1 fractional position to actual pixel x coordinate
            sy = int(star["y"] * h)   # converts the 0–1 fractional position to actual pixel y coordinate
            sr = star["r"]
            sc = QColor("#FFFFFF")
            # Twinkle effect
            twinkle = int(star["a"] * (0.6 + 0.4 * abs(math.sin(self.logo_tick * 0.02 + star["x"] * 10))))   # makes each star's alpha oscillate at a slightly different rate using its x position as a phase offset
            sc.setAlpha(min(255, twinkle))   # clamps the final alpha to 255 so no star becomes over-bright
            p.setPen(Qt.NoPen)
            p.setBrush(sc)
            p.drawEllipse(QRectF(sx - sr, sy - sr, sr * 2, sr * 2))   # draws the star as a tiny filled circle

        # ── Orbs ──
        p.setPen(Qt.NoPen)
        for orb in self.orbs:
            ax = orb["x"] * w   # converts the fractional orb x position to pixel coordinates
            ay = orb["y"] * h   # converts the fractional orb y position to pixel coordinates
            r = orb["r"]
            # Halo
            halo_col = QColor(_blend(orb["col"], self._GRAD_TOP, 0.68))   # blends the orb colour 68% toward the background for a very faint outer halo
            halo_col.setAlpha(55)   # sets the halo to semi-transparent (alpha 55) so it glows softly without obscuring stars
            p.setBrush(halo_col)
            p.drawEllipse(QRectF(ax - r*2, ay - r*2, r*4, r*4))   # draws the halo as a circle twice the orb's radius
            # Core
            core_col = QColor(_blend(orb["col"], self._GRAD_TOP, 0.45))   # blends the orb colour 45% toward the background for the visible orb body
            core_col.setAlpha(95)   # sets the core to mostly transparent (alpha 95) for a glowing soft light effect
            p.setBrush(core_col)
            p.drawEllipse(QRectF(ax - r, ay - r, r*2, r*2))   # draws the orb core at its actual radius

        # ── City skyline ──
        self._draw_skyline(p, w, h)   # calls the skyline drawing method to paint buildings and lit windows at the bottom

        # ── Brand text ──
        self._draw_brand(p, w, h)   # calls the brand text drawing method to paint 'PARAGON' and the tagline

        # ── Animated logo ──
        self._draw_logo(p, w, h)   # calls the logo drawing method to paint the pulsing ring logo at the top

        p.end()

    def _draw_skyline(self, p: QPainter, w: int, h: int):
        rng = random.Random(99)   # fixed-seed RNG so window light patterns stay consistent across every repaint
        ground = h   # places the base of all buildings at the very bottom of the panel
        sil_col = QColor(_blend("#FFFFFF", self._GRAD_BOT, 0.87))   # building silhouette colour: 87% dark background + 13% white for a dim navy building colour
        roof_col = QColor(_blend("#FFFFFF", self._GRAD_BOT, 0.82))   # slightly lighter colour for the roof strip at the top of each building
        win_lit  = QColor(_blend("#FFF0A0", self._GRAD_MID, 0.42))   # lit window colour: warm yellow blended 42% with the mid-gradient blue
        win_dark = QColor(_blend("#FFFFFF", self._GRAD_BOT, 0.78))   # unlit window colour: dim grey, darker than the building silhouette

        buildings = [
            # Each tuple: (start_x_frac, width_frac, height_frac, floor_count, window_columns)
            (0.00, 0.07, 0.27, 4, 2), (0.06, 0.05, 0.40, 6, 1),   # left edge buildings
            (0.10, 0.09, 0.56, 8, 2), (0.18, 0.07, 0.35, 5, 2),   # near-left buildings
            (0.24, 0.04, 0.25, 3, 1), (0.28, 0.08, 0.46, 7, 2),   # centre-left buildings
            (0.35, 0.06, 0.38, 5, 1), (0.40, 0.10, 0.62, 9, 2),   # tallest centre building
            (0.50, 0.07, 0.32, 4, 2), (0.56, 0.05, 0.44, 6, 1),   # centre-right buildings
            (0.61, 0.09, 0.52, 7, 2), (0.70, 0.06, 0.37, 5, 2),   # right-of-centre buildings
            (0.75, 0.04, 0.28, 4, 1), (0.79, 0.08, 0.48, 7, 2),   # far-right buildings
            (0.87, 0.07, 0.42, 6, 1), (0.93, 0.07, 0.33, 5, 2),   # right edge buildings
        ]

        p.setPen(Qt.NoPen)   # removes the outline pen so buildings are drawn as clean filled rectangles
        for bx_f, bw_f, bh_f, floors, win_cols in buildings:
            bx = int(bx_f * w)   # converts fractional start x to pixel x coordinate
            bw = max(10, int(bw_f * w))   # converts fractional width to pixels, minimum 10px so tiny buildings are still visible
            bh = int(bh_f * h * 0.50)   # building height is a fraction of 50% of the panel height so skyline doesn't overpower the view
            by = ground - bh   # calculates the top-left y coordinate (ground minus building height)

            p.setBrush(sil_col)
            p.drawRect(bx, by, bw, bh)   # draws the main building rectangle in the silhouette colour
            p.setBrush(roof_col)
            p.drawRect(bx - 1, by, bw + 2, 3)   # draws a slightly wider and lighter 3px roof strip at the very top of the building

            win_w = max(3, bw // (win_cols * 2 + 1))   # calculates window width by dividing building width by the number of windows and gaps
            win_h = max(4, 12)   # window height is at least 4px, normally 12px tall
            for fl in range(floors):
                wy1 = by + 8 + fl * (win_h + 7)   # top y of this floor's windows (8px from roof + floor index × window+gap height)
                wy2 = wy1 + win_h
                if wy2 >= ground - 6:
                    break   # stops drawing windows when they would overlap the ground line
                for ci in range(win_cols):
                    spacing = bw // (win_cols + 1)   # distributes windows evenly across the building width
                    wx1 = bx + spacing * (ci + 1) - win_w // 2   # centres each window within its column
                    wc = win_lit if rng.random() > 0.30 else win_dark   # randomly chooses lit (70% chance) or dark (30% chance) window
                    p.setBrush(wc)
                    p.drawRect(wx1, wy1, win_w, win_h)   # draws the window rectangle in the chosen lit/dark colour

        # Ground glow — paints a 12-layer blue gradient strip along the very bottom to simulate reflected city light
        for i in range(12):
            gc = QColor(_blend("#3060C0", self._GRAD_BOT, i / 12))   # each layer is a progressively darker blend of blue toward the background
            gc.setAlpha(120)   # sets the glow to mostly transparent (alpha 120) so it subtly illuminates the ground
            p.setBrush(gc)
            p.drawRect(0, ground - i, w, 1)   # draws each glow layer as a 1px tall line at increasing distances from the bottom

    def _draw_brand(self, p: QPainter, w: int, h: int):
        yc = int(h * 0.22)   # vertical centre for the brand text block, placed at 22% from the top of the panel
        # Title
        p.setPen(QColor("#FFFFFF"))   # sets the pen to white for the main brand title
        p.setFont(QFont("Segoe UI", 40, QFont.Bold))   # uses a massive 40pt bold font so 'PARAGON' dominates the left panel
        p.drawText(QRectF(0, yc - 28, w, 56), Qt.AlignCenter, "PARAGON")   # draws the 'PARAGON' title centred horizontally at the brand position

        # Subtitle
        p.setPen(QColor("#8CA8D8"))   # sets the pen to a muted blue-grey for the subtitle text
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))   # uses small 9pt bold with letter-spaced caps for the subtitle
        p.drawText(QRectF(0, yc + 30, w, 20), Qt.AlignCenter,
                   "A P A R T M E N T   M A N A G E M E N T")   # draws the subtitle with extra letter spacing below the main title

        # Tagline
        p.setPen(QColor("#5E80B0"))   # sets the pen to a darker blue-grey for the tagline, making it less prominent than the subtitle
        p.setFont(QFont("Segoe UI", 9))   # uses regular 9pt (non-bold) for the tagline
        p.drawText(QRectF(0, yc + 60, w, 20), Qt.AlignCenter,
                   "Smart  ·  Efficient  ·  Professional")   # draws the three-word tagline separated by dots, below the subtitle

    def _draw_logo(self, p: QPainter, w: int, h: int):
        cx = w // 2   # horizontal centre of the panel for centering the logo
        cy = int(h * 0.08)   # places the logo at 8% from the top, above the brand text block
        pulse = 2.5 * math.sin(self.logo_tick * 0.07)   # creates a 2.5px pulsing size oscillation using a sine wave keyed to the animation tick
        r = 32 + pulse   # the logo ring radius oscillates between ~29.5px and ~34.5px creating a breathing effect

        # Outer glow
        glow = QColor(_blend("#4361EE", self._GRAD_TOP, 0.60))   # blends the indigo accent 60% toward the background for a faint outer glow
        glow.setAlpha(60)   # sets the glow to mostly transparent (alpha 60) so it softly illuminates the area around the logo
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QRectF(cx - r - 18, cy - r - 18, (r+18)*2, (r+18)*2))   # draws the glow as a circle 18px larger than the ring on each side

        # Ring
        p.setPen(QPen(QColor("#6B8DF0"), 2))   # sets a 2px light-blue pen for the outer ring outline
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx - r, cy - r, r*2, r*2))   # draws the thin pulsing outer ring

        # Inner disc
        inner_c = QColor(_blend("#4361EE", self._GRAD_TOP, 0.48))   # blends the indigo accent 48% toward the dark background for the sphere fill
        p.setPen(Qt.NoPen)
        p.setBrush(inner_c)
        p.drawEllipse(QRectF(cx - r + 8, cy - r + 8, (r-8)*2, (r-8)*2))   # draws the filled inner disc 8px inside the ring on each side

        # "P" — clean bold font
        p.setPen(QColor("#FFFFFF"))   # sets the pen to white for the 'P' letter drawn in the centre of the logo
        p.setFont(QFont("Segoe UI", int(r * 0.72), QFont.Bold))   # scales the 'P' font to 72% of the ring radius so it fits neatly inside
        p.drawText(QRectF(cx - r, cy - r, r * 2, r * 2), Qt.AlignCenter, "P")   # draws the 'P' letter centred inside the logo circle


# ──────────────────────────────────────────────────────────
# SMALL HELPER WIDGETS
# ──────────────────────────────────────────────────────────
class _AnimatedLogoWidget(QWidget):
    """3D glossy animated logo for the login right panel — rotating ring + shimmer."""
    clicked = Signal()   # emitted when the user clicks the logo to request a theme toggle

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0         # current rotation angle (0–360) for the conical gradient ring
        self._pulse = 0.0       # glow pulse progress (0.0–1.0) for the glass highlight oscillation
        self._pulse_dir = 1     # direction of the pulse: 1 = growing, -1 = shrinking
        self._hover = False     # tracks whether the mouse is hovering over the logo
        self.setFixedSize(80, 80)   # locks the logo widget to an 80×80 pixel square
        self.setCursor(Qt.PointingHandCursor)   # shows a hand cursor when hovering to hint it is clickable
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)   # connects the timer to the _tick method that advances the animation each frame
        self._timer.start(30)   # fires every 30ms (~33fps) to animate the spinning ring and pulsing highlight

    def _tick(self):
        self._angle = (self._angle + 4) % 360   # rotates the ring 4° per tick, wrapping back to 0 after a full rotation
        self._pulse += 0.05 * self._pulse_dir   # increments or decrements the pulse by 5% each tick
        if self._pulse >= 1.0:
            self._pulse = 1.0; self._pulse_dir = -1   # reverses pulse direction at maximum brightness
        elif self._pulse <= 0.0:
            self._pulse = 0.0; self._pulse_dir = 1    # reverses pulse direction at minimum brightness
        self.update()   # requests a repaint so the new angle and pulse value are drawn

    def enterEvent(self, e):
        self._hover = True; self.update()   # sets the hover flag and immediately repaints to switch to the purple hover colour scheme

    def leaveEvent(self, e):
        self._hover = False; self.update()   # clears the hover flag and repaints to switch back to the normal blue colour scheme

    def mousePressEvent(self, e):
        self.clicked.emit()   # emits the clicked signal when the user presses on the logo (triggers theme toggle)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)   # enables smooth anti-aliased rendering for the circular logo
        s = min(self.width(), self.height())   # uses the smaller of width/height so the logo is always a perfect circle
        cx, cy = s / 2, s / 2   # calculates the centre point of the logo
        r = s / 2 - 4   # radius inset by 4px from the edge to leave room for the ring stroke

        # ── Outer rainbow spinning ring ──
        ring_grad = QConicalGradient(cx, cy, self._angle)   # creates a conical (pie-sweep) gradient centred on the logo, starting from the current angle
        if self._hover:
            # Hover state: rainbow colours for the spinning ring
            ring_grad.setColorAt(0.00, QColor("#FF6FD8"))   # hot pink at 0°
            ring_grad.setColorAt(0.25, QColor("#6366F1"))   # indigo at 90°
            ring_grad.setColorAt(0.50, QColor("#06B6D4"))   # cyan at 180°
            ring_grad.setColorAt(0.75, QColor("#10B981"))   # green at 270°
            ring_grad.setColorAt(1.00, QColor("#FF6FD8"))   # returns to pink at 360°
        else:
            # Normal state: blue-to-violet-to-cyan gradient
            ring_grad.setColorAt(0.00, QColor("#4361EE"))   # indigo blue at the start
            ring_grad.setColorAt(0.40, QColor("#8B5CF6"))   # violet at 40%
            ring_grad.setColorAt(0.70, QColor("#06B6D4"))   # cyan at 70%
            ring_grad.setColorAt(1.00, QColor("#4361EE"))   # back to indigo at 360°
        p.setPen(QPen(ring_grad, 4))   # applies the spinning gradient as a 4px pen for the outer ring
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(2, 2, s - 4, s - 4))   # draws the spinning rainbow/gradient ring 2px inside the widget edges

        # ── Sphere body ──
        sphere = QRadialGradient(cx - r * 0.3, cy - r * 0.35, r * 1.1)   # off-centre origin creates a 3D light-source effect (top-left)
        if self._hover:
            # Hover: purple colour scheme for the sphere
            sphere.setColorAt(0.0, QColor(lerp_color("#A78BFA", "#FFFFFF", 0.3)))   # bright purple-white centre
            sphere.setColorAt(0.4, QColor("#7C3AED"))   # deep purple at 40%
            sphere.setColorAt(1.0, QColor("#1E1B4B"))   # very dark indigo at the edge
        else:
            # Normal: blue colour scheme for the sphere
            sphere.setColorAt(0.0, QColor(lerp_color("#4361EE", "#FFFFFF", 0.4)))   # bright blue-white centre (40% white blend)
            sphere.setColorAt(0.4, QColor(lerp_color("#4361EE", "#000033", 0.3)))   # slightly darkened blue at 40% radius
            sphere.setColorAt(1.0, QColor("#0A0A2A"))   # near-black dark navy at the sphere edge
        p.setPen(Qt.NoPen)
        p.setBrush(sphere)
        p.drawEllipse(QRectF(6, 6, s - 12, s - 12))   # draws the sphere body 6px inside the outer ring

        # ── Glass specular highlight ──
        gloss = QRadialGradient(cx - r * 0.28, cy - r * 0.38, r * 0.52)   # top-left off-centre origin to simulate light reflection
        gloss_a = int(190 + self._pulse * 55)   # alpha oscillates between 190 and 245 with the pulse for a shimmering effect
        gloss.setColorAt(0.0, QColor(255, 255, 255, gloss_a))   # bright white at the highlight centre
        gloss.setColorAt(0.6, QColor(255, 255, 255, 55))   # fading white at 60% of the highlight radius
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))   # fully transparent at the highlight edge
        p.setBrush(gloss)
        p.drawEllipse(QRectF(10, 10, (s - 20) * 0.68, (s - 20) * 0.50))   # draws the glass highlight in the top-left 68%×50% of the sphere area

        # ── Inner rim light ──
        rim = QRadialGradient(cx + r * 0.48, cy + r * 0.48, r * 0.38)   # off-centre to the bottom-right to simulate reflected light from below
        rim.setColorAt(0.0, QColor(100, 150, 255, 90))   # soft blue-white glow at the rim centre (alpha 90, partially transparent)
        rim.setColorAt(1.0, QColor(100, 150, 255, 0))    # fades to fully transparent at the edge of the rim glow
        p.setBrush(rim)
        p.drawEllipse(QRectF(s * 0.48, s * 0.48, s * 0.50, s * 0.50))   # draws the rim light in the bottom-right quadrant of the sphere

        # ── P letter — clean bold font ──
        p.setPen(QColor("#FFFFFF"))   # makes the 'P' letter bright white for maximum contrast against the dark sphere
        p.setFont(QFont("Segoe UI", int(s * 0.32), QFont.Bold))   # scales the 'P' to 32% of the widget size so it fills the sphere neatly
        p.drawText(QRectF(0, 0, s, s), Qt.AlignCenter, "P")   # centres 'P' both horizontally and vertically within the sphere
        p.end()

    def stop(self):
        self._timer.stop()   # stops the spinning animation when the logo widget is no longer needed


class _GradientBar(QWidget):
    def __init__(self, c1, c2, parent=None):
        super().__init__(parent)
        self._c1, self._c2 = c1, c2   # stores the two gradient colours (left colour and right colour) for use in paintEvent

    def paintEvent(self, event):
        p = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), 0)   # creates a horizontal gradient from left edge to right edge
        grad.setColorAt(0.0, QColor(self._c1))   # starts with the first colour (e.g. indigo accent) on the left
        grad.setColorAt(1.0, QColor(self._c2))   # ends with the second colour (e.g. teal/violet accent2) on the right
        p.fillRect(0, 0, self.width(), self.height(), grad)   # paints the entire widget area with the left-to-right gradient
        p.end()
