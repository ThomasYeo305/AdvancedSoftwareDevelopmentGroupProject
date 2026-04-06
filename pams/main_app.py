# ============================================================
# PAMS — main_app.py
# Primary application shell: sidebar + topbar + content area
# Professional Corporate SaaS layout  (PySide6)
# ============================================================
from __future__ import annotations   # allows forward-reference type hints in Python 3.9 and earlier
import traceback   # imports traceback so the view loader can print detailed error messages if a view fails to import
from typing import Callable   # imports Callable so on_logout parameter can be correctly type-hinted as a function

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,   # core layout and text widgets
    QPushButton, QScrollArea, QSizePolicy, QLineEdit, QSpacerItem,   # button, scrollable area, spacer
    QGraphicsDropShadowEffect,   # drop shadow used for card elevation in sub-widgets
)
from PySide6.QtCore import Qt, QRectF, Signal, QTimer, QPointF   # Qt flags, float rect, signal/slot, animation timer
from PySide6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QConicalGradient,   # fonts, colours, painter, and gradient types
    QRadialGradient, QPen, QPixmap, QIcon, QPainterPath,           # radial gradient for sphere, pen, icon/pixmap types
)
import math   # imports the math module for sine/cosine used in logo and orb animations

from .theme import (
    PALETTE as P, FONTS as F, DIMS as D,   # imports colour tokens, font tokens, and dimension tokens
    NAV_ITEMS, ROLE_COLORS, lerp_color, is_dark_theme,   # imports role-based nav items, role colour map, and theme helpers
)
from . import theme as _theme  # needed to read CURRENT_THEME_IDX at runtime for theme-aware colours
from .widgets import qfont, Toast, _blend, draw_key_icon   # imports shared widget utilities and the vector icon drawing function


def _readable_on(hex_color: str) -> str:
    """Return #FFFFFF or #1A1A2E whichever has better contrast against hex_color."""
    c = hex_color.lstrip("#")
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)   # splits the hex colour into red, green, blue channels (0–255)
    # Relative luminance (sRGB)
    def lin(v): x = v / 255; return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4   # converts an sRGB 8-bit value to linear light (applies gamma correction)
    lum = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)   # calculates relative luminance using the standard WCAG formula
    return "#FFFFFF" if lum < 0.35 else "#1A1A2E"   # returns white for dark backgrounds, dark navy for light backgrounds


# ──────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────
class Sidebar(QWidget):
    navigate = Signal(str)   # emits the nav key (e.g. 'dashboard') when a nav item is clicked
    theme_requested = Signal()   # emits when the logo is clicked to toggle the colour theme

    def __init__(self, user: dict, on_navigate: Callable, on_logout: Callable, parent=None):
        super().__init__(parent)
        self._user = user   # stores the logged-in user dict (name, role, location)
        self._on_nav = on_navigate   # stores the callback to call when a navigation item is clicked
        self._on_logout = on_logout  # stores the callback to call when the logout button is clicked
        self._nav_items = NAV_ITEMS.get(user["role"], [])   # gets the list of nav items allowed for this user's role (RBAC)
        self._active_key = "dashboard"   # tracks which nav item is currently highlighted (starts on dashboard)
        self._item_widgets: list[_NavItem] = []   # list of all _NavItem widgets so their active state can be toggled

        _base = ROLE_COLORS.get(user["role"], P.bg_sidebar)   # picks the base accent colour for this role (e.g. emerald for admin)
        self._accent = _base
        _dark = is_dark_theme()
        if _dark:
            # Dark mode: sidebar colours are deeply blended toward black for a dark UI
            self._bg        = lerp_color(_base, "#000000", 0.78)   # main sidebar background: 78% black blend
            self._bg_top    = lerp_color(_base, "#000000", 0.70)   # slightly lighter top for the gradient depth effect
            self._nav_text  = "#E8ECF4"   # near-white text colour for dark mode sidebar
            self._nav_active = lerp_color(_base, "#FFFFFF", 0.22)   # active nav item background: faint white blend
            self._nav_hover  = lerp_color(_base, "#FFFFFF", 0.12)   # hover nav item background: very faint white blend
        else:
            # Light mode: sidebar colours are blended toward white
            self._bg        = lerp_color(_base, "#FFFFFF", 0.86)   # main sidebar background: 86% white blend (very light)
            self._bg_top    = lerp_color(_base, "#FFFFFF", 0.78)   # slightly more saturated top for gradient depth
            self._nav_text  = "#1A1A2E"   # dark navy text colour for light mode sidebar
            self._nav_active = lerp_color(_base, "#FFFFFF", 0.55)   # active nav item: medium blend between accent and white
            self._nav_hover  = lerp_color(_base, "#FFFFFF", 0.70)   # hover nav item: lighter blend between accent and white
        self._glow = _dark   # enables the glow effect on active nav items only in dark mode
        self._nav_text_dim = lerp_color(self._nav_text, self._bg, 0.45)   # muted version of nav text (45% blended with background) for secondary labels
        self._accent_col = lerp_color(_base, P.accent, 0.35) if _dark else _base   # in dark mode, slightly merges the role colour toward the main indigo accent

        self.setFixedWidth(D.sidebar_w)   # locks the sidebar to the fixed width defined in the design tokens
        self._build()   # calls the method that constructs all the sidebar widgets

    def paintEvent(self, event):
        """Draw a subtle vertical gradient for depth instead of a flat background."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        grad = QLinearGradient(0, 0, 0, h)   # creates a top-to-bottom gradient for the sidebar background
        grad.setColorAt(0.0, QColor(self._bg_top))   # slightly lighter (or more saturated) colour at the top of the sidebar
        grad.setColorAt(0.4, QColor(self._bg))        # transitions to the main background colour at 40% height
        grad.setColorAt(1.0, QColor(lerp_color(self._bg, "#000000", 0.08)))   # slightly darker at the very bottom for depth
        p.fillRect(0, 0, w, h, grad)   # paints the entire sidebar background with the vertical gradient
        p.end()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)   # removes all padding from the sidebar outer layout
        lay.setSpacing(0)   # removes the gap between all sidebar sections

        # ── Brand strip ──
        brand = QWidget()
        brand.setStyleSheet("background: transparent;")   # makes the brand strip transparent so the paintEvent gradient shows through
        bl = QHBoxLayout(brand)
        bl.setContentsMargins(16, D.pad_lg, 12, D.pad_md)   # adds 16px left, large top, 12px right, medium bottom padding to the brand row

        # Logo circle — now fully animated 3D glossy
        _logo_color = lerp_color(self._accent, P.accent, 0.40)   # blends the role accent 40% toward the main indigo to create a unique per-role logo colour
        logo = _LogoCircle(_logo_color)
        logo.setFixedSize(56, 56)   # locks the animated logo circle to 56×56 pixels
        logo.theme_clicked.connect(self.theme_requested.emit)   # forwards the logo click to the sidebar's theme_requested signal
        bl.addWidget(logo)

        # Title block
        title_w = QWidget()
        title_w.setStyleSheet("background: transparent;")
        tl = QVBoxLayout(title_w)
        tl.setContentsMargins(12, 0, 0, 0)   # adds 12px left padding to the title block to separate it from the logo
        tl.setSpacing(1)   # puts 1px between the PARAGON and Management Suite labels
        t1 = QLabel("PARAGON")
        t1.setFont(QFont("Segoe UI", 17, QFont.Bold))   # uses a large 17pt bold font for the brand name
        t1.setStyleSheet(f"color: {self._nav_text};")   # sets the brand name colour to the nav text colour for the current theme
        tl.addWidget(t1)
        t2 = QLabel("Management Suite")
        t2.setFont(QFont("Segoe UI", 9))   # uses a small 9pt font for the product line subtitle
        t2.setStyleSheet(f"color: {self._nav_text_dim};")   # uses the muted text colour so the subtitle is secondary to the brand name
        tl.addWidget(t2)
        bl.addWidget(title_w, 1)   # gives the title block all remaining stretch space to the right of the logo
        lay.addWidget(brand)

        # ── Accent divider line ──
        div = _AccentDivider(self._accent_col, self._bg)   # creates a 2px line that fades from accent colour at the centre to transparent at the edges
        div.setFixedHeight(2)
        lay.addWidget(div)
        lay.addSpacing(6)   # adds 6px of space below the top divider before the nav header

        # ── Nav section header ──
        nav_hdr = QLabel("  NAVIGATION")
        nav_hdr.setFont(QFont("Segoe UI", 8, QFont.Bold))   # uses tiny 8pt bold for the 'NAVIGATION' section header label
        nav_hdr.setStyleSheet(
            f"color: {self._nav_text_dim}; "
            f"background: transparent; padding: 6px 0 6px {D.pad_md}px;")   # sets the header to muted grey with left padding matching the nav items
        lay.addWidget(nav_hdr)

        # ── Nav items ──
        nav_area = QWidget()
        nav_area.setStyleSheet("background: transparent;")
        nl = QVBoxLayout(nav_area)
        nl.setContentsMargins(10, 0, 10, 0)   # indents nav items 10px from each side of the sidebar
        nl.setSpacing(4)   # puts 4px gaps between each navigation item
        for icon, label, key in self._nav_items:
            item = _NavItem(icon, label, key,
                            bg=self._bg,
                            nav_text=self._nav_text,
                            nav_active=self._nav_active,
                            nav_hover=self._nav_hover,
                            accent_color=self._accent_col,   # passes the per-role accent colour so the active nav indicator uses the right colour
                            glow=self._glow,   # enables glow effects on the active indicator only in dark mode
                            on_click=self._navigate)   # wires the nav item click to the sidebar's own _navigate method
            nl.addWidget(item)   # adds each nav item widget to the vertical nav list
            self._item_widgets.append(item)   # keeps a reference so active state can be toggled later
        lay.addWidget(nav_area)   # adds the entire nav items container to the sidebar vertical layout

        if self._item_widgets:
            self._set_active("dashboard")   # highlights the Dashboard nav item as selected when the sidebar first loads

        # ── Spacer ──
        lay.addStretch(1)   # pushes the location badge and profile area to the bottom of the sidebar

        # ── Location badge ──
        if self._user.get("location"):   # only shows the location badge if the user has a location assigned (e.g. branch staff)
            loc = QLabel(f"  Location: {self._user['location']}")
            loc.setFont(QFont("Segoe UI", 10))   # uses 10pt font for the compact location label
            loc.setStyleSheet(
                f"color: {self._nav_text}; background: transparent; padding: 4px {D.pad_md}px;")   # uses the nav text colour with left padding matching the nav items
            lay.addWidget(loc)

        # ── Bottom divider ──
        div2 = _AccentDivider(self._accent_col, self._bg)   # creates a second accent divider line above the profile area
        div2.setFixedHeight(2)   # locks the bottom divider to exactly 2px tall
        lay.addWidget(div2)

        # ── User profile area ──
        profile = QWidget()
        profile.setStyleSheet("background: transparent;")   # transparent so the sidebar gradient shows through the profile strip
        pl = QHBoxLayout(profile)
        pl.setContentsMargins(D.pad_sm + 2, D.pad_sm, D.pad_sm, D.pad_sm + 2)   # adds small padding around the profile row

        # Avatar — larger with accent glow
        initials = "".join(p[0] for p in self._user["full_name"].split()[:2])   # takes the first letter of each word in the full name to build 1–2 letter initials
        avatar = _AvatarCircle(initials, self._accent_col)   # creates the round avatar widget with the user's initials and role accent colour
        avatar.setFixedSize(48, 48)   # locks the avatar circle to 48×48 pixels
        pl.addWidget(avatar)

        # Info
        info = QWidget()
        info.setStyleSheet("background: transparent;")   # transparent info block so the sidebar gradient shows through
        il = QVBoxLayout(info)
        il.setContentsMargins(10, 0, 0, 0)   # 10px left gap between avatar circle and the name/role text
        il.setSpacing(1)   # 1px gap between the name label and the role label
        nm = QLabel(self._user["full_name"])
        nm.setFont(QFont("Segoe UI", 10, QFont.Bold))   # bold 10pt for the full name in the profile strip
        nm.setStyleSheet(f"color: {self._nav_text};")   # uses the nav text colour for the name (white in dark mode, dark navy in light)
        nm.setMaximumWidth(D.sidebar_w - 100)   # caps the name label width so it does not overlap the logout button
        nm.setMinimumWidth(0)   # allows the name label to shrink down to zero if space is very tight
        nm.setSizePolicy(nm.sizePolicy().horizontalPolicy(), nm.sizePolicy().verticalPolicy())   # keeps default size policy so the label still expands horizontally
        from PySide6.QtCore import Qt as _Qt   # local import to avoid a shadowing issue with the outer Qt reference
        nm.setWordWrap(False)   # disables word wrap so the name stays on one line and gets ellipsis-trimmed instead
        fm = nm.fontMetrics()   # gets the font metrics object to measure how wide the full name text would render
        elided = fm.elidedText(self._user["full_name"], _Qt.ElideRight, D.sidebar_w - 104)   # truncates the name with "…" on the right if it is wider than the available space
        nm.setText(elided)   # sets the (possibly shortened) name text on the label
        il.addWidget(nm)
        rl = QLabel(self._user["role"])
        rl.setFont(QFont("Segoe UI", 9))   # small 9pt font for the role label below the name
        rl.setStyleSheet(f"color: {self._nav_text_dim};")   # uses the muted text colour so the role is visually secondary to the name
        il.addWidget(rl)
        pl.addWidget(info, 1)   # stretches the info block to fill all remaining horizontal space in the profile row

        # Logout button — glossy pill with icon
        logout = QPushButton("⏻  Logout")
        logout.setFont(QFont("Segoe UI", 10, QFont.Bold))   # bold 10pt font for the logout button text
        logout.setCursor(Qt.PointingHandCursor)   # changes the cursor to a hand pointer when hovering over the logout button
        logout.setFixedSize(100, 36)   # locks the logout button to exactly 100×36 pixels
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
        """)   # normal state: dark gradient with subtle red tint; hover: deep red gradient with white text; pressed: darkest red
        logout.clicked.connect(self._on_logout)   # connects the logout button click to the stored logout callback (goes back to login)
        pl.addWidget(logout)

        lay.addWidget(profile)   # adds the complete profile strip (avatar + name + role + logout) to the bottom of the sidebar

    def _navigate(self, key: str):
        self._set_active(key)   # highlights the clicked nav item by its key (e.g. 'tenants')
        self._on_nav(key)   # calls the external navigation callback (defined in MainApp) to actually switch the view

    def _set_active(self, key: str):
        self._active_key = key   # stores the currently active nav key so it can be restored after a theme reload
        for item in self._item_widgets:
            item.set_active(item._key == key)   # tells each nav item widget whether it is the active one (True/False)

    def refresh_active(self, key: str):
        self._set_active(key)   # re-highlights the correct nav item (called from MainApp after navigating programmatically)


# ──────────────────────────────────────────────────────────
# NAV ITEM
# ──────────────────────────────────────────────────────────
class _NavItem(QWidget):
    def __init__(self, icon, label, key, bg, nav_text, nav_active, nav_hover,
                 on_click, accent_color=None, glow=False, parent=None):
        super().__init__(parent)
        self._key = key   # stores the route key (e.g. 'tenants') that this nav item represents
        self._on_click = on_click   # stores the callback to call when this nav item is clicked
        self._active = False   # tracks whether this nav item is currently the selected/active page
        self._hover = False   # tracks whether the mouse is currently hovering over this nav item

        self._bg_col = bg   # sidebar background colour used to reset the item background when not hovered
        self._nav_text = nav_text   # normal text colour for the nav item label (white in dark, dark in light)
        self._nav_active = nav_active   # background fill colour to use when this item is the active page
        self._nav_hover = nav_hover   # background fill colour to use when the mouse hovers over this item
        self._icon = icon   # the icon key string passed to draw_key_icon (e.g. 'dashboard', 'tenants')
        self._label = label   # the human-readable display text shown next to the icon (e.g. 'Dashboard')
        self._glow = glow   # whether to show the glow effect behind the active indicator bar (dark mode only)
        self._accent_color = accent_color or nav_active   # per-role accent colour for the active indicator bar gradient
        self._text_on_hl = _readable_on(bg)   # calculates whether white or dark text is more readable on the active background

        self.setFixedHeight(52)   # locks each nav item to exactly 52px tall so the sidebar stays evenly spaced
        self.setCursor(Qt.PointingHandCursor)   # shows a hand cursor when hovering to indicate the item is clickable
        self.setStyleSheet("background: transparent;")   # clears the Qt default background so paintEvent has full control

    def set_active(self, active: bool):
        self._active = active   # updates the active state flag
        self.update()   # triggers a repaint so the new active/inactive appearance is drawn immediately

    def enterEvent(self, event):
        self._hover = True   # sets the hover flag when the mouse enters the nav item
        self.update()   # repaints to show the hover highlight colour

    def leaveEvent(self, event):
        self._hover = False   # clears the hover flag when the mouse leaves the nav item
        self.update()   # repaints to remove the hover highlight colour

    def mousePressEvent(self, event):
        self._on_click(self._key)   # calls the navigation callback with this item's key when the user clicks it

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)   # enables anti-aliasing so the rounded corners look smooth
        w, h = self.width(), self.height()
        r = QRectF(3, 2, w - 6, h - 4)   # the rounded rectangle area with 3px horizontal and 2px vertical inset

        if self._active:
            # Glossy gradient active background
            p.setPen(Qt.NoPen)   # no border on the active background fill
            active_grad = QLinearGradient(0, 0, w, h)   # diagonal top-left to bottom-right gradient for the active fill
            active_grad.setColorAt(0.0, QColor(lerp_color(self._accent_color, "#FFFFFF", 0.18)))   # slightly lighter accent at the top-left corner
            active_grad.setColorAt(0.5, QColor(self._nav_active))   # pure nav_active colour in the middle
            active_grad.setColorAt(1.0, QColor(lerp_color(self._nav_active, "#000000", 0.10)))   # 10% darker at the bottom-right for depth
            p.setBrush(active_grad)
            p.drawRoundedRect(r, 14, 14)   # draws the active background with 14px corner radius

            # Top gloss sheen
            gloss_rect = QRectF(4, 3, w - 8, (h - 6) * 0.45)   # upper 45% of the item area for the glass-like shine
            gloss_grad = QLinearGradient(0, gloss_rect.top(), 0, gloss_rect.bottom())   # top-to-bottom gradient for the gloss
            gloss_grad.setColorAt(0.0, QColor(255, 255, 255, 38))   # semi-transparent white at the top of the shine
            gloss_grad.setColorAt(1.0, QColor(255, 255, 255, 0))   # fully transparent at the bottom of the shine
            p.setBrush(gloss_grad)
            p.drawRoundedRect(gloss_rect, 12, 12)   # draws the top gloss sheen over the active background

            # Left indicator bar — thick vibrant glowing
            bar_grad = QLinearGradient(0, 8, 0, h - 8)   # vertical gradient for the left accent bar
            bar_grad.setColorAt(0.0, QColor(lerp_color(self._accent_color, "#FFFFFF", 0.60)))   # bright near-white at the top of the bar
            bar_grad.setColorAt(0.5, QColor(self._accent_color))   # pure accent colour in the middle of the bar
            bar_grad.setColorAt(1.0, QColor(lerp_color(self._accent_color, "#000000", 0.30)))   # 30% darker at the bottom of the bar
            p.setBrush(bar_grad)
            p.drawRoundedRect(QRectF(3, 8, 5, h - 16), 3, 3)   # draws the 5px wide indicator bar on the left edge

            # Left bar outer glow
            glow_col = QColor(self._accent_color)
            glow_col.setAlpha(40)   # sets the glow to 40/255 alpha (mostly transparent) to avoid being too bright
            p.setBrush(glow_col)
            p.drawRoundedRect(QRectF(1, 5, 9, h - 10), 4, 4)   # draws a wider 9px rounded rect behind the bar as a soft glow

            text_col = QColor(self._text_on_hl)   # uses white or dark text depending on background luminance

        elif self._hover:
            p.setPen(Qt.NoPen)   # no border on the hover fill
            hover_grad = QLinearGradient(0, 0, w, h)   # diagonal gradient for the hover highlight
            hover_grad.setColorAt(0.0, QColor(lerp_color(self._nav_hover, "#FFFFFF", 0.08)))   # very slightly lighter at top-left
            hover_grad.setColorAt(1.0, QColor(self._nav_hover))   # nav_hover colour at bottom-right
            p.setBrush(hover_grad)
            p.drawRoundedRect(r, 14, 14)   # draws the hover background with the same 14px corner radius
            text_col = QColor(self._text_on_hl)   # uses high-contrast text colour on the highlighted background
        else:
            text_col = QColor(self._nav_text)   # normal (not active, not hovered) text colour from nav_text

        # Custom vector icon — drawn by key, no emoji/text
        icon_cx = 30.0   # horizontal centre of the icon area (30px from the left edge)
        icon_cy = h / 2   # vertical centre of the icon is the midpoint of the nav item
        icon_size = h * 0.36   # icon is 36% of the item height (~19px) to keep it compact
        draw_key_icon(p, self._key, icon_cx, icon_cy, icon_size, text_col)   # calls the shared function to draw the icon for this nav key

        # Label text
        font = QFont("Segoe UI", 11, QFont.Bold if self._active else QFont.Normal)   # bold font for the active item, normal weight for others
        font.setLetterSpacing(QFont.AbsoluteSpacing, 0.3 if self._active else 0)   # adds slight letter spacing to the active label for a premium look
        p.setFont(font)
        label_rect = QRectF(56, 0, w - 62, h)   # text starts 56px from the left (after the icon) with 6px right margin
        p.setPen(text_col)
        p.drawText(label_rect, Qt.AlignVCenter | Qt.AlignLeft, self._label)   # draws the nav label text vertically centred and left-aligned
        p.end()


# ──────────────────────────────────────────────────────────
# TOP BAR
# ──────────────────────────────────────────────────────────
class TopBar(QWidget):
    search_triggered = Signal(str)      # emits the search query text when the user presses Enter in the search bar
    notification_clicked = Signal()     # emits when the notifications bell is clicked (wired to navigate to payments)

    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self._user = user   # stores the logged-in user dict for role colour and notification filtering
        self.setFixedHeight(D.topbar_h)   # locks the top bar to the fixed height from the design tokens
        self.setObjectName("topbar")   # sets the Qt object name so the #topbar CSS selector applies to this widget only
        self.setStyleSheet(f"""
            #topbar {{
                background-color: {P.bg_surface};
                border-bottom: 1px solid {P.border};
            }}
            #topbar QLabel  {{ background: transparent; }}
            #topbar QWidget {{ background: transparent; }}
        """)   # surface background colour with a 1px border at the bottom; all child labels/widgets are transparent
        self._late_count = 0   # initialises the late payment counter to zero before the first DB query
        self._build()   # builds all the top bar widgets (breadcrumb, search bar, role badge, bell)
        self._refresh_notifications()   # immediately queries the DB for overdue payments to set the bell badge

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(D.pad_lg, 0, D.pad_lg, 0)   # adds large left and right padding, no top/bottom
        lay.setSpacing(0)   # removes automatic spacing between widgets so positions are controlled manually

        # ── Left: breadcrumb ──
        crumb_lbl = QLabel("PARAGON")
        crumb_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))   # small 9pt bold font for the brand name in the breadcrumb
        crumb_lbl.setStyleSheet(f"color: {P.accent}; letter-spacing: 1px; background: transparent;")   # accent colour with slight letter-spacing for a premium look
        lay.addWidget(crumb_lbl)

        sep = QLabel("  /  ")
        sep.setFont(QFont("Segoe UI", 11))   # slightly larger 11pt for the breadcrumb separator slash
        sep.setStyleSheet(f"color: {P.text_muted}; background: transparent;")   # muted grey colour so the separator is subtle
        lay.addWidget(sep)

        self._title_lbl = QLabel("Dashboard")
        self._title_lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))   # large 16pt bold font for the current page title
        self._title_lbl.setStyleSheet(f"color: {P.text_primary}; background: transparent;")   # primary text colour (bright in dark mode) for the page title
        lay.addWidget(self._title_lbl)

        # ── Center: search bar (FUNCTIONAL) ──
        lay.addStretch(1)   # pushes the search bar toward the center by consuming all left-side extra space

        # Search container with built-in icon
        self._search = QLineEdit()
        self._search.setPlaceholderText("   Search tenants, apartments…")   # hint text shown when the search bar is empty
        self._search.setFixedWidth(320)   # locks the search bar to exactly 320px wide
        self._search.setFixedHeight(40)   # locks the search bar to 40px tall

        # Custom-drawn vector icon for a sleek, big-company search look
        def _create_search_icon():
            pix = QPixmap(24, 24)   # creates a 24×24 pixel canvas for the search icon
            pix.fill(Qt.transparent)   # clears the canvas to fully transparent so only the drawn lines show
            p = QPainter(pix)
            p.setRenderHint(QPainter.Antialiasing)   # enables smooth anti-aliased line drawing
            p.setPen(QPen(QColor(P.text_muted), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))   # muted grey 2px pen with round caps for a clean look
            p.drawEllipse(5, 5, 8, 8)   # draws the magnifying glass circle at the top-left of the icon
            p.drawLine(11, 11, 17, 17)   # draws the magnifying glass handle as a diagonal line from the circle to the bottom-right
            p.end()
            return QIcon(pix)   # wraps the painted pixmap as a QIcon to use as the search action icon

        search_action = self._search.addAction(
            _create_search_icon(),
            QLineEdit.ActionPosition.LeadingPosition,   # places the search icon at the left (leading) side of the text field
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
        """)   # pill-shaped input with card background; focus state changes the border to accent colour to show it is active
        self._search.returnPressed.connect(self._on_search)   # wires the Enter key press to the search handler method
        lay.addWidget(self._search)
        lay.addStretch(1)   # pushes the right-side widgets away from the search bar by consuming all right-side extra space

        # ── Right: user name (colored by role) ──
        role_color = ROLE_COLORS.get(self._user["role"], P.accent)   # looks up the accent colour for this role (e.g. emerald for admin)
        name_lbl = QLabel(self._user["full_name"])
        name_lbl.setFont(qfont(F.body_bold))   # uses the body-bold font token for the user name
        name_lbl.setStyleSheet(f"color: {role_color}; background: transparent;")   # colours the user's name with their role colour
        lay.addWidget(name_lbl)
        lay.addSpacing(10)   # adds a 10px gap between the user name and the role badge

        # ── Role badge ──
        badge = QPushButton(self._user["role"])
        badge.setEnabled(False)   # disables the badge so it cannot be clicked (it is purely decorative)
        badge.setFont(qfont(F.small_bold))   # uses the small-bold font token for the compact role label
        badge.setFixedHeight(30)   # locks the role badge to 30px tall
        badge.setStyleSheet(f"""
            QPushButton {{
                background-color: {role_color};
                color: #FFFFFF;
                border: none;
                border-radius: 15px;
                padding: 0 16px;
                font-weight: bold;
            }}
        """)   # solid role-colour pill with white text and fully rounded ends
        lay.addWidget(badge)
        lay.addSpacing(12)   # adds a 12px gap between the role badge and the notification bell

        # ── Notification bell (FUNCTIONAL) ──
        self._bell_btn = QPushButton()
        self._bell_btn.setCursor(Qt.PointingHandCursor)   # shows a hand cursor to indicate the bell is clickable
        self._bell_btn.setFixedSize(42, 42)   # locks the bell button to 42×42 pixels (slightly larger for touch targets)
        self._bell_btn.clicked.connect(self.notification_clicked.emit)   # forwards the bell click to the notification_clicked signal
        self._bell_btn.setToolTip("Late payments — click to view")   # shows a tooltip describing what clicking the bell does
        self._update_bell_style()   # applies the initial bell style (grey if no late payments, red if there are)
        lay.addWidget(self._bell_btn)

    def _on_search(self):
        """Emit the search query when user presses Enter."""
        q = self._search.text().strip()   # removes leading/trailing whitespace from the typed search text
        if q:   # only emits if the search text is not empty
            self.search_triggered.emit(q)   # sends the search string to the MainApp's global search handler

    def _refresh_notifications(self):
        """Query DB for late payment count and update the bell badge."""
        try:
            from .. import database as db   # imports the database module relative to the pams package
            payments = db.get_all_payments(location=self._user.get("location"))   # fetches all payments filtered to the user's branch location
            self._late_count = sum(
                1 for p in payments
                if p.get("status") in ("Overdue", "Late", "Pending")   # counts payments with any of the three overdue/late statuses
            )
        except Exception:
            self._late_count = 0   # if the DB query fails for any reason, defaults the late count to zero
        self._update_bell_style()   # redraws the bell button with the new count

    def _update_bell_style(self):
        """Style the bell button with a red badge count if there are late payments."""
        count = self._late_count
        if count > 0:
            badge_text = str(count) if count < 100 else "99+"   # shows the exact count or '99+' if there are 100 or more late payments
            self._bell_btn.setText(f"🔔 {badge_text}")   # updates the bell button text to show the late payment count beside the bell emoji
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
            """)   # light red tinted background with a red border pill; hover makes the background more saturated
        else:
            self._bell_btn.setText("🔔")   # no count badge; just the plain bell emoji
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
            """)   # transparent background with muted grey bell; turns accent colour on hover

    def set_title(self, title: str):
        self._title_lbl.setText(title)   # updates the breadcrumb page title label to the new view name
        # refresh notifications whenever we switch views
        self._refresh_notifications()   # re-queries the DB for late payments each time the user changes pages


# ──────────────────────────────────────────────────────────
# MAIN APPLICATION SHELL
# ──────────────────────────────────────────────────────────
class MainApp(QWidget):
    """Sidebar + TopBar + scrollable content area."""

    theme_requested = Signal()   # emits when the user clicks the logo to request a theme toggle

    VIEW_TITLES = {
        "dashboard":   "Dashboard",        # maps the dashboard route key to its human-readable page title
        "tenants":     "Tenant Management",   # maps the tenants route key to its page title
        "apartments":  "Apartment Management",  # apartments page title
        "payments":    "Payment & Billing",  # payments page title
        "maintenance": "Maintenance",   # maintenance page title
        "complaints":  "Complaints Management",   # complaints page title
        "reports":     "Reports & Analytics",   # reports page title
        "users":       "User Management",   # user management page title (admin only)
    }

    def __init__(self, user: dict, on_logout: Callable, initial_page: str = "dashboard", parent=None):
        super().__init__(parent)
        self._user = user   # stores the user dict so child widgets can use role, name, and location
        self._on_logout = on_logout   # stores the callback that clears the main window and shows the login screen
        self._current_view = None   # tracks the currently displayed view widget (unused but reserved for future cleanup)
        self.setStyleSheet(f"background-color: {P.bg_surface};")   # sets the app shell background to the surface colour
        self._build()   # builds the sidebar, topbar, and scroll area layout
        self._navigate(initial_page)   # navigates to dashboard (or whatever initial_page was passed in) on startup

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)   # no padding on the outer shell so sidebar and body fill the entire window
        root.setSpacing(0)   # no gap between the sidebar and the body area

        # ── Sidebar ──
        self._sidebar = Sidebar(self._user,
                                on_navigate=self._navigate,   # when a nav item is clicked, call this app's _navigate method
                                on_logout=self._logout)   # when logout is clicked, call this app's _logout method
        self._sidebar.theme_requested.connect(self.theme_requested.emit)   # forwards the logo theme click signal up to main.py
        root.addWidget(self._sidebar)

        # ── Body (topbar + content) ──
        body = QWidget()
        body.setStyleSheet(f"background-color: {P.bg_surface};")   # surface colour for the body area behind views
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)   # no margins so the topbar and content fill the full width
        bl.setSpacing(0)   # no gap between the topbar and the content scroll area

        self._topbar = TopBar(self._user)
        self._topbar.search_triggered.connect(self._on_global_search)   # wires the topbar search box to this app's global search handler
        self._topbar.notification_clicked.connect(
            lambda: self._navigate("payments"))   # clicking the bell navigates directly to the payments view
        bl.addWidget(self._topbar)

        # ── Scrollable content ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)   # makes the inner content widget resize with the scroll area
        self._scroll.setFrameShape(QFrame.NoFrame)   # removes the default border frame around the scroll area
        self._scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {P.bg_surface};
                border: none;
            }}
        """)   # matches the surface background and removes the border so it blends with the body
        bl.addWidget(self._scroll, 1)   # gives the scroll area all remaining vertical space in the body layout
        root.addWidget(body, 1)   # gives the body area all remaining horizontal space beside the sidebar

    # ──────────────────────────────────────────────────────
    # NAVIGATION
    # ──────────────────────────────────────────────────────
    def _navigate(self, key: str):
        self._topbar.set_title(self.VIEW_TITLES.get(key, key.title()))   # updates the breadcrumb title to the page name (e.g. 'Tenant Management')
        self._sidebar.refresh_active(key)   # highlights the matching nav item in the sidebar for the new page

        # Create new content widget
        container = QWidget()
        container.setStyleSheet(f"background-color: {P.bg_surface};")   # surface colour background for the new view container
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)   # no margins so the view fills the full scroll area width and height
        self._load_view(key, container, cl)   # dynamically imports and instantiates the requested view widget
        self._scroll.setWidget(container)   # replaces the scroll area's content with the newly created view container

    def _load_view(self, key: str, parent: QWidget, layout: QVBoxLayout):
        """Dynamically import and instantiate the requested view."""
        try:
            if key == "dashboard":
                from .views.dashboard_view import DashboardView   # lazy import so views only load when needed
                layout.addWidget(DashboardView(self._user, parent))   # creates and adds the Dashboard view

            elif key == "tenants":
                from .views.tenant_view import TenantView   # lazy import for the Tenant Management view
                layout.addWidget(TenantView(self._user, parent))

            elif key == "apartments":
                from .views.apartment_view import ApartmentView   # lazy import for the Apartment Management view
                layout.addWidget(ApartmentView(self._user, parent))

            elif key == "payments":
                from .views.payment_view import PaymentView   # lazy import for the Payment & Billing view
                layout.addWidget(PaymentView(self._user, parent))

            elif key == "maintenance":
                from .views.maintenance_view import MaintenanceView   # lazy import for the Maintenance view
                layout.addWidget(MaintenanceView(self._user, parent))

            elif key == "complaints":
                from .views.complaint_view import ComplaintView   # lazy import for the Complaints Management view
                layout.addWidget(ComplaintView(self._user, parent))

            elif key == "reports":
                from .views.report_view import ReportView   # lazy import for the Reports & Analytics view
                layout.addWidget(ReportView(self._user, parent))

            elif key == "users":
                from .views.user_view import UserView   # lazy import for the User Management view (admin only)
                layout.addWidget(UserView(self._user, parent))

        except Exception as exc:
            err = QLabel(f"Error loading view:\n{traceback.format_exc()}")   # shows the full Python traceback if the view fails to load
            err.setFont(QFont("Consolas", 10))   # monospace Consolas font so the traceback is easy to read
            err.setStyleSheet(f"color: {P.danger}; padding: 40px;")   # red danger colour with 40px padding for comfortable reading
            err.setWordWrap(True)   # enables word wrapping so long error messages don't overflow horizontally
            layout.addWidget(err)

    # ──────────────────────────────────────────────────────
    # GLOBAL SEARCH
    # ──────────────────────────────────────────────────────
    def _on_global_search(self, query: str):
        """Navigate to tenants (most common search), pre-fill its search box."""
        self._navigate("tenants")   # switches to the Tenant Management view first
        # Try to pre-fill the tenant view's search box
        widget = self._scroll.widget()   # gets the current content widget inside the scroll area
        if widget:
            from .views.tenant_view import TenantView   # imports TenantView to use its type in findChildren
            for child in widget.findChildren(TenantView):   # searches the widget tree for the TenantView instance
                if hasattr(child, "_search"):
                    child._search.setText(query)   # pre-fills the tenant view's search box with the global search query
                break   # only fills the first TenantView found
        Toast(self.window(), f"Searching tenants for \"{query}\"…", kind="info")   # shows an info toast confirming the search was triggered

    # ──────────────────────────────────────────────────────
    # TOAST / LOGOUT
    # ──────────────────────────────────────────────────────
    def show_toast(self, message: str, kind="success"):
        Toast(self.window(), message, kind)   # creates a Toast notification anchored to the top-level window

    def _logout(self):
        self._on_logout()   # calls the logout callback from main.py which destroys this widget and shows the login screen


# ──────────────────────────────────────────────────────────
# INTERNAL HELPER WIDGETS
# ──────────────────────────────────────────────────────────
class _LogoCircle(QWidget):
    """Animated 3D glossy logo — rotating gradient ring, inner glow, shimmer highlight."""
    theme_clicked = Signal()   # emits when the user clicks the logo to request a colour theme toggle

    def __init__(self, bg, parent=None):
        super().__init__(parent)
        self._bg = bg   # stores the base accent colour used for the sphere gradient and ring colours
        self._hover = False   # tracks whether the mouse is currently hovering over the logo widget
        self._angle = 0   # current rotation angle (0–359°) of the conical gradient ring
        self._pulse = 0.0   # current pulse value (0.0–1.0) used to animate the gloss brightness
        self._pulse_dir = 1   # direction of the pulse animation: 1 = growing brighter, -1 = fading
        self.setCursor(Qt.PointingHandCursor)   # shows a hand cursor so the user knows the logo is clickable
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)   # fires the _tick method each timer interval to advance the animation
        self._timer.start(30)   # fires every 30 milliseconds (~33 frames per second) for smooth animation

    def _tick(self):
        self._angle = (self._angle + 3) % 360   # advances the ring rotation by 3° each tick and wraps at 360°
        self._pulse += 0.04 * self._pulse_dir   # moves the pulse value by 4% per tick in the current direction
        if self._pulse >= 1.0:
            self._pulse = 1.0; self._pulse_dir = -1   # clamps at 1.0 and reverses direction to start fading
        elif self._pulse <= 0.0:
            self._pulse = 0.0; self._pulse_dir = 1   # clamps at 0.0 and reverses direction to start brightening
        self.update()   # requests a repaint on every tick to redraw the animated logo

    def enterEvent(self, event):
        self._hover = True; self.update()   # sets hover flag and repaints to switch to the rainbow ring effect

    def leaveEvent(self, event):
        self._hover = False; self.update()   # clears hover flag and repaints to return to the normal blue ring

    def mousePressEvent(self, event):
        self.theme_clicked.emit()   # emits the theme_clicked signal to trigger a colour theme change

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)   # enables anti-aliasing for smooth circular shapes
        s = min(self.width(), self.height())   # uses the smallest dimension to keep the logo circular
        cx, cy = s / 2, s / 2   # centre of the logo circle
        r = s / 2 - 3   # radius with a 3px inset so the outer ring fits within the widget bounds

        # ── Outer rotating rainbow/gradient ring ──
        ring_grad = QConicalGradient(cx, cy, self._angle)   # conical gradient centred on the logo, rotated by the current angle each tick
        if self._hover:
            # Rainbow ring on hover to show the theme-switching action
            ring_grad.setColorAt(0.00, QColor("#FF6FD8"))   # hot pink at 0°
            ring_grad.setColorAt(0.20, QColor("#6366F1"))   # indigo at 72°
            ring_grad.setColorAt(0.40, QColor("#06B6D4"))   # cyan at 144°
            ring_grad.setColorAt(0.60, QColor("#10B981"))   # emerald green at 216°
            ring_grad.setColorAt(0.80, QColor("#F59E0B"))   # amber at 288°
            ring_grad.setColorAt(1.00, QColor("#FF6FD8"))   # back to pink to complete the loop
        else:
            # Normal blue→violet→cyan ring
            ring_grad.setColorAt(0.00, QColor(P.accent))   # main app accent (indigo) at the start
            ring_grad.setColorAt(0.33, QColor(lerp_color(P.accent, "#8B5CF6", 0.6)))   # 60% blend toward violet
            ring_grad.setColorAt(0.66, QColor("#06B6D4"))   # cyan two-thirds around
            ring_grad.setColorAt(1.00, QColor(P.accent))   # back to accent to complete the loop
        pen = QPen(ring_grad, 3.5)   # 3.5px wide pen using the conical gradient for the rotating ring
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)   # no fill; only the ring outline is drawn
        p.drawEllipse(QRectF(2, 2, s - 4, s - 4))   # draws the outer rotating ring with a 2px inset from widget edges

        # ── Deep glossy sphere background ──
        sphere_grad = QRadialGradient(cx - r * 0.28, cy - r * 0.32, r * 1.15)   # off-centre origin (top-left) for a 3D lit-sphere look
        pulse_val = 0.12 + self._pulse * 0.10   # scales the pulse value to a small 12–22% range for subtle breathing
        if self._hover:
            # Purple sphere on hover
            sphere_grad.setColorAt(0.0, QColor(lerp_color("#9B59F5", "#FFFFFF", 0.25)))   # bright purple-white at the highlight point
            sphere_grad.setColorAt(0.45, QColor("#5B21B6"))   # deep purple in the mid-tone
            sphere_grad.setColorAt(0.80, QColor("#1E1B4B"))   # very dark indigo near the edge
            sphere_grad.setColorAt(1.0, QColor("#0C0A1E"))   # almost-black at the outer edge of the sphere
        else:
            # Normal accent-coloured sphere
            sphere_grad.setColorAt(0.0, QColor(lerp_color(P.accent, "#FFFFFF", 0.35)))   # pale accent-tinted highlight at the light source
            sphere_grad.setColorAt(0.40, QColor(lerp_color(P.accent, "#000033", 0.35)))   # accent fading toward dark blue
            sphere_grad.setColorAt(0.75, QColor(lerp_color(P.accent, "#000022", 0.70)))   # 70% toward near-black dark navy
            sphere_grad.setColorAt(1.0, QColor(lerp_color(self._bg, "#000000", 0.30)))   # darkened version of the bg colour at the rim
        p.setPen(Qt.NoPen)
        p.setBrush(sphere_grad)
        p.drawEllipse(QRectF(5, 5, s - 10, s - 10))   # draws the sphere with a 5px inset inside the outer ring

        # ── Top-left specular highlight (gloss) ──
        gloss = QRadialGradient(cx - r * 0.30, cy - r * 0.40, r * 0.55)   # small radial gradient at the top-left to simulate a light reflection
        gloss_alpha = int(180 + self._pulse * 55)   # alpha oscillates between 180 and 235 with the pulse for a breathing gloss
        gloss.setColorAt(0.0, QColor(255, 255, 255, gloss_alpha))   # bright white at the centre of the highlight
        gloss.setColorAt(0.5, QColor(255, 255, 255, 60))   # fades to near-transparent at mid-radius
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))   # fully transparent at the edge of the gloss circle
        p.setBrush(gloss)
        p.drawEllipse(QRectF(8, 8, (s - 16) * 0.72, (s - 16) * 0.52))   # draws the gloss in the upper-left portion of the sphere

        # ── Bottom-right subtle rim light ──
        rim = QRadialGradient(cx + r * 0.50, cy + r * 0.50, r * 0.40)   # small gradient at the bottom-right for a secondary ambient rim light
        rim.setColorAt(0.0, QColor(120, 160, 255, 80))   # soft blue-white at the centre of the rim
        rim.setColorAt(1.0, QColor(120, 160, 255, 0))   # fades to transparent at the rim's edge
        p.setBrush(rim)
        p.drawEllipse(QRectF(s * 0.45, s * 0.45, s * 0.52, s * 0.52))   # draws the rim light in the lower-right quadrant

        # ── Pulsing outer glow ──
        glow_a = int(18 + self._pulse * 38)   # glow alpha pulses between 18 and 56 to create a breathing halo effect
        glow_col = QColor(P.accent if not self._hover else "#9B59F5")   # uses accent in normal mode, purple in hover mode
        glow_col.setAlpha(glow_a)
        for glow_r in range(3):   # draws 3 concentric glow rings with decreasing alpha and width
            g2 = QColor(glow_col)
            g2.setAlpha(glow_a - glow_r * 6)   # each successive ring is 6 alpha units fainter
            p.setPen(QPen(g2, 2.5 - glow_r * 0.6))   # each successive ring is also slightly thinner
            p.drawEllipse(QRectF(glow_r, glow_r, s - glow_r * 2, s - glow_r * 2))   # draws each glow ring slightly inset from the previous

        # ── P letter — clean bold font ──
        p.setPen(QColor("#FFFFFF"))   # white colour for the 'P' letter so it stands out on any sphere colour
        p.setFont(QFont("Segoe UI", max(1, int(s * 0.32)), QFont.Bold))   # font size is 32% of the widget size (minimum 1pt) so it scales with the logo without going to 0
        p.drawText(QRectF(0, 0, s, s), Qt.AlignCenter, "P")   # draws the 'P' letter perfectly centred in the logo circle
        p.end()


class _AvatarCircle(QWidget):
    def __init__(self, initials, bg, parent=None):
        super().__init__(parent)
        self._initials = initials   # the 1–2 letter initials to display inside the avatar circle
        self._bg = bg   # the accent colour used for the sphere gradient background of the avatar

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)   # enables smooth anti-aliased circles
        s = min(self.width(), self.height())   # uses the smaller dimension to ensure the avatar stays circular
        cx, cy = s / 2, s / 2   # calculates the centre coordinates of the avatar
        r = s / 2 - 2   # radius with a 2px inset so the outer ring fits within the widget

        # Outer ring
        ring_col = QColor(lerp_color(self._bg, "#FFFFFF", 0.40))   # blends the accent colour 40% toward white for a soft ring
        p.setPen(QPen(ring_col, 2))   # 2px ring outline using the blended ring colour
        p.setBrush(Qt.NoBrush)   # no fill on the outer ring — only the outline is drawn
        p.drawEllipse(QRectF(1, 1, s - 2, s - 2))   # draws the outer ring with a 1px inset from the widget edge

        # Body
        body_grad = QRadialGradient(cx - r * 0.25, cy - r * 0.3, r * 1.0)   # off-centre origin for a 3D sphere appearance
        body_grad.setColorAt(0.0, QColor(lerp_color(self._bg, "#FFFFFF", 0.35)))   # 35% white highlight at the lit top-left
        body_grad.setColorAt(0.5, QColor(lerp_color(self._bg, "#FFFFFF", 0.18)))   # 18% white in the mid-tone ring
        body_grad.setColorAt(1.0, QColor(lerp_color(self._bg, "#000000", 0.15)))   # 15% darker at the outer edge for roundness
        p.setPen(Qt.NoPen)   # no border on the filled sphere
        p.setBrush(body_grad)
        p.drawEllipse(QRectF(4, 4, s - 8, s - 8))   # draws the filled sphere body with 4px inset from widget edges

        # Gloss
        gloss = QRadialGradient(cx - r * 0.22, cy - r * 0.30, r * 0.50)   # small top-left radial gradient for the specular highlight
        gloss.setColorAt(0.0, QColor(255, 255, 255, 130))   # semi-transparent white at the highlight centre
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))   # fully transparent at the highlight edge
        p.setBrush(gloss)
        p.drawEllipse(QRectF(6, 6, (s - 12) * 0.65, (s - 12) * 0.48))   # draws the gloss in the upper-left 65%×48% portion of the avatar

        # Initials
        accent = QColor(lerp_color(self._bg, "#FFFFFF", 0.85))   # blends the accent 85% toward white for high-contrast initials
        p.setPen(accent)   # uses the near-white colour for the initials text
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))   # bold 11pt Segoe UI for compact readable initials
        p.drawText(QRectF(0, 0, s, s), Qt.AlignCenter, self._initials)   # draws the initials perfectly centred in the avatar circle
        p.end()


class _GradientDivider(QWidget):
    """Legacy divider — kept for backward compat but no longer used by Sidebar."""
    def __init__(self, bg, parent=None):
        super().__init__(parent)
        self._bg = bg   # stores the background colour to calculate the divider's fade colours
    def paintEvent(self, event):
        p = QPainter(self)
        w = self.width()
        mid = QColor(lerp_color(self._bg, "#FFFFFF", 0.20))   # mid colour is 20% lighter than the background for the centre of the divider
        edge = QColor(lerp_color(self._bg, "#FFFFFF", 0.04))   # edge colour is barely lighter (4%) to fade to near-invisible at the sides
        for i in range(w):   # draws the divider pixel-by-pixel to create a smooth gradient
            t = abs(i / max(1, w) - 0.5) * 2   # t goes from 0.0 at the centre to 1.0 at each edge
            c = QColor(lerp_color(mid.name(), edge.name(), t))   # interpolates between mid and edge colours based on distance from centre
            p.setPen(c)
            p.drawPoint(i, 0)   # draws a single pixel at this horizontal position
        p.end()


class _AccentDivider(QWidget):
    """A 2px divider that fades from accent color in the center to transparent."""
    def __init__(self, accent: str, bg: str, parent=None):
        super().__init__(parent)
        self._accent = accent   # stores the accent colour for the bright centre of the divider
        self._bg = bg   # stores the background colour to blend toward at the divider edges
    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        grad = QLinearGradient(0, 0, w, 0)   # horizontal left-to-right gradient for the divider
        edge = QColor(self._bg)   # the background colour used as the invisible edge (no contrast)
        mid = QColor(lerp_color(self._accent, "#FFFFFF", 0.30))   # accent blended 30% toward white for a softer highlight at the centre
        grad.setColorAt(0.0, edge)   # left edge is the background colour (invisible)
        grad.setColorAt(0.3, mid)    # fades to the mid accent colour by 30% from the left
        grad.setColorAt(0.7, mid)    # holds the accent colour across the centre 40% of the divider
        grad.setColorAt(1.0, edge)   # right edge returns to background colour (invisible)
        p.fillRect(0, 0, w, h, grad)   # fills the entire 2px-tall divider with the horizontal gradient
        p.end()


class _TopBarBorder(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(3)   # locks the top bar border to exactly 3px tall
    def paintEvent(self, event):
        p = QPainter(self)
        w = self.width()
        grad = QLinearGradient(0, 0, w, 0)   # horizontal gradient from left to right across the full top bar width
        grad.setColorAt(0.0, QColor(P.accent))   # starts with the vivid accent colour at the left edge
        grad.setColorAt(1.0, QColor(P.divider))   # fades to the subtle divider colour at the right edge
        p.fillRect(0, 0, w, 3, grad)   # fills the 3px-tall border strip with the horizontal gradient
        p.end()
