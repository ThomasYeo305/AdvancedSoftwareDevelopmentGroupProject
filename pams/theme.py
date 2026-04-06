# ============================================================
# PAMS - Paragon Apartment Management System
# theme.py  — Design tokens, palette, and PySide6 QSS
# Corporate SaaS — Professional Property-Tech Aesthetic
# ============================================================

from dataclasses import dataclass   # imports dataclass decorator so we can define palette/font/dimension classes with less boilerplate
from typing import Dict              # imports Dict for type hints used in the ROLE_COLORS dictionary


# ──────────────────────────────────────────────────────────
# COLOUR PALETTE  (Professional Light Theme — Polished)
# ──────────────────────────────────────────────────────────
@dataclass
class _Palette:
    # --- Background colours ---
    bg_base:       str = "#EDEEF4"   # very light grey-blue used as the outermost window background behind all cards
    bg_surface:    str = "#F0F2F8"   # slightly brighter surface colour used for scroll areas and secondary panels
    bg_card:       str = "#FFFFFF"   # pure white used as the background for every floating card and form panel
    bg_card_hover: str = "#F7F8FD"   # very faint blue-tinted white shown when hovering over a card
    bg_sidebar:    str = "#0C1F3F"   # deep navy used as the sidebar and topbar background
    bg_input:      str = "#F5F7FC"   # pale blue-white used as the fill colour inside text inputs and dropdowns
    bg_row_alt:    str = "#F6F8FC"   # alternating row shade (slightly off-white) used in table rows for readability
    bg_overlay:    str = "#E8E8E8"   # medium grey used for disabled input backgrounds and overlay masks

    # --- Accent colours (brand identity, calls-to-action) ---
    accent:        str = "#4361EE"   # primary indigo-blue; used for main buttons, active sidebar items, and links
    accent_dim:    str = "#3651D4"   # slightly darker shade of accent; used for the hover state of primary buttons
    accent_glow:   str = "#E0E7FF"   # very pale indigo; used as the background of hovered dropdown items and focus rings
    accent_light:  str = "#818CF8"   # lighter indigo; used in dark-mode as the main accent
    accent_ultra:  str = "#C7D2FE"   # pastel indigo; used for pressed-state backgrounds of outline buttons
    accent2:       str = "#1A2F54"   # deep navy used for the 'PARAGON' brand heading on the login right panel
    accent2_dim:   str = "#0F2040"   # darker navy; used for hover states on accent2-coloured elements

    # --- Semantic colours (status indicators) ---
    success:       str = "#10B981"   # teal-green used for 'Paid', 'Active', 'Occupied', and success toast notifications
    success_light: str = "#D1FAE5"   # pale green background used for success badges and highlight boxes
    warning:       str = "#F59E0B"   # amber-yellow used for 'Pending', 'Maintenance', and warning toasts
    warning_light: str = "#FEF3C7"   # pale yellow background used for warning badges
    danger:        str = "#EF4444"   # red used for 'Overdue', delete buttons, and error messages
    danger_light:  str = "#FEE2E2"   # pale red background used for danger badges
    info:          str = "#6366F1"   # medium indigo used for 'In Progress' status and info toasts
    info_light:    str = "#E0E7FF"   # pale indigo background used for info badges

    # --- Text colours ---
    text_primary:  str = "#111827"   # near-black used for all main body text and headings; high contrast on white
    text_secondary:str = "#4B5563"   # dark grey used for secondary labels, form captions, and table headers
    text_muted:    str = "#9CA3AF"   # medium grey used for placeholder text, timestamps, and disabled labels
    text_on_accent:str = "#FFFFFF"   # pure white used for text drawn directly on coloured buttons (ensures readability)
    text_link:     str = "#4361EE"   # same as accent; used for hyperlink-style labels

    # --- Border and divider colours ---
    border:        str = "#E2E5ED"   # light grey-blue used for card borders and input outlines in the resting state
    border_focus:  str = "#4361EE"   # accent indigo; replaces border colour when an input or control has keyboard focus
    divider:       str = "#E5E7EF"   # very light grey line used between rows in tables and between sections in cards

    # --- Shadow colours (used by drop-shadow effects) ---
    shadow_sm:     str = "#F4F4F4"   # near-white shadow colour for very subtle small shadows
    shadow_md:     str = "#EDEDED"   # light grey shadow colour for medium card shadows
    shadow_lg:     str = "#E0E0E0"   # medium grey shadow colour for larger elevated panels

    # --- Sidebar navigation colours ---
    nav_text:      str = "#94A3C0"   # muted blue-grey used for unselected navigation item labels in the sidebar
    nav_active_bg: str = "#1E3A65"   # dark navy highlight applied behind the currently selected sidebar nav item
    nav_active_text:str = "#FFFFFF"  # pure white text used on the active (selected) sidebar nav item
    nav_hover_bg:  str = "#162F55"   # slightly darker navy used as the hover background on sidebar nav items


PALETTE = _Palette()   # creates the single global palette instance that all views import as 'P' to read colour values


# ──────────────────────────────────────────────────────────
# THEME VARIANTS
# ──────────────────────────────────────────────────────────
_THEMES: list[tuple[str, dict]] = [
    # ─── 1. LIGHT — Refined warm ivory with indigo accent ───
    ("☀  Light", {}),   # light theme has no overrides; it simply uses all the default values defined in _Palette above

    # ─── 2. DARK — Deep obsidian with violet/indigo accents ───
    ("🌙  Dark", {
        "bg_base":       "#0B0D14",   # replaces the light background with a near-black base for dark mode
        "bg_surface":    "#10121A",   # replaces the surface with a very dark charcoal for dark mode panels
        "bg_card":       "#161822",   # dark navy-black used as the card background in dark mode
        "bg_card_hover": "#1C1F2E",   # slightly lighter navy for card hover states in dark mode
        "bg_sidebar":    "#080A12",   # deepest black used for the sidebar in dark mode
        "bg_input":      "#1C1F2E",   # dark navy used as the input field background in dark mode
        "bg_row_alt":    "#12141C",   # very dark alternating row colour in dark mode tables
        "bg_overlay":    "#222538",   # dark overlay used for disabled fields in dark mode
        "accent":        "#818CF8",   # switches to a lighter indigo so the accent is visible on dark backgrounds
        "accent_dim":    "#6366F1",   # slightly darker light indigo for hover states in dark mode
        "accent_glow":   "#1E1B4B",   # dark indigo glow background for focus/hover effects in dark mode
        "accent_light":  "#A5B4FC",   # lightest indigo variant for dark mode highlights
        "accent_ultra":  "#312E81",   # deep indigo pressed-state background in dark mode
        "accent2":       "#94A3B8",   # replaces deep navy with a cool grey so the brand text remains visible in dark mode
        "accent2_dim":   "#64748B",   # slightly darker grey for hover states of accent2 elements in dark mode
        "text_primary":  "#ECF0F8",   # near-white replaces the near-black text so it reads on dark backgrounds
        "text_secondary":"#A0AEC0",   # light cool grey replaces dark grey for secondary text in dark mode
        "text_muted":    "#5A6578",   # darker muted colour for placeholder and disabled text in dark mode
        "text_on_accent":"#FFFFFF",   # still pure white; buttons remain white-text regardless of theme
        "text_link":     "#818CF8",   # matches the dark-mode accent so links are visible on dark cards
        "border":        "#222538",   # very dark border colour so card outlines are subtle but present in dark mode
        "border_focus":  "#818CF8",   # light indigo focus ring so inputs show clearly when focused in dark mode
        "divider":       "#1C1F2E",   # near-black divider lines between table rows in dark mode
        "shadow_sm":     "#06080E",   # extremely dark shadow so small cards still show depth in dark mode
        "shadow_md":     "#05070C",   # very dark medium shadow for dark mode cards
        "shadow_lg":     "#04060A",   # darkest shadow for large elevated panels in dark mode
        "nav_text":      "#8899B4",   # slightly brighter muted text for sidebar labels in dark mode
        "nav_active_bg": "#222538",   # dark indigo-navy highlight for the active sidebar item in dark mode
        "nav_hover_bg":  "#1A1D28",   # slightly lighter dark background for sidebar hover in dark mode
        "success":       "#34D399",   # brighter green so success badges are readable on dark backgrounds
        "success_light": "#064E3B",   # dark green background for success badges in dark mode
        "warning":       "#FBBF24",   # bright amber so warning states are easily seen in dark mode
        "warning_light": "#78350F",   # dark warm brown background for warning badges in dark mode
        "danger":        "#F87171",   # bright coral-red so error states are easy to see in dark mode
        "danger_light":  "#7F1D1D",   # dark red background for error badges in dark mode
        "info":          "#818CF8",   # light indigo for info/in-progress badges in dark mode
        "info_light":    "#1E1B4B",   # dark indigo background for info badges in dark mode
    }),
]

THEME_NAMES = [t[0] for t in _THEMES]  # builds a list of just the theme display names, e.g. ["☀  Light", "🌙  Dark"]
CURRENT_THEME_IDX: int = 0              # tracks which theme is active right now; 0 = Light (the default)
_PALETTE_DEFAULTS = {f.name: f.default for f in PALETTE.__dataclass_fields__.values()}  # captures the original default values of every palette field so we can restore them when switching to Light


def cycle_theme() -> str:
    """Advance to the next theme, mutate PALETTE in place, return new theme name."""
    global CURRENT_THEME_IDX                                                    # declares we're modifying the module-level counter, not a local variable
    CURRENT_THEME_IDX = (CURRENT_THEME_IDX + 1) % len(_THEMES)                 # advances the index by 1 and wraps back to 0 after the last theme
    name, overrides = _THEMES[CURRENT_THEME_IDX]                               # unpacks the new theme's display name and its colour override dictionary
    for field, default in _PALETTE_DEFAULTS.items():                           # loops through every colour slot in the palette
        setattr(PALETTE, field, overrides.get(field, default))                 # if the theme overrides this field use that value, otherwise restore the Light default
    return name                                                                 # returns the new theme's display name so the title bar can show e.g. "│  🌙  Dark"


def get_theme_index() -> int:
    """Return the current theme index (0=Light, 1=Dark, ...)."""
    return CURRENT_THEME_IDX   # returns the integer index so callers can check which theme is currently active


def is_dark_theme() -> bool:
    """Return True if the current theme is Dark (index 1)."""
    return CURRENT_THEME_IDX == 1   # returns True only when the Dark theme (index 1) is active, used for conditional colour adjustments


def lerp_color(hex1: str, hex2: str, t: float) -> str:
    """Linearly interpolate between two hex colours."""
    r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)  # splits hex1 into its red, green, blue components (0-255)
    r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)  # splits hex2 into its red, green, blue components (0-255)
    r = round(r1 + (r2 - r1) * t)   # blends the red channel: t=0 gives hex1's red, t=1 gives hex2's red, t=0.5 gives the midpoint
    g = round(g1 + (g2 - g1) * t)   # blends the green channel the same way
    b = round(b1 + (b2 - b1) * t)   # blends the blue channel the same way
    return f"#{r:02x}{g:02x}{b:02x}"  # formats the result back as a lowercase hex colour string like "#7b9aef"


# ──────────────────────────────────────────────────────────
# TYPOGRAPHY (kept as tuples for QFont construction)
# ──────────────────────────────────────────────────────────
_FONT_FAMILY = "Segoe UI"       # sets the preferred font family for all UI text (falls back to Arial/Helvetica on non-Windows)
_FONT_MONO   = "Cascadia Code"  # sets the monospace font family used for code/numeric displays

@dataclass(frozen=True)
class _Fonts:
    # Each tuple is (family, size_in_pt, weight_string) — used by qfont() in widgets.py to build QFont objects
    display:      tuple = (_FONT_FAMILY, 30, "bold")    # very large bold heading used for major titles (e.g. report headers)
    h1:           tuple = (_FONT_FAMILY, 22, "bold")    # large bold heading; used for section/page titles
    h2:           tuple = (_FONT_FAMILY, 18, "bold")    # medium bold heading; used for card titles
    h3:           tuple = (_FONT_FAMILY, 15, "bold")    # smaller bold heading; used for sub-section labels
    h4:           tuple = (_FONT_FAMILY, 13, "bold")    # small bold heading; used for table column headers inside cards
    body:         tuple = (_FONT_FAMILY, 11, "normal")  # standard body text; used for most labels and descriptions
    body_bold:    tuple = (_FONT_FAMILY, 11, "bold")    # bold body text; used for highlighted labels and important values
    body_semi:    tuple = (_FONT_FAMILY, 11, "bold")    # same as body_bold; provided as a named alias for semantic clarity
    small:        tuple = (_FONT_FAMILY, 10, "normal")  # small text; used for captions below KPI values and minor notes
    small_bold:   tuple = (_FONT_FAMILY, 10, "bold")    # small bold text; used for badge labels and status chips
    tiny:         tuple = (_FONT_FAMILY, 9,  "normal")  # very small text; used for timestamps and footer information
    tiny_bold:    tuple = (_FONT_FAMILY, 9,  "bold")    # very small bold text; used for upper-case section labels in the sidebar
    mono:         tuple = (_FONT_MONO,   10, "normal")  # monospace font; used for IDs, NI numbers, and code-like numeric values
    nav:          tuple = (_FONT_FAMILY, 11, "normal")  # sidebar navigation item label font (non-selected items)
    nav_bold:     tuple = (_FONT_FAMILY, 11, "bold")    # sidebar navigation item label font (selected item is shown bold)
    btn:          tuple = (_FONT_FAMILY, 11, "bold")    # standard button label font; all buttons use this size
    btn_lg:       tuple = (_FONT_FAMILY, 13, "bold")    # larger button font used for primary call-to-action buttons like 'SIGN IN'
    label:        tuple = (_FONT_FAMILY, 10, "normal")  # form field label above inputs (e.g. "USERNAME")
    label_bold:   tuple = (_FONT_FAMILY, 10, "bold")    # bold field label used to draw extra attention to required fields
    input:        tuple = (_FONT_FAMILY, 11, "normal")  # text shown inside input fields as the user types
    caption:      tuple = (_FONT_FAMILY, 9,  "normal")  # small helper text shown below inputs or beside form elements


FONTS = _Fonts()   # creates the single global FONTS instance that all views import and use via F.h1, F.body, etc.


# ──────────────────────────────────────────────────────────
# DIMENSIONS / SPACING
# ──────────────────────────────────────────────────────────
@dataclass(frozen=True)
class _Dims:
    sidebar_w:  int = 270   # fixed width in pixels of the left navigation sidebar
    topbar_h:   int = 68    # fixed height in pixels of the top search/profile bar
    card_radius:int = 16    # corner radius in pixels applied to all card and panel widgets
    btn_radius: int = 12    # corner radius in pixels applied to all buttons
    btn_h:      int = 42    # standard button height in pixels (used for most action buttons)
    btn_h_lg:   int = 48    # larger button height in pixels (used for the main Sign In button on the login screen)
    input_h:    int = 44    # standard input field height in pixels so all fields align consistently
    input_r:    int = 12    # corner radius in pixels applied to all input fields and dropdowns
    pad_xs:     int = 6     # extra-small padding (6px); used for tight gaps between closely related controls
    pad_sm:     int = 14    # small padding (14px); used for compact inner content padding inside cards
    pad_md:     int = 22    # medium padding (22px); standard inner content margin inside cards and sections
    pad_lg:     int = 30    # large padding (30px); used for section-level outer margins
    pad_xl:     int = 48    # extra-large padding (48px); used for prominent whitespace above major headings
    shadow_off: int = 4     # vertical offset in pixels for drop shadows on cards (creates depth illusion)
    glow_w:     int = 2     # stroke width in pixels for focus-glow borders drawn around focused inputs
    anim_ms:    int = 150   # default animation duration in milliseconds for hover/press transitions


DIMS = _Dims()   # creates the single global DIMS instance imported as 'D' throughout all view files


# ──────────────────────────────────────────────────────────
# ROLE → ACCENT COLOUR MAP
# ──────────────────────────────────────────────────────────
ROLE_COLORS: Dict[str, str] = {
    "Administrator":   "#4361EE",    # indigo accent applied to Admin sidebar, banners, and avatar circles
    "Manager":         "#1E293B",    # dark slate applied to Manager UI elements
    "Front-Desk Staff":"#10B981",    # teal-green accent for Front-Desk Staff
    "Finance Manager": "#F59E0B",    # amber accent for Finance Manager views (money/value association)
    "Maintenance Staff":"#EF4444",   # red accent for Maintenance Staff views (alert, urgency)
}

# ──────────────────────────────────────────────────────────
# NAV ITEMS PER ROLE
# ──────────────────────────────────────────────────────────
NAV_ITEMS = {
    # Each tuple is (icon_placeholder, display_label, route_key)
    # route_key is used by MainApp._navigate() to determine which view to show
    "Administrator": [
        ("", "Dashboard",    "dashboard"),    # shows the admin KPI overview with occupancy, rent totals, and open issues
        ("", "Tenants",      "tenants"),      # shows the tenant management view for adding, editing, and viewing tenants
        ("", "Apartments",   "apartments"),   # shows the apartment management view for adding and updating flat details
        ("", "Payments",     "payments"),     # shows the payments and invoicing view for tracking rent and overdue amounts
        ("", "Maintenance",  "maintenance"),  # shows the maintenance requests view for tracking and resolving repair jobs
        ("", "Complaints",   "complaints"),   # shows the complaints management view for tenant-reported complaints
        ("", "Reports",      "reports"),      # shows the reporting view with occupancy, financial, and maintenance charts
        ("", "Users",        "users"),        # shows the user account management view (add/edit/deactivate staff accounts)
    ],
    "Manager": [
        ("", "Dashboard",    "dashboard"),    # shows the manager's multi-city KPI overview with city-level performance rings
        ("", "Tenants",      "tenants"),      # shows full tenant management — managers can view all cities
        ("", "Apartments",   "apartments"),   # shows apartment management across all managed locations
        ("", "Payments",     "payments"),     # shows payment tracking with collected vs. pending breakdown
        ("", "Maintenance",  "maintenance"),  # shows maintenance requests; managers can assign and track resolutions
        ("", "Reports",      "reports"),      # shows the full cross-city performance report (SD5 generateReport)
    ],
    "Front-Desk Staff": [
        ("", "Dashboard",    "dashboard"),    # shows the front-desk daily summary (active tenants, open maintenance)
        ("", "Tenants",      "tenants"),      # shows tenant records — front desk can register new tenants and view details
        ("", "Maintenance",  "maintenance"),  # shows maintenance requests — front desk can log new issues
        ("", "Complaints",   "complaints"),   # shows complaints — front desk can receive and forward tenant complaints
    ],
    "Finance Manager": [
        ("", "Dashboard",    "dashboard"),    # shows a finance-focused dashboard with rent collected vs. pending
        ("", "Payments",     "payments"),     # shows full payment management including generating and marking invoices paid
        ("", "Reports",      "reports"),      # shows financial reports including rent collected, pending, and maintenance costs
    ],
    "Maintenance Staff": [
        ("", "Dashboard",   "dashboard"),     # shows the maintenance staff dashboard with their assigned open jobs
        ("", "Maintenance", "maintenance"),   # shows all maintenance requests; staff can update status and log resolution costs
    ],
}


# ──────────────────────────────────────────────────────────
# GLOBAL QSS STYLESHEET
# ──────────────────────────────────────────────────────────
def get_global_qss() -> str:
    """Build and return the global QSS string from the current PALETTE."""
    _P = PALETTE   # creates a local alias to the global PALETTE so the f-string below can reference it as _P
    _D = DIMS      # creates a local alias to DIMS so spacing/radius values can be inserted into the QSS string
    return f"""
/* ── Base ── */
* {{ font-family: "{_FONT_FAMILY}"; }}                        /* applies Segoe UI as the default font to every single widget in the app */
QMainWindow {{ background-color: {_P.bg_base}; }}             /* sets the outermost window background to the light grey-blue base colour */

/* ── Scroll Area ── */
QScrollArea {{ border: none; background-color: {_P.bg_surface}; }}  /* removes the border from scroll areas and sets their background to the surface colour */

/* ── Scrollbar ── */
QScrollBar:vertical {{
    background: {_P.bg_surface}; width: 10px; margin: 2px; border-radius: 5px;  /* styles the vertical scrollbar track as a narrow rounded strip in the surface colour */
}}
QScrollBar::handle:vertical {{
    background: {lerp_color(_P.accent, _P.bg_surface, 0.72)};  /* colours the draggable scrollbar thumb as a faint tint of the accent colour */
    border-radius: 5px; min-height: 36px;                        /* rounds the scrollbar thumb corners and ensures it is never shorter than 36px */
}}
QScrollBar::handle:vertical:hover {{ background: {lerp_color(_P.accent, _P.bg_surface, 0.50)}; }}  /* makes the scrollbar thumb darker when the mouse hovers over it */
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}                       /* hides the up/down arrow buttons on the scrollbar so it looks minimal */
QScrollBar:horizontal {{
    background: {_P.bg_surface}; height: 10px; margin: 2px; border-radius: 5px;  /* styles the horizontal scrollbar track the same way as the vertical one */
}}
QScrollBar::handle:horizontal {{
    background: {lerp_color(_P.accent, _P.bg_surface, 0.72)};  /* colours the horizontal scrollbar thumb with the same faint accent tint */
    border-radius: 5px; min-width: 36px;                         /* rounds the corners and ensures the thumb is never narrower than 36px */
}}
QScrollBar::handle:horizontal:hover {{ background: {lerp_color(_P.accent, _P.bg_surface, 0.50)}; }}  /* darkens the horizontal thumb on hover */
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}                      /* hides the left/right arrow buttons on the horizontal scrollbar */

/* ── QLineEdit ── */
QLineEdit {{
    background-color: {_P.bg_input}; border: 1.5px solid {_P.border};  /* gives text inputs a pale background and a light grey border */
    border-radius: {_D.input_r}px; padding: 10px 16px;                  /* rounds the input corners by 12px and adds inner padding for breathing room */
    font-size: 12px; color: {_P.text_primary};                          /* sets the typing text to 12pt in the main near-black text colour */
    selection-background-color: {_P.accent_glow}; selection-color: {_P.accent};  /* when text is selected it gets a pale indigo background with accent-colour text */
}}
QLineEdit:focus {{
    border: 2px solid {_P.border_focus};                                        /* thickens the border to 2px and switches it to accent indigo when the input is focused */
    background-color: {lerp_color(_P.bg_input, _P.accent_glow, 0.08)};         /* very slightly tints the input background with indigo on focus to reinforce the focus state */
}}
QLineEdit:disabled {{ background-color: {_P.bg_overlay}; color: {_P.text_muted}; }}  /* greys out disabled inputs with a medium-grey background and muted text colour */

/* ── QComboBox ── */
QComboBox {{
    background-color: {_P.bg_input}; border: 1.5px solid {_P.border};           /* gives dropdowns the same pale background and grey border as text inputs */
    border-radius: {_D.input_r}px; padding: 10px 14px;                          /* rounds dropdown corners and adds inner padding to match text inputs */
    font-size: 12px; color: {_P.text_primary}; min-height: 24px;                /* sets dropdown text to 12pt in the primary text colour with a minimum content height */
}}
QComboBox:focus {{ border: 2px solid {_P.border_focus}; }}                      /* switches the dropdown border to accent indigo when it has keyboard focus */
QComboBox::drop-down {{ border: none; padding-right: 14px; }}                   /* hides the default dropdown arrow button border and shifts it 14px from the right edge */
QComboBox::down-arrow {{
    width: 0; height: 0; border-left: 5px solid transparent;                    /* uses CSS triangle trick: zero-size box with transparent left side */
    border-right: 5px solid transparent; border-top: 7px solid {_P.text_muted}; /* completes the downward-pointing triangle arrow using the muted text colour */
}}
QComboBox QAbstractItemView {{
    background-color: {_P.bg_card}; border: 1px solid {_P.border};              /* styles the dropdown popup menu with a white card background and thin border */
    border-radius: 10px; padding: 6px;                                            /* rounds the popup's corners by 10px and adds inner padding around the items list */
    color: {_P.text_primary};                                                     /* explicitly sets item text to the near-black primary colour so items are readable on the white background */
    selection-background-color: {_P.accent_glow}; selection-color: {_P.accent}; /* highlights the hovered/selected dropdown option with a pale indigo background */
    font-size: 12px; outline: 0;                                                  /* sets item text to 12pt and removes the default keyboard-focus dotted outline */
}}
QComboBox QAbstractItemView::item {{
    color: {_P.text_primary}; padding: 8px 12px; min-height: 28px;              /* ensures every individual dropdown row has readable dark text with generous padding */
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: {_P.accent_glow}; color: {_P.accent};                     /* tints a hovered item with pale indigo and switches the text to accent colour */
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: {_P.accent_glow}; color: {_P.accent};                     /* matches the selected item style to the hover style for consistency */
}}

/* ── QPushButton — Primary ── */
QPushButton[cssClass="primary"] {{
    background-color: {_P.accent}; color: {_P.text_on_accent}; border: none;    /* gives primary buttons a solid indigo fill with white text and no border */
    border-radius: {_D.btn_radius}px; padding: 11px 28px;                        /* rounds primary button corners by 12px and adds horizontal/vertical padding */
    font-size: 12px; font-weight: bold; min-height: 22px;
}}
QPushButton[cssClass="primary"]:hover {{ background-color: {_P.accent_dim}; }}
QPushButton[cssClass="primary"]:pressed {{ background-color: {lerp_color(_P.accent_dim, '#000000', 0.15)}; }}

/* ── QPushButton — Outline ── */
QPushButton[cssClass="outline"] {{
    background-color: {_P.bg_card}; color: {_P.accent};
    border: 2px solid {_P.accent}; border-radius: {_D.btn_radius}px;
    padding: 11px 22px; font-size: 12px; font-weight: bold; min-height: 22px;  /* sets button padding and font to match primary buttons, just with transparent bg */
}}
QPushButton[cssClass="outline"]:hover {{
    background-color: {_P.accent_glow}; border-color: {_P.accent_dim};         /* on hover, fills the outline button with a pale indigo glow and darkens the border */
}}
QPushButton[cssClass="outline"]:pressed {{ background-color: {_P.accent_ultra}; }}  /* on press, fills with a deeper indigo to give tactile feedback */

/* ── QPushButton — Danger ── */
QPushButton[cssClass="danger"] {{
    background-color: {_P.danger}; color: #FFFFFF; border: none;               /* gives danger buttons a red background with white text — used for delete/destructive actions */
    border-radius: {_D.btn_radius}px; padding: 11px 22px;
    font-size: 12px; font-weight: bold; min-height: 22px;
}}
QPushButton[cssClass="danger"]:hover {{ background-color: #DC2626; }}           /* darkens the danger button red slightly on hover */
QPushButton[cssClass="danger"]:pressed {{ background-color: #B91C1C; }}         /* darkens further on press to give click feedback */

/* ── QPushButton — Success ── */
QPushButton[cssClass="success"] {{
    background-color: {_P.success}; color: #FFFFFF; border: none;              /* gives success buttons a teal-green background with white text — used for confirm/save actions */
    border-radius: {_D.btn_radius}px; padding: 11px 22px;
    font-size: 12px; font-weight: bold; min-height: 22px;
}}
QPushButton[cssClass="success"]:hover {{ background-color: #059669; }}           /* darkens the green on hover */
QPushButton[cssClass="success"]:pressed {{ background-color: #047857; }}         /* darkens further on press */

/* ── QPushButton — Warning ── */
QPushButton[cssClass="warning"] {{
    background-color: {_P.warning}; color: #1A1A1A; border: none;              /* gives warning buttons an amber background with near-black text (amber is too bright for white text) */
    border-radius: {_D.btn_radius}px; padding: 11px 22px;
    font-size: 12px; font-weight: bold; min-height: 22px;
}}
QPushButton[cssClass="warning"]:hover {{ background-color: #D97706; }}           /* darkens the amber on hover */
QPushButton[cssClass="warning"]:pressed {{ background-color: #B45309; }}         /* darkens to a burnt orange on press */

/* ── QPushButton — Ghost ── */
QPushButton[cssClass="ghost"] {{
    background-color: transparent; color: {_P.text_secondary}; border: none;   /* ghost buttons have no background or border — they look like plain text until hovered */
    padding: 8px 14px; font-size: 12px;
}}
QPushButton[cssClass="ghost"]:hover {{
    color: {_P.text_primary}; background-color: {_P.bg_card_hover};            /* on hover, ghost buttons get a faint card-colour background and darker text */
    border-radius: 8px;                                                          /* rounds the hover background so it looks like a pill on hover */
}}

/* ── QTableView ── */
QTableView {{
    background-color: {_P.bg_card}; border: none; gridline-color: {_P.divider};   /* makes the table white with no outer border and soft divider lines between columns */
    font-size: 12px; selection-background-color: rgba(67,97,238,0.14);             /* sets table text to 12pt and uses a semi-transparent indigo for selected row highlights */
    selection-color: {_P.accent}; alternate-background-color: {_P.bg_row_alt}; outline: 0;  /* colours selected cell text indigo, uses an off-white alternate row shade, hides focus outline */
}}
QTableView::item {{
    padding: 8px 14px; border-bottom: 1px solid {_P.divider};   /* adds inner padding to each cell and draws a thin divider line below each row */
}}
QTableView::item:hover {{
    background-color: {lerp_color(_P.accent_glow, _P.bg_card, 0.70)};  /* very faintly tints a row with indigo glow when the mouse hovers over it */
}}
QTableView::item:selected {{
    background-color: rgba(67,97,238,0.12); color: {_P.accent};  /* highlights the selected row with a transparent indigo tint and changes text to accent colour */
}}
QHeaderView::section {{
    background-color: {_P.bg_surface}; color: {_P.text_secondary}; border: none;  /* gives column headers a surface-colour background with secondary grey text */
    border-bottom: 2px solid {_P.divider}; padding: 12px 14px;                     /* draws a 2px underline below headers and adds generous padding for readability */
    font-weight: bold; font-size: 11px; text-transform: uppercase;                  /* makes header labels bold, slightly smaller, and forces UPPERCASE text */
}}
QHeaderView::section:hover {{ background-color: {_P.divider}; color: {_P.text_primary}; }}  /* when hovering a header, tints it with the divider colour and darkens the text */

/* ── QRadioButton ── */
QRadioButton {{
    color: {_P.text_secondary}; font-size: 11px; spacing: 8px;  /* sets radio button label text to secondary grey at 11pt with 8px gap from the circle */
}}
QRadioButton::indicator {{
    width: 16px; height: 16px; border-radius: 8px;               /* draws the radio circle as a 16×16px circle (border-radius = half width) */
    border: 2px solid {_P.border}; background: {_P.bg_card};     /* gives the circle a grey border and white interior in the unchecked state */
}}
QRadioButton::indicator:checked {{ background: {_P.accent}; border-color: {_P.accent}; }}  /* fills the radio circle with accent indigo and changes its border to accent when checked */
QRadioButton::indicator:hover {{ border-color: {_P.accent}; }}   /* switches the radio circle border to accent on hover to signal interactivity */

/* ── QCheckBox ── */
QCheckBox {{
    color: {_P.text_primary}; font-size: 12px; spacing: 10px;   /* sets checkbox label text to the primary colour at 12pt with 10px gap from the box */
}}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 5px;               /* draws the checkbox as a slightly rounded 18×18px square */
    border: 2px solid {_P.border}; background: {_P.bg_card};     /* gives it a grey border and white fill when unchecked */
}}
QCheckBox::indicator:checked {{ background: {_P.accent}; border-color: {_P.accent}; }}  /* fills the checkbox with accent indigo when ticked */

/* ── QProgressBar ── */
QProgressBar {{
    background-color: {_P.border}; border: none; border-radius: 7px;  /* draws the progress bar track as a rounded grey bar with no border */
    max-height: 14px; text-align: center; font-size: 0px;              /* caps the height at 14px and hides the percentage text (we use custom labels instead) */
}}
QProgressBar::chunk {{ background-color: {_P.accent}; border-radius: 7px; }}  /* fills the completed portion of the bar with accent indigo, rounded to match the track */

/* ── QDialog ── */
QDialog {{ background-color: {_P.bg_card}; border-radius: 12px; }}  /* gives all popup dialogs a white card background with rounded corners */

/* ── QMessageBox ── */
QMessageBox {{ background-color: {_P.bg_card}; }}                              /* gives message boxes (alerts/confirms) a white background */
QMessageBox QLabel {{ color: {_P.text_primary}; font-size: 12px; }}            /* styles message box body text in the primary colour at 12pt */
QMessageBox QPushButton {{
    background-color: {_P.accent}; color: #FFFFFF; border: none;               /* styles message box buttons as solid indigo with white text */
    border-radius: 10px; padding: 10px 28px; font-weight: bold; min-width: 90px;  /* rounds their corners, adds padding, makes text bold, and ensures a minimum width */
}}
QMessageBox QPushButton:hover {{ background-color: {_P.accent_dim}; }}         /* darkens message box button on hover */

/* ── QInputDialog ── */
QInputDialog {{ background-color: {_P.bg_card}; }}                             /* gives input dialogs (e.g. Add City) a white card background */
QInputDialog QLabel {{ color: {_P.text_primary}; font-size: 12px; }}           /* styles the prompt label text in the primary near-black colour */
QInputDialog QLineEdit {{
    background-color: {_P.bg_input}; border: 1.5px solid {_P.border};         /* gives the text input inside an input dialog the same pale background as regular inputs */
    border-radius: 8px; padding: 8px 12px;
    font-size: 12px; color: {_P.text_primary};
}}
QInputDialog QPushButton {{
    background-color: {_P.accent}; color: #FFFFFF; border: none;               /* styles OK/Cancel buttons in input dialogs as solid indigo with white text */
    border-radius: 10px; padding: 10px 28px; font-weight: bold; min-width: 90px;
}}
QInputDialog QPushButton:hover {{ background-color: {_P.accent_dim}; }}        /* darkens on hover to match the message box button hover behaviour */

/* ── Generic QPushButton fallback (dialogs without cssClass) ── */
QPushButton:!property(cssClass) {{ color: {_P.text_primary}; }}

/* ── Card Frame ── */
QFrame[cssClass="card"] {{
    background-color: {_P.bg_card}; border: 1px solid {_P.border};  /* gives card frames a white background and a thin grey border */
    border-radius: {_D.card_radius}px;                                /* rounds card corners by 16px for a modern SaaS look */
}}

/* ── QToolTip ── */
QToolTip {{
    background-color: {_P.bg_sidebar}; color: #FFFFFF;               /* gives tooltip popups a dark navy background with white text */
    border: 1px solid {_P.accent}; border-radius: 8px;               /* adds a thin indigo border and rounded corners to tooltips */
    padding: 8px 14px; font-size: 11px;                              /* adds padding inside tooltip text and uses a slightly smaller font */
}}

/* ── Glass Panel ── */
QFrame[cssClass="glass"] {{
    background-color: rgba({int(_P.bg_card[1:3], 16)}, {int(_P.bg_card[3:5], 16)}, {int(_P.bg_card[5:7], 16)}, 220);  /* translucent white background extracted from bg_card hex; allows content behind it to show through */
    border: 1px solid {lerp_color(_P.border, _P.accent, 0.15)};      /* slightly accent-tinted border to give the glass panel a subtle indigo glow */
    border-radius: {_D.card_radius}px;                                /* rounds glass panel corners by 16px to match regular cards */
}}
"""

GLOBAL_QSS = get_global_qss()  # pre-builds the stylesheet at import time for any legacy code that reads GLOBAL_QSS directly