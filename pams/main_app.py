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
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QPen, QPixmap, QIcon,
)

from .theme import (
    PALETTE as P, FONTS as F, DIMS as D,
    NAV_ITEMS, ROLE_COLORS, lerp_color, is_dark_theme,
)
from . import theme as _theme  # needed to read CURRENT_THEME_IDX at runtime
from .widgets import qfont, Toast, _blend


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

        # Logo circle
        _logo_color = lerp_color(self._accent, P.accent, 0.40)
        logo = _LogoCircle(_logo_color)
        logo.setFixedSize(48, 48)
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
            loc = QLabel(f"  📍 {self._user['location']}")
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
        nm = QLabel(self._user["full_name"][:20])
        nm.setFont(QFont("Segoe UI", 10, QFont.Bold))
        nm.setStyleSheet(f"color: {self._nav_text};")
        il.addWidget(nm)
        rl = QLabel(self._user["role"])
        rl.setFont(QFont("Segoe UI", 9))
        rl.setStyleSheet(f"color: {self._nav_text_dim};")
        il.addWidget(rl)
        pl.addWidget(info, 1)

        # Logout button — pill shaped
        logout = QPushButton("⏻")
        logout.setFont(QFont("Segoe UI", 13))
        logout.setCursor(Qt.PointingHandCursor)
        logout.setFixedSize(36, 36)
        logout_bg = lerp_color(self._bg, "#FFFFFF", 0.06 if self._glow else 0.12)
        logout.setStyleSheet(f"""
            QPushButton {{
                background: {logout_bg}; color: {self._nav_text_dim};
                border: 1px solid {lerp_color(self._bg, "#FFFFFF", 0.15)};
                border-radius: 18px;
            }}
            QPushButton:hover {{
                color: {P.danger}; background: {lerp_color(P.danger, self._bg, 0.85)};
                border-color: {lerp_color(P.danger, self._bg, 0.50)};
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

        self.setFixedHeight(48)
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
            # Soft rounded active background
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(self._nav_active))
            p.drawRoundedRect(r, 14, 14)

            # Glowing accent indicator bar on left
            accent = QColor(self._accent_color)
            p.setBrush(accent)
            p.drawRoundedRect(QRectF(3, 10, 4, h - 20), 2, 2)

            # Subtle accent glow behind the bar (if dark)
            if self._glow:
                glow_col = QColor(self._accent_color)
                glow_col.setAlpha(25)
                p.setBrush(glow_col)
                p.drawRoundedRect(QRectF(1, 6, 8, h - 12), 4, 4)

            text_col = QColor(self._text_on_hl)
        elif self._hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(self._nav_hover))
            p.drawRoundedRect(r, 14, 14)
            text_col = QColor(self._text_on_hl)
        else:
            text_col = QColor(self._nav_text)

        # Icon
        p.setPen(text_col)
        p.setFont(QFont("Segoe UI", 15))
        p.drawText(QRectF(14, 0, 36, h), Qt.AlignCenter, self._icon)

        # Label
        font = QFont("Segoe UI", 11, QFont.Bold if self._active else QFont.Normal)
        p.setFont(font)
        label_rect = QRectF(52, 0, w - 58, h)
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
    theme_clicked = Signal()

    def __init__(self, bg, parent=None):
        super().__init__(parent)
        self._bg = bg
        self._hover = False
        self.setCursor(Qt.PointingHandCursor)

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def mousePressEvent(self, event):
        self.theme_clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = min(self.width(), self.height())
        if self._hover:
            # Fill fully with theme accent on hover (matches login logo hover)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(P.accent))
            p.drawEllipse(QRectF(0, 0, s, s))
            p.setPen(QPen(QColor(lerp_color(P.accent, "#FFFFFF", 0.55)), 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(3, 3, s - 6, s - 6))
        else:
            glow = QColor(lerp_color(self._bg, "#FFFFFF", 0.08))
            p.setPen(Qt.NoPen); p.setBrush(glow)
            p.drawEllipse(QRectF(0, 0, s, s))
            ring = QColor(lerp_color(self._bg, "#FFFFFF", 0.18))
            p.setBrush(ring)
            p.setPen(QPen(QColor("#FFFFFF"), 1.5))
            p.drawEllipse(QRectF(3, 3, s - 6, s - 6))
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", 16, QFont.Bold))
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
        glow = QColor(lerp_color(self._bg, "#FFFFFF", 0.06))
        p.setPen(Qt.NoPen); p.setBrush(glow)
        p.drawEllipse(QRectF(0, 0, s, s))
        fill = QColor(lerp_color(self._bg, "#FFFFFF", 0.18))
        p.setBrush(fill)
        accent = QColor(lerp_color(self._bg, "#FFFFFF", 0.60))
        p.setPen(QPen(accent, 1.5))
        p.drawEllipse(QRectF(3, 3, s - 6, s - 6))
        p.setPen(accent)
        p.setFont(qfont(F.small_bold))
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
