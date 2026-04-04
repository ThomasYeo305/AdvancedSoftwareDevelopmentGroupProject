# ============================================================
# PAMS - Paragon Apartment Management System
# theme.py  — Design tokens, palette, and PySide6 QSS
# Corporate SaaS — Professional Property-Tech Aesthetic
# ============================================================

from dataclasses import dataclass
from typing import Dict


# ──────────────────────────────────────────────────────────
# COLOUR PALETTE  (Professional Light Theme — Polished)
# ──────────────────────────────────────────────────────────
@dataclass
class _Palette:
    bg_base:       str = "#EDEEF4"
    bg_surface:    str = "#F0F2F8"
    bg_card:       str = "#FFFFFF"
    bg_card_hover: str = "#F7F8FD"
    bg_sidebar:    str = "#0C1F3F"
    bg_input:      str = "#F5F7FC"
    bg_row_alt:    str = "#F6F8FC"
    bg_overlay:    str = "#E8E8E8"

    accent:        str = "#4361EE"
    accent_dim:    str = "#3651D4"
    accent_glow:   str = "#E0E7FF"
    accent_light:  str = "#818CF8"
    accent_ultra:  str = "#C7D2FE"
    accent2:       str = "#1A2F54"
    accent2_dim:   str = "#0F2040"

    success:       str = "#10B981"
    success_light: str = "#D1FAE5"
    warning:       str = "#F59E0B"
    warning_light: str = "#FEF3C7"
    danger:        str = "#EF4444"
    danger_light:  str = "#FEE2E2"
    info:          str = "#6366F1"
    info_light:    str = "#E0E7FF"

    text_primary:  str = "#111827"
    text_secondary:str = "#4B5563"
    text_muted:    str = "#9CA3AF"
    text_on_accent:str = "#FFFFFF"
    text_link:     str = "#4361EE"

    border:        str = "#E2E5ED"
    border_focus:  str = "#4361EE"
    divider:       str = "#E5E7EF"

    shadow_sm:     str = "#F4F4F4"
    shadow_md:     str = "#EDEDED"
    shadow_lg:     str = "#E0E0E0"

    nav_text:      str = "#94A3C0"
    nav_active_bg: str = "#1E3A65"
    nav_active_text:str = "#FFFFFF"
    nav_hover_bg:  str = "#162F55"


PALETTE = _Palette()


# ──────────────────────────────────────────────────────────
# THEME VARIANTS
# ──────────────────────────────────────────────────────────
_THEMES: list[tuple[str, dict]] = [
    # ─── 1. LIGHT — Refined warm ivory with indigo accent ───
    ("☀  Light", {}),   # default — no overrides needed

    # ─── 2. DARK — Deep obsidian with violet/indigo accents ───
    ("🌙  Dark", {
        "bg_base":       "#0B0D14",
        "bg_surface":    "#10121A",
        "bg_card":       "#161822",
        "bg_card_hover": "#1C1F2E",
        "bg_sidebar":    "#080A12",
        "bg_input":      "#1C1F2E",
        "bg_row_alt":    "#12141C",
        "bg_overlay":    "#222538",
        "accent":        "#818CF8",
        "accent_dim":    "#6366F1",
        "accent_glow":   "#1E1B4B",
        "accent_light":  "#A5B4FC",
        "accent_ultra":  "#312E81",
        "accent2":       "#94A3B8",
        "accent2_dim":   "#64748B",
        "text_primary":  "#ECF0F8",
        "text_secondary":"#A0AEC0",
        "text_muted":    "#5A6578",
        "text_on_accent":"#FFFFFF",
        "text_link":     "#818CF8",
        "border":        "#222538",
        "border_focus":  "#818CF8",
        "divider":       "#1C1F2E",
        "shadow_sm":     "#06080E",
        "shadow_md":     "#05070C",
        "shadow_lg":     "#04060A",
        "nav_text":      "#8899B4",
        "nav_active_bg": "#222538",
        "nav_hover_bg":  "#1A1D28",
        "success":       "#34D399",
        "success_light": "#064E3B",
        "warning":       "#FBBF24",
        "warning_light": "#78350F",
        "danger":        "#F87171",
        "danger_light":  "#7F1D1D",
        "info":          "#818CF8",
        "info_light":    "#1E1B4B",
    }),

    # ─── 3. MIDNIGHT — Rich sapphire with teal/cyan accents ───
    ("✦  Midnight", {
        "bg_base":       "#070B18",
        "bg_surface":    "#0C1125",
        "bg_card":       "#111830",
        "bg_card_hover": "#182040",
        "bg_sidebar":    "#060918",
        "bg_input":      "#182040",
        "bg_row_alt":    "#0E1328",
        "bg_overlay":    "#1A2348",
        "accent":        "#22D3EE",
        "accent_dim":    "#06B6D4",
        "accent_glow":   "#083344",
        "accent_light":  "#67E8F9",
        "accent_ultra":  "#164E63",
        "accent2":       "#7DD3FC",
        "accent2_dim":   "#38BDF8",
        "text_primary":  "#E4EAF8",
        "text_secondary":"#8DA0C2",
        "text_muted":    "#4A5E80",
        "text_on_accent":"#03101C",
        "text_link":     "#22D3EE",
        "border":        "#1A2348",
        "border_focus":  "#22D3EE",
        "divider":       "#152038",
        "shadow_sm":     "#030510",
        "shadow_md":     "#02040C",
        "shadow_lg":     "#010308",
        "nav_text":      "#7090B8",
        "nav_active_bg": "#1A2348",
        "nav_hover_bg":  "#131A35",
        "success":       "#2DD4BF",
        "success_light": "#042F2E",
        "warning":       "#FCD34D",
        "warning_light": "#713F12",
        "danger":        "#FB7185",
        "danger_light":  "#881337",
        "info":          "#38BDF8",
        "info_light":    "#0C4A6E",
    }),
]

THEME_NAMES = [t[0] for t in _THEMES]
CURRENT_THEME_IDX: int = 0
_PALETTE_DEFAULTS = {f.name: f.default for f in PALETTE.__dataclass_fields__.values()}


def cycle_theme() -> str:
    """Advance to the next theme, mutate PALETTE in place, return new theme name."""
    global CURRENT_THEME_IDX
    CURRENT_THEME_IDX = (CURRENT_THEME_IDX + 1) % len(_THEMES)
    name, overrides = _THEMES[CURRENT_THEME_IDX]
    for field, default in _PALETTE_DEFAULTS.items():
        setattr(PALETTE, field, overrides.get(field, default))
    return name


def get_theme_index() -> int:
    """Return the current theme index (0=Light, 1=Dark, ...)."""
    return CURRENT_THEME_IDX


def is_dark_theme() -> bool:
    """Return True if the current theme has a dark background (Dark or Midnight)."""
    return CURRENT_THEME_IDX in (1, 2)


def lerp_color(hex1: str, hex2: str, t: float) -> str:
    """Linearly interpolate between two hex colours."""
    r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)
    r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


# ──────────────────────────────────────────────────────────
# TYPOGRAPHY (kept as tuples for QFont construction)
# ──────────────────────────────────────────────────────────
_FONT_FAMILY = "Segoe UI"
_FONT_MONO   = "Cascadia Code"

@dataclass(frozen=True)
class _Fonts:
    display:      tuple = (_FONT_FAMILY, 30, "bold")
    h1:           tuple = (_FONT_FAMILY, 22, "bold")
    h2:           tuple = (_FONT_FAMILY, 18, "bold")
    h3:           tuple = (_FONT_FAMILY, 15, "bold")
    h4:           tuple = (_FONT_FAMILY, 13, "bold")
    body:         tuple = (_FONT_FAMILY, 11, "normal")
    body_bold:    tuple = (_FONT_FAMILY, 11, "bold")
    body_semi:    tuple = (_FONT_FAMILY, 11, "bold")
    small:        tuple = (_FONT_FAMILY, 10, "normal")
    small_bold:   tuple = (_FONT_FAMILY, 10, "bold")
    tiny:         tuple = (_FONT_FAMILY, 9,  "normal")
    tiny_bold:    tuple = (_FONT_FAMILY, 9,  "bold")
    mono:         tuple = (_FONT_MONO,   10, "normal")
    nav:          tuple = (_FONT_FAMILY, 11, "normal")
    nav_bold:     tuple = (_FONT_FAMILY, 11, "bold")
    btn:          tuple = (_FONT_FAMILY, 11, "bold")
    btn_lg:       tuple = (_FONT_FAMILY, 13, "bold")
    label:        tuple = (_FONT_FAMILY, 10, "normal")
    label_bold:   tuple = (_FONT_FAMILY, 10, "bold")
    input:        tuple = (_FONT_FAMILY, 11, "normal")
    caption:      tuple = (_FONT_FAMILY, 9,  "normal")


FONTS = _Fonts()


# ──────────────────────────────────────────────────────────
# DIMENSIONS / SPACING
# ──────────────────────────────────────────────────────────
@dataclass(frozen=True)
class _Dims:
    sidebar_w:  int = 270
    topbar_h:   int = 68
    card_radius:int = 16
    btn_radius: int = 12
    btn_h:      int = 42
    btn_h_lg:   int = 48
    input_h:    int = 44
    input_r:    int = 12
    pad_xs:     int = 6
    pad_sm:     int = 14
    pad_md:     int = 22
    pad_lg:     int = 30
    pad_xl:     int = 48
    shadow_off: int = 4
    glow_w:     int = 2
    anim_ms:    int = 150


DIMS = _Dims()


# ──────────────────────────────────────────────────────────
# ROLE → ACCENT COLOUR MAP
# ──────────────────────────────────────────────────────────
ROLE_COLORS: Dict[str, str] = {
    "Administrator":   "#4361EE",
    "Manager":         "#1E293B",
    "Front-Desk Staff":"#10B981",
    "Finance Manager": "#F59E0B",
    "Maintenance Staff":"#EF4444",
}

# ──────────────────────────────────────────────────────────
# NAV ITEMS PER ROLE
# ──────────────────────────────────────────────────────────
NAV_ITEMS = {
    "Administrator": [
        ("DB", "Dashboard",    "dashboard"),
        ("TN", "Tenants",      "tenants"),
        ("AP", "Apartments",   "apartments"),
        ("PM", "Payments",     "payments"),
        ("MT", "Maintenance",  "maintenance"),
        ("CP", "Complaints",   "complaints"),
        ("RP", "Reports",      "reports"),
        ("US", "Users",        "users"),
    ],
    "Manager": [
        ("DB", "Dashboard",    "dashboard"),
        ("TN", "Tenants",      "tenants"),
        ("AP", "Apartments",   "apartments"),
        ("PM", "Payments",     "payments"),
        ("MT", "Maintenance",  "maintenance"),
        ("RP", "Reports",      "reports"),
    ],
    "Front-Desk Staff": [
        ("DB", "Dashboard",    "dashboard"),
        ("TN", "Tenants",      "tenants"),
        ("MT", "Maintenance",  "maintenance"),
        ("CP", "Complaints",   "complaints"),
    ],
    "Finance Manager": [
        ("DB", "Dashboard",    "dashboard"),
        ("PM", "Payments",     "payments"),
        ("RP", "Reports",      "reports"),
    ],
    "Maintenance Staff": [
        ("DB", "Dashboard",   "dashboard"),
        ("MT", "Maintenance", "maintenance"),
    ],
}


# ──────────────────────────────────────────────────────────
# GLOBAL QSS STYLESHEET
# ──────────────────────────────────────────────────────────
def get_global_qss() -> str:
    """Build and return the global QSS string from the current PALETTE."""
    _P = PALETTE
    _D = DIMS
    return f"""
/* ── Base ── */
* {{ font-family: "{_FONT_FAMILY}"; }}
QMainWindow {{ background-color: {_P.bg_base}; }}

/* ── Scroll Area ── */
QScrollArea {{ border: none; background-color: {_P.bg_surface}; }}

/* ── Scrollbar ── */
QScrollBar:vertical {{
    background: {_P.bg_surface}; width: 10px; margin: 2px; border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {lerp_color(_P.accent, _P.bg_surface, 0.72)};
    border-radius: 5px; min-height: 36px;
}}
QScrollBar::handle:vertical:hover {{ background: {lerp_color(_P.accent, _P.bg_surface, 0.50)}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {_P.bg_surface}; height: 10px; margin: 2px; border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {lerp_color(_P.accent, _P.bg_surface, 0.72)};
    border-radius: 5px; min-width: 36px;
}}
QScrollBar::handle:horizontal:hover {{ background: {lerp_color(_P.accent, _P.bg_surface, 0.50)}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── QLineEdit ── */
QLineEdit {{
    background-color: {_P.bg_input}; border: 1.5px solid {_P.border};
    border-radius: {_D.input_r}px; padding: 10px 16px;
    font-size: 12px; color: {_P.text_primary};
    selection-background-color: {_P.accent_glow}; selection-color: {_P.accent};
}}
QLineEdit:focus {{
    border: 2px solid {_P.border_focus};
    background-color: {lerp_color(_P.bg_input, _P.accent_glow, 0.08)};
}}
QLineEdit:disabled {{ background-color: {_P.bg_overlay}; color: {_P.text_muted}; }}

/* ── QComboBox ── */
QComboBox {{
    background-color: {_P.bg_input}; border: 1.5px solid {_P.border};
    border-radius: {_D.input_r}px; padding: 10px 14px;
    font-size: 12px; color: {_P.text_primary}; min-height: 24px;
}}
QComboBox:focus {{ border: 2px solid {_P.border_focus}; }}
QComboBox::drop-down {{ border: none; padding-right: 14px; }}
QComboBox::down-arrow {{
    width: 0; height: 0; border-left: 5px solid transparent;
    border-right: 5px solid transparent; border-top: 7px solid {_P.text_muted};
}}
QComboBox QAbstractItemView {{
    background-color: {_P.bg_card}; border: 1px solid {_P.border};
    border-radius: 10px; padding: 6px;
    selection-background-color: {_P.accent_glow}; selection-color: {_P.accent};
    font-size: 12px; outline: 0;
}}

/* ── QPushButton — Primary ── */
QPushButton[cssClass="primary"] {{
    background-color: {_P.accent}; color: {_P.text_on_accent}; border: none;
    border-radius: {_D.btn_radius}px; padding: 11px 28px;
    font-size: 12px; font-weight: bold; min-height: 22px;
}}
QPushButton[cssClass="primary"]:hover {{ background-color: {_P.accent_dim}; }}
QPushButton[cssClass="primary"]:pressed {{ background-color: {lerp_color(_P.accent_dim, '#000000', 0.15)}; }}

/* ── QPushButton — Outline ── */
QPushButton[cssClass="outline"] {{
    background-color: {_P.bg_card}; color: {_P.accent};
    border: 2px solid {_P.accent}; border-radius: {_D.btn_radius}px;
    padding: 11px 22px; font-size: 12px; font-weight: bold; min-height: 22px;
}}
QPushButton[cssClass="outline"]:hover {{
    background-color: {_P.accent_glow}; border-color: {_P.accent_dim};
}}
QPushButton[cssClass="outline"]:pressed {{ background-color: {_P.accent_ultra}; }}

/* ── QPushButton — Danger ── */
QPushButton[cssClass="danger"] {{
    background-color: {_P.danger}; color: #FFFFFF; border: none;
    border-radius: {_D.btn_radius}px; padding: 11px 22px;
    font-size: 12px; font-weight: bold; min-height: 22px;
}}
QPushButton[cssClass="danger"]:hover {{ background-color: #DC2626; }}
QPushButton[cssClass="danger"]:pressed {{ background-color: #B91C1C; }}

/* ── QPushButton — Success ── */
QPushButton[cssClass="success"] {{
    background-color: {_P.success}; color: #FFFFFF; border: none;
    border-radius: {_D.btn_radius}px; padding: 11px 22px;
    font-size: 12px; font-weight: bold; min-height: 22px;
}}
QPushButton[cssClass="success"]:hover {{ background-color: #059669; }}
QPushButton[cssClass="success"]:pressed {{ background-color: #047857; }}

/* ── QPushButton — Warning ── */
QPushButton[cssClass="warning"] {{
    background-color: {_P.warning}; color: #1A1A1A; border: none;
    border-radius: {_D.btn_radius}px; padding: 11px 22px;
    font-size: 12px; font-weight: bold; min-height: 22px;
}}
QPushButton[cssClass="warning"]:hover {{ background-color: #D97706; }}
QPushButton[cssClass="warning"]:pressed {{ background-color: #B45309; }}

/* ── QPushButton — Ghost ── */
QPushButton[cssClass="ghost"] {{
    background-color: transparent; color: {_P.text_secondary}; border: none;
    padding: 8px 14px; font-size: 12px;
}}
QPushButton[cssClass="ghost"]:hover {{
    color: {_P.text_primary}; background-color: {_P.bg_card_hover};
    border-radius: 8px;
}}

/* ── QTableView ── */
QTableView {{
    background-color: {_P.bg_card}; border: none; gridline-color: {_P.divider};
    font-size: 12px; selection-background-color: rgba(67,97,238,0.14);
    selection-color: {_P.accent}; alternate-background-color: {_P.bg_row_alt}; outline: 0;
}}
QTableView::item {{
    padding: 8px 14px; border-bottom: 1px solid {_P.divider};
}}
QTableView::item:hover {{
    background-color: {lerp_color(_P.accent_glow, _P.bg_card, 0.70)};
}}
QTableView::item:selected {{
    background-color: rgba(67,97,238,0.12); color: {_P.accent};
}}
QHeaderView::section {{
    background-color: {_P.bg_surface}; color: {_P.text_secondary}; border: none;
    border-bottom: 2px solid {_P.divider}; padding: 12px 14px;
    font-weight: bold; font-size: 11px; text-transform: uppercase;
}}
QHeaderView::section:hover {{ background-color: {_P.divider}; color: {_P.text_primary}; }}

/* ── QRadioButton ── */
QRadioButton {{
    color: {_P.text_secondary}; font-size: 11px; spacing: 8px;
}}
QRadioButton::indicator {{
    width: 16px; height: 16px; border-radius: 8px;
    border: 2px solid {_P.border}; background: {_P.bg_card};
}}
QRadioButton::indicator:checked {{ background: {_P.accent}; border-color: {_P.accent}; }}
QRadioButton::indicator:hover {{ border-color: {_P.accent}; }}

/* ── QCheckBox ── */
QCheckBox {{
    color: {_P.text_primary}; font-size: 12px; spacing: 10px;
}}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 5px;
    border: 2px solid {_P.border}; background: {_P.bg_card};
}}
QCheckBox::indicator:checked {{ background: {_P.accent}; border-color: {_P.accent}; }}

/* ── QProgressBar ── */
QProgressBar {{
    background-color: {_P.border}; border: none; border-radius: 7px;
    max-height: 14px; text-align: center; font-size: 0px;
}}
QProgressBar::chunk {{ background-color: {_P.accent}; border-radius: 7px; }}

/* ── QDialog ── */
QDialog {{ background-color: {_P.bg_card}; border-radius: 12px; }}

/* ── QMessageBox ── */
QMessageBox {{ background-color: {_P.bg_card}; }}
QMessageBox QLabel {{ color: {_P.text_primary}; font-size: 12px; }}
QMessageBox QPushButton {{
    background-color: {_P.accent}; color: #FFFFFF; border: none;
    border-radius: 10px; padding: 10px 28px; font-weight: bold; min-width: 90px;
}}
QMessageBox QPushButton:hover {{ background-color: {_P.accent_dim}; }}

/* ── Card Frame ── */
QFrame[cssClass="card"] {{
    background-color: {_P.bg_card}; border: 1px solid {_P.border};
    border-radius: {_D.card_radius}px;
}}

/* ── QToolTip ── */
QToolTip {{
    background-color: {_P.bg_sidebar}; color: #FFFFFF;
    border: 1px solid {_P.accent}; border-radius: 8px;
    padding: 8px 14px; font-size: 11px;
}}

/* ── Glass Panel ── */
QFrame[cssClass="glass"] {{
    background-color: rgba({int(_P.bg_card[1:3], 16)}, {int(_P.bg_card[3:5], 16)}, {int(_P.bg_card[5:7], 16)}, 220);
    border: 1px solid {lerp_color(_P.border, _P.accent, 0.15)};
    border-radius: {_D.card_radius}px;
}}
"""

GLOBAL_QSS = get_global_qss()  # backward-compat alias