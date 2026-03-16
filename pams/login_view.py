# ============================================================
# PAMS — login_view.py
# Modern split-panel animated login  (PySide6)
# ============================================================
from __future__ import annotations
import math, random
from typing import Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSizePolicy, QSpacerItem,
)
from PySide6.QtCore import Qt, QTimer, QRectF, Signal
from PySide6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QRadialGradient,
    QPen, QBrush, QIcon, QPixmap, QAction,
)

from .theme import PALETTE as P, FONTS as F, DIMS as D, lerp_color, is_dark_theme
from .widgets import qfont, styled_button, _blend, Toast
from . import theme as _theme
from . import database as db


def _make_eye_icon(visible: bool, color: str = "#9CA3AF") -> QIcon:
    """Create a clean eye / eye-slash icon as QIcon using QPainter."""
    size = 32
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.8)
    p.setPen(pen)

    cx, cy = size // 2, size // 2

    # Eye shape — almond
    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    path.moveTo(4, cy)
    path.cubicTo(8, cy - 8, 24, cy - 8, 28, cy)
    path.cubicTo(24, cy + 8, 8, cy + 8, 4, cy)
    p.drawPath(path)

    # Iris circle
    p.drawEllipse(QRectF(cx - 4, cy - 4, 8, 8))

    # Pupil dot
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(QRectF(cx - 2, cy - 2, 4, 4))

    # Slash line when hidden
    if not visible:
        pen.setWidth(2.2)
        p.setPen(pen)
        p.drawLine(6, 6, 26, 26)

    p.end()
    return QIcon(pixmap)


class LoginView(QWidget):
    """
    Full-screen modern login.
    Left  : animated gradient panel — floating orbs + city skyline.
    Right : clean white form panel.
    """
    theme_requested = Signal()

    _GRAD_TOP   = "#040C1C"
    _GRAD_MID   = "#0E2050"
    _GRAD_BOT   = "#020610"
    _ORB_COLORS = ["#4361EE", "#6366F1", "#3B49CC",
                    "#818CF8", "#4F5BD5", "#A5B4FC", "#8B5CF6",
                    "#7C3AED", "#6D28D9"]
    _ORB_COUNT  = 20

    DEMO_CREDS = [
        ("Admin",      "admin_bristol", "admin123"),
        ("Manager",    "manager",       "manager123"),
        ("Front Desk", "frontdesk1",    "front123"),
        ("Finance",    "finance1",      "finance123"),
        ("Maint.",     "maint1",        "maint123"),
    ]

    def __init__(self, on_login: Callable, parent=None):
        super().__init__(parent)
        self._on_login   = on_login
        self._pw_visible = False
        self._logo_tick  = 0
        self._init_orbs()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Left: animated canvas (56 %) ──
        self._left_panel = _AnimatedPanel(self)
        layout.addWidget(self._left_panel, 56)

        # ── Right: form panel (44 %) ──
        right = QWidget()
        right.setStyleSheet(f"background-color: {P.bg_card};")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addStretch(1)

        form = self._build_form()
        right_layout.addWidget(form, 0, Qt.AlignCenter)
        right_layout.addStretch(1)
        layout.addWidget(right, 44)

        # ── Start animation ──
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(45)

    # ──────────────────────────────────────────────────────
    # ORB DATA
    # ──────────────────────────────────────────────────────
    def _init_orbs(self):
        random.seed()
        self._orbs = []
        for _ in range(self._ORB_COUNT):
            self._orbs.append({
                "x": random.uniform(0.05, 0.93),
                "y": random.uniform(0.04, 0.82),
                "r": random.randint(28, 88),
                "vx": random.uniform(-0.00035, 0.00035),
                "vy": random.uniform(-0.00028, 0.00028),
                "col": random.choice(self._ORB_COLORS),
            })

    def _tick(self):
        for orb in self._orbs:
            orb["x"] += orb["vx"]
            orb["y"] += orb["vy"]
            if not 0.01 < orb["x"] < 0.99:
                orb["vx"] *= -1
            if not 0.01 < orb["y"] < 0.88:
                orb["vy"] *= -1
        self._logo_tick += 1
        self._left_panel.orbs = self._orbs
        self._left_panel.logo_tick = self._logo_tick
        self._left_panel.update()

    # ──────────────────────────────────────────────────────
    # RIGHT PANEL — FORM
    # ──────────────────────────────────────────────────────
    def _build_form(self) -> QWidget:
        form = QWidget()
        form.setFixedWidth(400)
        form.setStyleSheet(f"background-color: {P.bg_card};")
        fl = QVBoxLayout(form)
        fl.setSpacing(5)
        fl.setContentsMargins(14, 0, 14, 0)

        # Logo + brand
        logo = QPushButton("P")
        logo.setFixedSize(52, 52)
        logo.setFont(QFont("Segoe UI", 16, QFont.Bold))
        logo.setCursor(Qt.PointingHandCursor)
        logo.setToolTip("Click to change theme")
        logo.setStyleSheet(
            f"QPushButton {{ background-color: {_blend(P.accent, P.bg_card, 0.86)}; "
            f"color: {P.accent}; border-radius: 26px; "
            f"border: 2px solid {P.accent}; }}"
            f"QPushButton:hover {{ background-color: {P.accent}; color: #FFFFFF; }}")
        logo.clicked.connect(self.theme_requested.emit)
        fl.addWidget(logo, 0, Qt.AlignCenter)

        title = QLabel("PARAGON")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {P.accent2};")
        title.setAlignment(Qt.AlignCenter)
        fl.addWidget(title)

        sub = QLabel("Apartment Management System")
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet(f"color: {P.text_muted};")
        sub.setAlignment(Qt.AlignCenter)
        fl.addWidget(sub)

        # Accent bar
        bar = _GradientBar(P.accent, P.accent2)
        bar.setFixedHeight(4)
        fl.addWidget(bar)
        fl.addSpacing(10)

        # Welcome text
        wel = QLabel("Welcome back")
        wel.setFont(QFont("Segoe UI", 20, QFont.Bold))
        wel.setStyleSheet(f"color: {P.text_primary};")
        wel.setAlignment(Qt.AlignCenter)
        fl.addWidget(wel)
        wel2 = QLabel("Sign in to continue to your dashboard")
        wel2.setFont(QFont("Segoe UI", 11))
        wel2.setStyleSheet(f"color: {P.text_muted};")
        wel2.setAlignment(Qt.AlignCenter)
        fl.addWidget(wel2)
        fl.addSpacing(16)

        # Username
        fl.addWidget(self._field_label("USERNAME"))
        self._user_entry = QLineEdit()
        self._user_entry.setPlaceholderText("Enter your username")
        self._user_entry.setFixedHeight(D.input_h)
        fl.addWidget(self._user_entry)
        fl.addSpacing(6)

        # Password — eye icon INSIDE the input field
        fl.addWidget(self._field_label("PASSWORD"))
        self._pw_entry = QLineEdit()
        self._pw_entry.setPlaceholderText("Enter your password")
        self._pw_entry.setEchoMode(QLineEdit.Password)
        self._pw_entry.setFixedHeight(D.input_h)
        # Add eye toggle action inside the line edit (right side)
        eye_color = P.text_muted if not is_dark_theme() else "#8899B4"
        self._eye_action = QAction(_make_eye_icon(False, eye_color), "", self._pw_entry)
        self._eye_action.setToolTip("Show / hide password")
        self._pw_entry.addAction(self._eye_action, QLineEdit.TrailingPosition)
        self._eye_action.triggered.connect(self._toggle_pw)
        # Extra right padding so text doesn't overlap the icon
        self._pw_entry.setStyleSheet(
            self._pw_entry.styleSheet() + f"padding-right: 38px;")
        fl.addWidget(self._pw_entry)

        # Error label
        self._err_lbl = QLabel("")
        self._err_lbl.setFont(QFont("Segoe UI", 10))
        self._err_lbl.setStyleSheet(f"color: {P.danger};")
        self._err_lbl.setAlignment(Qt.AlignCenter)
        self._err_lbl.setWordWrap(True)
        fl.addWidget(self._err_lbl)

        # Sign in button — gradient style
        self._login_btn = QPushButton("SIGN  IN   ›")
        self._login_btn.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self._login_btn.setCursor(Qt.PointingHandCursor)
        self._login_btn.setFixedHeight(50)
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
        """)
        self._login_btn.clicked.connect(self._attempt_login)
        fl.addSpacing(10)
        fl.addWidget(self._login_btn)

        # Divider
        fl.addSpacing(6)
        div_row = QHBoxLayout()
        div_row.setContentsMargins(0, 0, 0, 0)
        sep1 = QFrame(); sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet(f"color: {P.divider};")
        sep1.setFixedHeight(1)
        div_row.addWidget(sep1, 1, Qt.AlignVCenter)
        or_lbl = QLabel("or")
        or_lbl.setFont(qfont(F.caption))
        or_lbl.setStyleSheet(f"color: {P.text_muted};")
        or_lbl.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        div_row.addWidget(or_lbl, 0, Qt.AlignVCenter)
        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"color: {P.divider};")
        sep2.setFixedHeight(1)
        div_row.addWidget(sep2, 1, Qt.AlignVCenter)
        fl.addLayout(div_row)

        # Demo chips
        fl.addSpacing(4)
        demo_lbl = QLabel("QUICK DEMO LOGIN")
        demo_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        demo_lbl.setStyleSheet(f"color: {P.text_muted};")
        demo_lbl.setAlignment(Qt.AlignCenter)
        fl.addWidget(demo_lbl)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)
        _dark = is_dark_theme()
        # In dark mode, use brighter chip colors so ALL chips are clearly visible
        if _dark:
            role_colors = {
                "Admin": "#818CF8", "Manager": "#94A3B8", "Front Desk": "#34D399",
                "Finance": "#FBBF24", "Maint.": "#F87171",
            }
        else:
            role_colors = {
                "Admin": P.accent, "Manager": "#475569", "Front Desk": P.success,
                "Finance": P.warning, "Maint.": P.danger,
            }
        for role, user, pw in self.DEMO_CREDS:
            color = role_colors.get(role, P.accent)
            chip = QPushButton(role)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setFont(QFont("Segoe UI", 10, QFont.Bold))
            if _dark:
                # Dark mode: semi-transparent background so chips glow
                bg = _blend(color, P.bg_card, 0.82)
                bg_hover = _blend(color, P.bg_card, 0.68)
                border_col = _blend(color, P.bg_card, 0.40)
            else:
                bg = _blend(color, P.bg_card, 0.89)
                bg_hover = _blend(color, P.bg_card, 0.78)
                border_col = _blend(color, P.bg_card, 0.45)
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
            """)
            chip.clicked.connect(
                lambda checked=False, u=user, p=pw: self._quick_demo(u, p))
            chips_row.addWidget(chip)
        fl.addLayout(chips_row)

        # Enter key binding
        self._user_entry.returnPressed.connect(self._attempt_login)
        self._pw_entry.returnPressed.connect(self._attempt_login)

        return form

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        lbl.setStyleSheet(f"color: {P.text_muted};")
        return lbl

    # ──────────────────────────────────────────────────────
    # ACTIONS
    # ──────────────────────────────────────────────────────
    def _toggle_pw(self):
        self._pw_visible = not self._pw_visible
        self._pw_entry.setEchoMode(
            QLineEdit.Normal if self._pw_visible else QLineEdit.Password)
        eye_color = P.text_muted if not is_dark_theme() else "#8899B4"
        self._eye_action.setIcon(_make_eye_icon(self._pw_visible, eye_color))

    def _attempt_login(self):
        username = self._user_entry.text().strip()
        password = self._pw_entry.text().strip()
        if not username or not password:
            self._err_lbl.setText("Please fill in both fields.")
            return
        self._err_lbl.setText("")
        self._login_btn.setText("Signing in...")
        self._login_btn.setEnabled(False)
        QTimer.singleShot(400, lambda: self._do_auth(username, password))

    def _do_auth(self, username: str, password: str):
        user = db.login(username, password)
        if user:
            self._login_btn.setText("✓  Success!")
            QTimer.singleShot(300, lambda: self._on_login(user))
        else:
            self._login_btn.setText("SIGN  IN   ›")
            self._login_btn.setEnabled(True)
            self._err_lbl.setText("Invalid username or password.")
            self._pw_entry.clear()

    def _quick_demo(self, username: str, password: str):
        self._user_entry.setText(username)
        self._pw_entry.setText(password)
        self._err_lbl.setText("")
        QTimer.singleShot(80, self._attempt_login)

    def destroy(self):
        self._timer.stop()


# ──────────────────────────────────────────────────────────
# ANIMATED LEFT PANEL  (QPainter-based)
# ──────────────────────────────────────────────────────────
class _AnimatedPanel(QWidget):
    """Left panel with gradient bg, floating orbs, star dots, city skyline, and brand text."""

    _GRAD_TOP = "#040C1C"
    _GRAD_MID = "#0E2050"
    _GRAD_BOT = "#020610"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.orbs = []
        self.logo_tick = 0
        self._buildings_rng = random.Random(99)  # stable windows
        # Pre-generate star positions
        self._stars = []
        rng = random.Random(42)
        for _ in range(60):
            self._stars.append({
                "x": rng.uniform(0.02, 0.98),
                "y": rng.uniform(0.02, 0.75),
                "r": rng.uniform(0.5, 2.0),
                "a": rng.randint(60, 200),
            })

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if w < 2:
            p.end(); return

        # ── Gradient background ──
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(self._GRAD_TOP))
        grad.setColorAt(0.50, QColor(self._GRAD_MID))
        grad.setColorAt(1.0, QColor(self._GRAD_BOT))
        p.fillRect(0, 0, w, h, grad)

        # ── Star dots ──
        for star in self._stars:
            sx = int(star["x"] * w)
            sy = int(star["y"] * h)
            sr = star["r"]
            sc = QColor("#FFFFFF")
            # Twinkle effect
            twinkle = int(star["a"] * (0.6 + 0.4 * abs(math.sin(self.logo_tick * 0.02 + star["x"] * 10))))
            sc.setAlpha(min(255, twinkle))
            p.setPen(Qt.NoPen)
            p.setBrush(sc)
            p.drawEllipse(QRectF(sx - sr, sy - sr, sr * 2, sr * 2))

        # ── Orbs ──
        p.setPen(Qt.NoPen)
        for orb in self.orbs:
            ax = orb["x"] * w
            ay = orb["y"] * h
            r = orb["r"]
            # Halo
            halo_col = QColor(_blend(orb["col"], self._GRAD_TOP, 0.68))
            halo_col.setAlpha(55)
            p.setBrush(halo_col)
            p.drawEllipse(QRectF(ax - r*2, ay - r*2, r*4, r*4))
            # Core
            core_col = QColor(_blend(orb["col"], self._GRAD_TOP, 0.45))
            core_col.setAlpha(95)
            p.setBrush(core_col)
            p.drawEllipse(QRectF(ax - r, ay - r, r*2, r*2))

        # ── City skyline ──
        self._draw_skyline(p, w, h)

        # ── Brand text ──
        self._draw_brand(p, w, h)

        # ── Animated logo ──
        self._draw_logo(p, w, h)

        p.end()

    def _draw_skyline(self, p: QPainter, w: int, h: int):
        rng = random.Random(99)
        ground = h
        sil_col = QColor(_blend("#FFFFFF", self._GRAD_BOT, 0.87))
        roof_col = QColor(_blend("#FFFFFF", self._GRAD_BOT, 0.82))
        win_lit  = QColor(_blend("#FFF0A0", self._GRAD_MID, 0.42))
        win_dark = QColor(_blend("#FFFFFF", self._GRAD_BOT, 0.78))

        buildings = [
            (0.00, 0.07, 0.27, 4, 2), (0.06, 0.05, 0.40, 6, 1),
            (0.10, 0.09, 0.56, 8, 2), (0.18, 0.07, 0.35, 5, 2),
            (0.24, 0.04, 0.25, 3, 1), (0.28, 0.08, 0.46, 7, 2),
            (0.35, 0.06, 0.38, 5, 1), (0.40, 0.10, 0.62, 9, 2),
            (0.50, 0.07, 0.32, 4, 2), (0.56, 0.05, 0.44, 6, 1),
            (0.61, 0.09, 0.52, 7, 2), (0.70, 0.06, 0.37, 5, 2),
            (0.75, 0.04, 0.28, 4, 1), (0.79, 0.08, 0.48, 7, 2),
            (0.87, 0.07, 0.42, 6, 1), (0.93, 0.07, 0.33, 5, 2),
        ]

        p.setPen(Qt.NoPen)
        for bx_f, bw_f, bh_f, floors, win_cols in buildings:
            bx = int(bx_f * w)
            bw = max(10, int(bw_f * w))
            bh = int(bh_f * h * 0.50)
            by = ground - bh

            p.setBrush(sil_col)
            p.drawRect(bx, by, bw, bh)
            p.setBrush(roof_col)
            p.drawRect(bx - 1, by, bw + 2, 3)

            win_w = max(3, bw // (win_cols * 2 + 1))
            win_h = max(4, 12)
            for fl in range(floors):
                wy1 = by + 8 + fl * (win_h + 7)
                wy2 = wy1 + win_h
                if wy2 >= ground - 6:
                    break
                for ci in range(win_cols):
                    spacing = bw // (win_cols + 1)
                    wx1 = bx + spacing * (ci + 1) - win_w // 2
                    wc = win_lit if rng.random() > 0.30 else win_dark
                    p.setBrush(wc)
                    p.drawRect(wx1, wy1, win_w, win_h)

        # Ground glow
        for i in range(12):
            gc = QColor(_blend("#3060C0", self._GRAD_BOT, i / 12))
            gc.setAlpha(120)
            p.setBrush(gc)
            p.drawRect(0, ground - i, w, 1)

    def _draw_brand(self, p: QPainter, w: int, h: int):
        yc = int(h * 0.22)
        # Title
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", 40, QFont.Bold))
        p.drawText(QRectF(0, yc - 28, w, 56), Qt.AlignCenter, "PARAGON")

        # Subtitle
        p.setPen(QColor("#8CA8D8"))
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        p.drawText(QRectF(0, yc + 30, w, 20), Qt.AlignCenter,
                   "A P A R T M E N T   M A N A G E M E N T")

        # Tagline
        p.setPen(QColor("#5E80B0"))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(QRectF(0, yc + 60, w, 20), Qt.AlignCenter,
                   "Smart  ·  Efficient  ·  Professional")

    def _draw_logo(self, p: QPainter, w: int, h: int):
        cx = w // 2
        cy = int(h * 0.08)
        pulse = 2.5 * math.sin(self.logo_tick * 0.07)
        r = 32 + pulse

        # Outer glow
        glow = QColor(_blend("#4361EE", self._GRAD_TOP, 0.60))
        glow.setAlpha(60)
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QRectF(cx - r - 18, cy - r - 18, (r+18)*2, (r+18)*2))

        # Ring
        p.setPen(QPen(QColor("#6B8DF0"), 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx - r, cy - r, r*2, r*2))

        # Inner disc
        inner_c = QColor(_blend("#4361EE", self._GRAD_TOP, 0.48))
        p.setPen(Qt.NoPen)
        p.setBrush(inner_c)
        p.drawEllipse(QRectF(cx - r + 8, cy - r + 8, (r-8)*2, (r-8)*2))

        # "P"
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", 19, QFont.Bold))
        p.drawText(QRectF(cx - r, cy - r, r*2, r*2), Qt.AlignCenter, "P")


# ──────────────────────────────────────────────────────────
# SMALL HELPER WIDGETS
# ──────────────────────────────────────────────────────────
class _GradientBar(QWidget):
    def __init__(self, c1, c2, parent=None):
        super().__init__(parent)
        self._c1, self._c2 = c1, c2

    def paintEvent(self, event):
        p = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0.0, QColor(self._c1))
        grad.setColorAt(1.0, QColor(self._c2))
        p.fillRect(0, 0, self.width(), self.height(), grad)
        p.end()
