# ============================================================
# PAMS — main_app.py
# Primary application shell: sidebar + topbar + content area
# Professional Corporate SaaS layout  (PySide6)
# ============================================================
from __future__ import annotations
import traceback
from typing import Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QSizePolicy, QLineEdit, QSpacerItem,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QRectF, Signal, QTimer, QPointF
from PySide6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QConicalGradient,
    QRadialGradient, QPen, QPixmap, QIcon, QPainterPath,
)
import math

from .theme import (
    PALETTE as P, FONTS as F, DIMS as D,
    NAV_ITEMS, ROLE_COLORS, lerp_color, is_dark_theme,
)
from . import theme as _theme  # needed to read CURRENT_THEME_IDX at runtime
from .widgets import qfont, Toast, _blend, draw_key_icon


def _readable_on(hex_color: str) -> str:
    """Return #FFFFFF or #1A1A2E whichever has better contrast against hex_color."""
    c = hex_color.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    # Relative luminance (sRGB)
    def lin(v): x = v / 255; return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    lum = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    return "#FFFFFF" if lum < 0.35 else "#1A1A2E"


# ──────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────
class Sidebar(QWidget):
    navigate = Signal(str)
    theme_requested = Signal()

    def __init__(self, user: dict, on_navigate: Callable, on_logout: Callable, parent=None):
        super().__init__(parent)
        self._user = user
        self._on_nav = on_navigate
        self._on_logout = on_logout
        self._nav_items = NAV_ITEMS.get(user["role"], [])
        self._active_key = "dashboard"
        self._item_widgets: list[_NavItem] = []

        _base = ROLE_COLORS.get(user["role"], P.bg_sidebar)
        self._accent = _base
        _dark = is_dark_theme()
        if _dark:
            self._bg        = lerp_color(_base, "#000000", 0.78)
            self._bg_top    = lerp_color(_base, "#000000", 0.70)
            self._nav_text  = "#E8ECF4"
            self._nav_active = lerp_color(_base, "#FFFFFF", 0.22)
            self._nav_hover  = lerp_color(_base, "#FFFFFF", 0.12)
        else:
            self._bg        = lerp_color(_base, "#FFFFFF", 0.86)
            self._bg_top    = lerp_color(_base, "#FFFFFF", 0.78)
            self._nav_text  = "#1A1A2E"
            self._nav_active = lerp_color(_base, "#FFFFFF", 0.55)
            self._nav_hover  = lerp_color(_base, "#FFFFFF", 0.70)
        self._glow = _dark
        self._nav_text_dim = lerp_color(self._nav_text, self._bg, 0.45)
        self._accent_col = lerp_color(_base, P.accent, 0.35) if _dark else _base

        self.setFixedWidth(D.sidebar_w)
        self._build()

    def paintEvent(self, event):
        """Draw a subtle vertical gradient for depth instead of a flat background."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(self._bg_top))
        grad.setColorAt(0.4, QColor(self._bg))
        grad.setColorAt(1.0, QColor(lerp_color(self._bg, "#000000", 0.08)))
        p.fillRect(0, 0, w, h, grad)
        p.end()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Brand strip ──
        brand = QWidget()
        brand.setStyleSheet("background: transparent;")
        bl = QHBoxLayout(brand)
        bl.setContentsMargins(16, D.pad_lg, 12, D.pad_md)

        # Logo circle — now fully animated 3D glossy
        _logo_color = lerp_color(self._accent, P.accent, 0.40)
        logo = _LogoCircle(_logo_color)
        logo.setFixedSize(56, 56)
        logo.theme_clicked.connect(self.theme_requested.emit)
        bl.addWidget(logo)

        # Title block
        title_w = QWidget()
        title_w.setStyleSheet("background: transparent;")
        tl = QVBoxLayout(title_w)
        tl.setContentsMargins(12, 0, 0, 0)
        tl.setSpacing(1)
        t1 = QLabel("PARAGON")
        t1.setFont(QFont("Segoe UI", 17, QFont.Bold))
        t1.setStyleSheet(f"color: {self._nav_text};")
        tl.addWidget(t1)
        t2 = QLabel("Management Suite")
        t2.setFont(QFont("Segoe UI", 9))
        t2.setStyleSheet(f"color: {self._nav_text_dim};")
        tl.addWidget(t2)
        bl.addWidget(title_w, 1)
        lay.addWidget(brand)

        # ── Accent divider line ──
        div = _AccentDivider(self._accent_col, self._bg)
        div.setFixedHeight(2)
        lay.addWidget(div)
        lay.addSpacing(6)

        # ── Nav section header ──
        nav_hdr = QLabel("  NAVIGATION")
        nav_hdr.setFont(QFont("Segoe UI", 8, QFont.Bold))
        nav_hdr.setStyleSheet(
            f"color: {self._nav_text_dim}; "
            f"background: transparent; padding: 6px 0 6px {D.pad_md}px;")
        lay.addWidget(nav_hdr)

        # ── Nav items ──
        nav_area = QWidget()
        nav_area.setStyleSheet("background: transparent;")
        nl = QVBoxLayout(nav_area)
        nl.setContentsMargins(10, 0, 10, 0)
        nl.setSpacing(4)
        for icon, label, key in self._nav_items:
            item = _NavItem(icon, label, key,
                            bg=self._bg,
                            nav_text=self._nav_text,
                            nav_active=self._nav_active,
                            nav_hover=self._nav_hover,
                            accent_color=self._accent_col,
                            glow=self._glow,
                            on_click=self._navigate)
            nl.addWidget(item)
            self._item_widgets.append(item)
        lay.addWidget(nav_area)

        if self._item_widgets:
            self._set_active("dashboard")

        # ── Spacer ──
        lay.addStretch(1)

        # ── Location badge ──
        if self._user.get("location"):
            loc = QLabel(f"  Location: {self._user['location']}")
            loc.setFont(QFont("Segoe UI", 10))
            loc.setStyleSheet(
                f"color: {self._nav_text}; background: transparent; padding: 4px {D.pad_md}px;")
            lay.addWidget(loc)

        # ── Bottom divider ──
        div2 = _AccentDivider(self._accent_col, self._bg)
        div2.setFixedHeight(2)
        lay.addWidget(div2)

        # ── User profile area ──
        profile = QWidget()
        profile.setStyleSheet("background: transparent;")
        pl = QHBoxLayout(profile)
        pl.setContentsMargins(D.pad_sm + 2, D.pad_sm, D.pad_sm, D.pad_sm + 2)

        # Avatar — larger with accent glow
        initials = "".join(p[0] for p in self._user["full_name"].split()[:2])
        avatar = _AvatarCircle(initials, self._accent_col)
        avatar.setFixedSize(48, 48)
        pl.addWidget(avatar)

        # Info
        info = QWidget()
        info.setStyleSheet("background: transparent;")
        il = QVBoxLayout(info)
        il.setContentsMargins(10, 0, 0, 0)
        il.setSpacing(1)
        nm = QLabel(self._user["full_name"])
        nm.setFont(QFont("Segoe UI", 10, QFont.Bold))
        nm.setStyleSheet(f"color: {self._nav_text};")
        nm.setMaximumWidth(D.sidebar_w - 100)
        nm.setMinimumWidth(0)
        nm.setSizePolicy(nm.sizePolicy().horizontalPolicy(), nm.sizePolicy().verticalPolicy())
        from PySide6.QtCore import Qt as _Qt
        nm.setWordWrap(False)
        fm = nm.fontMetrics()
        elided = fm.elidedText(self._user["full_name"], _Qt.ElideRight, D.sidebar_w - 104)
        nm.setText(elided)
        il.addWidget(nm)
        rl = QLabel(self._user["role"])
        rl.setFont(QFont("Segoe UI", 9))
        rl.setStyleSheet(f"color: {self._nav_text_dim};")
        il.addWidget(rl)
        pl.addWidget(info, 1)

        # Logout button — glossy pill with icon
        logout = QPushButton("⏻  Logout")
        logout.setFont(QFont("Segoe UI", 10, QFont.Bold))
        logout.setCursor(Qt.PointingHandCursor)
        logout.setFixedSize(100, 36)
        logout.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {lerp_color(self._bg, "#300010", 0.35)},
                    stop:1 {lerp_color(self._bg, "#000000", 0.25)});
                color: {lerp_color(self._nav_text, P.danger, 0.4)};
                border: 1.5px solid {lerp_color(P.danger, self._bg, 0.65)};
                border-radius: 18px;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {lerp_color(P.danger, "#000000", 0.55)},
                    stop:1 {lerp_color(P.danger, "#000000", 0.75)});
                color: #FFFFFF;
                border: 1.5px solid {lerp_color(P.danger, "#FFFFFF", 0.25)};
            }}
            QPushButton:pressed {{
                background: {lerp_color(P.danger, "#000000", 0.40)};
                color: #FFFFFF;
            }}
        """)
        logout.clicked.connect(self._on_logout)
        pl.addWidget(logout)

        lay.addWidget(profile)

    def _navigate(self, key: str):
        self._set_active(key)
        self._on_nav(key)

    def _set_active(self, key: str):
        self._active_key = key
        for item in self._item_widgets:
            item.set_active(item._key == key)

    def refresh_active(self, key: str):
        self._set_active(key)


# ──────────────────────────────────────────────────────────
# NAV ITEM
# ──────────────────────────────────────────────────────────
class _NavItem(QWidget):
    def __init__(self, icon, label, key, bg, nav_text, nav_active, nav_hover,
                 on_click, accent_color=None, glow=False, parent=None):
        super().__init__(parent)
        self._key = key
        self._on_click = on_click
        self._active = False
        self._hover = False

        self._bg_col = bg
        self._nav_text = nav_text
        self._nav_active = nav_active
        self._nav_hover = nav_hover
        self._icon = icon
        self._label = label
        self._glow = glow
        self._accent_color = accent_color or nav_active
        self._text_on_hl = _readable_on(bg)

        self.setFixedHeight(52)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent;")

    def set_active(self, active: bool):
        self._active = active
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def mousePressEvent(self, event):
        self._on_click(self._key)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = QRectF(3, 2, w - 6, h - 4)

        if self._active:
            # Glossy gradient active background
            p.setPen(Qt.NoPen)
            active_grad = QLinearGradient(0, 0, w, h)
            active_grad.setColorAt(0.0, QColor(lerp_color(self._accent_color, "#FFFFFF", 0.18)))
            active_grad.setColorAt(0.5, QColor(self._nav_active))
            active_grad.setColorAt(1.0, QColor(lerp_color(self._nav_active, "#000000", 0.10)))
            p.setBrush(active_grad)
            p.drawRoundedRect(r, 14, 14)

            # Top gloss sheen
            gloss_rect = QRectF(4, 3, w - 8, (h - 6) * 0.45)
            gloss_grad = QLinearGradient(0, gloss_rect.top(), 0, gloss_rect.bottom())
            gloss_grad.setColorAt(0.0, QColor(255, 255, 255, 38))
            gloss_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(gloss_grad)
            p.drawRoundedRect(gloss_rect, 12, 12)

            # Left indicator bar — thick vibrant glowing
            bar_grad = QLinearGradient(0, 8, 0, h - 8)
            bar_grad.setColorAt(0.0, QColor(lerp_color(self._accent_color, "#FFFFFF", 0.60)))
            bar_grad.setColorAt(0.5, QColor(self._accent_color))
            bar_grad.setColorAt(1.0, QColor(lerp_color(self._accent_color, "#000000", 0.30)))
            p.setBrush(bar_grad)
            p.drawRoundedRect(QRectF(3, 8, 5, h - 16), 3, 3)

            # Left bar outer glow
            glow_col = QColor(self._accent_color)
            glow_col.setAlpha(40)
            p.setBrush(glow_col)
            p.drawRoundedRect(QRectF(1, 5, 9, h - 10), 4, 4)

            text_col = QColor(self._text_on_hl)

        elif self._hover:
            p.setPen(Qt.NoPen)
            hover_grad = QLinearGradient(0, 0, w, h)
            hover_grad.setColorAt(0.0, QColor(lerp_color(self._nav_hover, "#FFFFFF", 0.08)))
            hover_grad.setColorAt(1.0, QColor(self._nav_hover))
            p.setBrush(hover_grad)
            p.drawRoundedRect(r, 14, 14)
            text_col = QColor(self._text_on_hl)
        else:
            text_col = QColor(self._nav_text)

        # Custom vector icon — drawn by key, no emoji/text
        icon_cx = 30.0
        icon_cy = h / 2
        icon_size = h * 0.36
        draw_key_icon(p, self._key, icon_cx, icon_cy, icon_size, text_col)

        # Label text
        font = QFont("Segoe UI", 11, QFont.Bold if self._active else QFont.Normal)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 0.3 if self._active else 0)
        p.setFont(font)
        label_rect = QRectF(56, 0, w - 62, h)
        p.setPen(text_col)
        p.drawText(label_rect, Qt.AlignVCenter | Qt.AlignLeft, self._label)
        p.end()


# ──────────────────────────────────────────────────────────
# TOP BAR
# ──────────────────────────────────────────────────────────
class TopBar(QWidget):
    search_triggered = Signal(str)      # emits the search query text
    notification_clicked = Signal()     # click → navigate to payments

    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self._user = user
        self.setFixedHeight(D.topbar_h)
        self.setObjectName("topbar")
        self.setStyleSheet(f"""
            #topbar {{
                background-color: {P.bg_surface};
                border-bottom: 1px solid {P.border};
            }}
            #topbar QLabel  {{ background: transparent; }}
            #topbar QWidget {{ background: transparent; }}
        """)
        self._late_count = 0
        self._build()
        self._refresh_notifications()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(D.pad_lg, 0, D.pad_lg, 0)
        lay.setSpacing(0)

        # ── Left: breadcrumb ──
        crumb_lbl = QLabel("PARAGON")
        crumb_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        crumb_lbl.setStyleSheet(f"color: {P.accent}; letter-spacing: 1px; background: transparent;")
        lay.addWidget(crumb_lbl)

        sep = QLabel("  /  ")
        sep.setFont(QFont("Segoe UI", 11))
        sep.setStyleSheet(f"color: {P.text_muted}; background: transparent;")
        lay.addWidget(sep)

        self._title_lbl = QLabel("Dashboard")
        self._title_lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self._title_lbl.setStyleSheet(f"color: {P.text_primary}; background: transparent;")
        lay.addWidget(self._title_lbl)

        # ── Center: search bar (FUNCTIONAL) ──
        lay.addStretch(1)

        # Search container with built-in icon
        self._search = QLineEdit()
        self._search.setPlaceholderText("   Search tenants, apartments…")
        self._search.setFixedWidth(320)
        self._search.setFixedHeight(40)

        # Custom-drawn vector icon for a sleek, big-company search look
        def _create_search_icon():
            pix = QPixmap(24, 24)
            pix.fill(Qt.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(QColor(P.text_muted), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawEllipse(5, 5, 8, 8)
            p.drawLine(11, 11, 17, 17)
            p.end()
            return QIcon(pix)

        search_action = self._search.addAction(
            _create_search_icon(),
            QLineEdit.ActionPosition.LeadingPosition,
        )

        self._search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {P.bg_card};
                border: 1.5px solid {P.border};
                border-radius: 20px;
                padding: 0 18px 0 8px;
                color: {P.text_primary};
                font-size: 13px;
                font-family: "Segoe UI";
            }}
            QLineEdit:focus {{
                border: 1.5px solid {P.accent};
                background-color: {P.bg_input};
            }}
        """)
        self._search.returnPressed.connect(self._on_search)
        lay.addWidget(self._search)
        lay.addStretch(1)

        # ── Right: user name (colored by role) ──
        role_color = ROLE_COLORS.get(self._user["role"], P.accent)
        name_lbl = QLabel(self._user["full_name"])
        name_lbl.setFont(qfont(F.body_bold))
        name_lbl.setStyleSheet(f"color: {role_color}; background: transparent;")
        lay.addWidget(name_lbl)
        lay.addSpacing(10)

        # ── Role badge ──
        badge = QPushButton(self._user["role"])
        badge.setEnabled(False)
        badge.setFont(qfont(F.small_bold))
        badge.setFixedHeight(30)
        badge.setStyleSheet(f"""
            QPushButton {{
                background-color: {role_color};
                color: #FFFFFF;
                border: none;
                border-radius: 15px;
                padding: 0 16px;
                font-weight: bold;
            }}
        """)
        lay.addWidget(badge)
        lay.addSpacing(12)

        # ── Notification bell (FUNCTIONAL) ──
        self._bell_btn = QPushButton()
        self._bell_btn.setCursor(Qt.PointingHandCursor)
        self._bell_btn.setFixedSize(42, 42)
        self._bell_btn.clicked.connect(self.notification_clicked.emit)
        self._bell_btn.setToolTip("Late payments — click to view")
        self._update_bell_style()
        lay.addWidget(self._bell_btn)

    def _on_search(self):
        """Emit the search query when user presses Enter."""
        q = self._search.text().strip()
        if q:
            self.search_triggered.emit(q)

    def _refresh_notifications(self):
        """Query DB for late payment count and update the bell badge."""
        try:
            from .. import database as db
            payments = db.get_all_payments(location=self._user.get("location"))
            self._late_count = sum(
                1 for p in payments
                if p.get("status") in ("Overdue", "Late", "Pending")
            )
        except Exception:
            self._late_count = 0
        self._update_bell_style()

    def _update_bell_style(self):
        """Style the bell button with a red badge count if there are late payments."""
        count = self._late_count
        if count > 0:
            badge_text = str(count) if count < 100 else "99+"
            self._bell_btn.setText(f"🔔 {badge_text}")
            self._bell_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {lerp_color(P.danger, P.bg_surface, 0.85)};
                    color: {P.danger};
                    border: 1.5px solid {lerp_color(P.danger, P.bg_surface, 0.50)};
                    border-radius: 21px;
                    font: bold 11px "Segoe UI";
                    padding: 0 4px;
                }}
                QPushButton:hover {{
                    background: {lerp_color(P.danger, P.bg_surface, 0.70)};
                    border-color: {P.danger};
                }}
            """)
        else:
            self._bell_btn.setText("🔔")
            self._bell_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {P.text_muted};
                    border: none;
                    font: 16px "Segoe UI";
                }}
                QPushButton:hover {{
                    color: {P.accent};
                }}
            """)

    def set_title(self, title: str):
        self._title_lbl.setText(title)
        # refresh notifications whenever we switch views
        self._refresh_notifications()


# ──────────────────────────────────────────────────────────
# MAIN APPLICATION SHELL
# ──────────────────────────────────────────────────────────
class MainApp(QWidget):
    """Sidebar + TopBar + scrollable content area."""

    theme_requested = Signal()

    VIEW_TITLES = {
        "dashboard":   "Dashboard",
        "tenants":     "Tenant Management",
        "apartments":  "Apartment Management",
        "payments":    "Payment & Billing",
        "maintenance": "Maintenance",
        "complaints":  "Complaints Management",
        "reports":     "Reports & Analytics",
        "users":       "User Management",
    }

    def __init__(self, user: dict, on_logout: Callable, initial_page: str = "dashboard", parent=None):
        super().__init__(parent)
        self._user = user
        self._on_logout = on_logout
        self._current_view = None
        self.setStyleSheet(f"background-color: {P.bg_surface};")
        self._build()
        self._navigate(initial_page)

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──
        self._sidebar = Sidebar(self._user,
                                on_navigate=self._navigate,
                                on_logout=self._logout)
        self._sidebar.theme_requested.connect(self.theme_requested.emit)
        root.addWidget(self._sidebar)

        # ── Body (topbar + content) ──
        body = QWidget()
        body.setStyleSheet(f"background-color: {P.bg_surface};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self._topbar = TopBar(self._user)
        self._topbar.search_triggered.connect(self._on_global_search)
        self._topbar.notification_clicked.connect(
            lambda: self._navigate("payments"))
        bl.addWidget(self._topbar)

        # ── Scrollable content ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {P.bg_surface};
                border: none;
            }}
        """)
        bl.addWidget(self._scroll, 1)
        root.addWidget(body, 1)

    # ──────────────────────────────────────────────────────
    # NAVIGATION
    # ──────────────────────────────────────────────────────
    def _navigate(self, key: str):
        self._topbar.set_title(self.VIEW_TITLES.get(key, key.title()))
        self._sidebar.refresh_active(key)

        # Create new content widget
        container = QWidget()
        container.setStyleSheet(f"background-color: {P.bg_surface};")
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        self._load_view(key, container, cl)
        self._scroll.setWidget(container)

    def _load_view(self, key: str, parent: QWidget, layout: QVBoxLayout):
        """Dynamically import and instantiate the requested view."""
        try:
            if key == "dashboard":
                from .views.dashboard_view import DashboardView
                layout.addWidget(DashboardView(self._user, parent))

            elif key == "tenants":
                from .views.tenant_view import TenantView
                layout.addWidget(TenantView(self._user, parent))

            elif key == "apartments":
                from .views.apartment_view import ApartmentView
                layout.addWidget(ApartmentView(self._user, parent))

            elif key == "payments":
                from .views.payment_view import PaymentView
                layout.addWidget(PaymentView(self._user, parent))

            elif key == "maintenance":
                from .views.maintenance_view import MaintenanceView
                layout.addWidget(MaintenanceView(self._user, parent))

            elif key == "complaints":
                from .views.complaint_view import ComplaintView
                layout.addWidget(ComplaintView(self._user, parent))

            elif key == "reports":
                from .views.report_view import ReportView
                layout.addWidget(ReportView(self._user, parent))

            elif key == "users":
                from .views.user_view import UserView
                layout.addWidget(UserView(self._user, parent))

        except Exception as exc:
            err = QLabel(f"Error loading view:\n{traceback.format_exc()}")
            err.setFont(QFont("Consolas", 10))
            err.setStyleSheet(f"color: {P.danger}; padding: 40px;")
            err.setWordWrap(True)
            layout.addWidget(err)

    # ──────────────────────────────────────────────────────
    # GLOBAL SEARCH
    # ──────────────────────────────────────────────────────
    def _on_global_search(self, query: str):
        """Navigate to tenants (most common search), pre-fill its search box."""
        self._navigate("tenants")
        # Try to pre-fill the tenant view's search box
        widget = self._scroll.widget()
        if widget:
            from .views.tenant_view import TenantView
            for child in widget.findChildren(TenantView):
                if hasattr(child, "_search"):
                    child._search.setText(query)
                break
        Toast(self.window(), f"Searching tenants for \"{query}\"…", kind="info")

    # ──────────────────────────────────────────────────────
    # TOAST / LOGOUT
    # ──────────────────────────────────────────────────────
    def show_toast(self, message: str, kind="success"):
        Toast(self.window(), message, kind)

    def _logout(self):
        self._on_logout()


# ──────────────────────────────────────────────────────────
# INTERNAL HELPER WIDGETS
# ──────────────────────────────────────────────────────────
class _LogoCircle(QWidget):
    """Animated 3D glossy logo — rotating gradient ring, inner glow, shimmer highlight."""
    theme_clicked = Signal()

    def __init__(self, bg, parent=None):
        super().__init__(parent)
        self._bg = bg
        self._hover = False
        self._angle = 0
        self._pulse = 0.0
        self._pulse_dir = 1
        self.setCursor(Qt.PointingHandCursor)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def _tick(self):
        self._angle = (self._angle + 3) % 360
        self._pulse += 0.04 * self._pulse_dir
        if self._pulse >= 1.0:
            self._pulse = 1.0; self._pulse_dir = -1
        elif self._pulse <= 0.0:
            self._pulse = 0.0; self._pulse_dir = 1
        self.update()

    def enterEvent(self, event):
        self._hover = True; self.update()

    def leaveEvent(self, event):
        self._hover = False; self.update()

    def mousePressEvent(self, event):
        self.theme_clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = min(self.width(), self.height())
        cx, cy = s / 2, s / 2
        r = s / 2 - 3

        # ── Outer rotating rainbow/gradient ring ──
        ring_grad = QConicalGradient(cx, cy, self._angle)
        if self._hover:
            ring_grad.setColorAt(0.00, QColor("#FF6FD8"))
            ring_grad.setColorAt(0.20, QColor("#6366F1"))
            ring_grad.setColorAt(0.40, QColor("#06B6D4"))
            ring_grad.setColorAt(0.60, QColor("#10B981"))
            ring_grad.setColorAt(0.80, QColor("#F59E0B"))
            ring_grad.setColorAt(1.00, QColor("#FF6FD8"))
        else:
            ring_grad.setColorAt(0.00, QColor(P.accent))
            ring_grad.setColorAt(0.33, QColor(lerp_color(P.accent, "#8B5CF6", 0.6)))
            ring_grad.setColorAt(0.66, QColor("#06B6D4"))
            ring_grad.setColorAt(1.00, QColor(P.accent))
        pen = QPen(ring_grad, 3.5)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(2, 2, s - 4, s - 4))

        # ── Deep glossy sphere background ──
        sphere_grad = QRadialGradient(cx - r * 0.28, cy - r * 0.32, r * 1.15)
        pulse_val = 0.12 + self._pulse * 0.10
        if self._hover:
            sphere_grad.setColorAt(0.0, QColor(lerp_color("#9B59F5", "#FFFFFF", 0.25)))
            sphere_grad.setColorAt(0.45, QColor("#5B21B6"))
            sphere_grad.setColorAt(0.80, QColor("#1E1B4B"))
            sphere_grad.setColorAt(1.0, QColor("#0C0A1E"))
        else:
            sphere_grad.setColorAt(0.0, QColor(lerp_color(P.accent, "#FFFFFF", 0.35)))
            sphere_grad.setColorAt(0.40, QColor(lerp_color(P.accent, "#000033", 0.35)))
            sphere_grad.setColorAt(0.75, QColor(lerp_color(P.accent, "#000022", 0.70)))
            sphere_grad.setColorAt(1.0, QColor(lerp_color(self._bg, "#000000", 0.30)))
        p.setPen(Qt.NoPen)
        p.setBrush(sphere_grad)
        p.drawEllipse(QRectF(5, 5, s - 10, s - 10))

        # ── Top-left specular highlight (gloss) ──
        gloss = QRadialGradient(cx - r * 0.30, cy - r * 0.40, r * 0.55)
        gloss_alpha = int(180 + self._pulse * 55)
        gloss.setColorAt(0.0, QColor(255, 255, 255, gloss_alpha))
        gloss.setColorAt(0.5, QColor(255, 255, 255, 60))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(gloss)
        p.drawEllipse(QRectF(8, 8, (s - 16) * 0.72, (s - 16) * 0.52))

        # ── Bottom-right subtle rim light ──
        rim = QRadialGradient(cx + r * 0.50, cy + r * 0.50, r * 0.40)
        rim.setColorAt(0.0, QColor(120, 160, 255, 80))
        rim.setColorAt(1.0, QColor(120, 160, 255, 0))
        p.setBrush(rim)
        p.drawEllipse(QRectF(s * 0.45, s * 0.45, s * 0.52, s * 0.52))

        # ── Pulsing outer glow ──
        glow_a = int(18 + self._pulse * 38)
        glow_col = QColor(P.accent if not self._hover else "#9B59F5")
        glow_col.setAlpha(glow_a)
        for glow_r in range(3):
            g2 = QColor(glow_col)
            g2.setAlpha(glow_a - glow_r * 6)
            p.setPen(QPen(g2, 2.5 - glow_r * 0.6))
            p.drawEllipse(QRectF(glow_r, glow_r, s - glow_r * 2, s - glow_r * 2))

        # ── P letter — clean bold font ──
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", int(s * 0.32), QFont.Bold))
        p.drawText(QRectF(0, 0, s, s), Qt.AlignCenter, "P")
        p.end()


class _AvatarCircle(QWidget):
    def __init__(self, initials, bg, parent=None):
        super().__init__(parent)
        self._initials = initials
        self._bg = bg

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = min(self.width(), self.height())
        cx, cy = s / 2, s / 2
        r = s / 2 - 2

        # Outer ring
        ring_col = QColor(lerp_color(self._bg, "#FFFFFF", 0.40))
        p.setPen(QPen(ring_col, 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(1, 1, s - 2, s - 2))

        # Body
        body_grad = QRadialGradient(cx - r * 0.25, cy - r * 0.3, r * 1.0)
        body_grad.setColorAt(0.0, QColor(lerp_color(self._bg, "#FFFFFF", 0.35)))
        body_grad.setColorAt(0.5, QColor(lerp_color(self._bg, "#FFFFFF", 0.18)))
        body_grad.setColorAt(1.0, QColor(lerp_color(self._bg, "#000000", 0.15)))
        p.setPen(Qt.NoPen)
        p.setBrush(body_grad)
        p.drawEllipse(QRectF(4, 4, s - 8, s - 8))

        # Gloss
        gloss = QRadialGradient(cx - r * 0.22, cy - r * 0.30, r * 0.50)
        gloss.setColorAt(0.0, QColor(255, 255, 255, 130))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(gloss)
        p.drawEllipse(QRectF(6, 6, (s - 12) * 0.65, (s - 12) * 0.48))

        # Initials
        accent = QColor(lerp_color(self._bg, "#FFFFFF", 0.85))
        p.setPen(accent)
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        p.drawText(QRectF(0, 0, s, s), Qt.AlignCenter, self._initials)
        p.end()


class _GradientDivider(QWidget):
    """Legacy divider — kept for backward compat but no longer used by Sidebar."""
    def __init__(self, bg, parent=None):
        super().__init__(parent)
        self._bg = bg
    def paintEvent(self, event):
        p = QPainter(self)
        w = self.width()
        mid = QColor(lerp_color(self._bg, "#FFFFFF", 0.20))
        edge = QColor(lerp_color(self._bg, "#FFFFFF", 0.04))
        for i in range(w):
            t = abs(i / max(1, w) - 0.5) * 2
            c = QColor(lerp_color(mid.name(), edge.name(), t))
            p.setPen(c)
            p.drawPoint(i, 0)
        p.end()


class _AccentDivider(QWidget):
    """A 2px divider that fades from accent color in the center to transparent."""
    def __init__(self, accent: str, bg: str, parent=None):
        super().__init__(parent)
        self._accent = accent
        self._bg = bg
    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        grad = QLinearGradient(0, 0, w, 0)
        edge = QColor(self._bg)
        mid = QColor(lerp_color(self._accent, "#FFFFFF", 0.30))
        grad.setColorAt(0.0, edge)
        grad.setColorAt(0.3, mid)
        grad.setColorAt(0.7, mid)
        grad.setColorAt(1.0, edge)
        p.fillRect(0, 0, w, h, grad)
        p.end()


class _TopBarBorder(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(3)
    def paintEvent(self, event):
        p = QPainter(self)
        w = self.width()
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(P.accent))
        grad.setColorAt(1.0, QColor(P.divider))
        p.fillRect(0, 0, w, 3, grad)
        p.end()
