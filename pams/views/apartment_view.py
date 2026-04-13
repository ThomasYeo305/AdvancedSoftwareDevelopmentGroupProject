# ============================================================
# PAMS — views/apartment_view.py
# Apartment Management CRUD View (PySide6)
#
# Contributors (UI):
#   Chouaib Hakim       — Student ID: 24018717
#   Sinoli Rodrigo      — Student ID: 24055025
# ============================================================
from __future__ import annotations   # allows forward type hints without circular imports

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QRadioButton, QButtonGroup,
    QDialog, QMessageBox, QScrollArea, QFrame, QInputDialog,   # QInputDialog used for the 'Add City' text prompt
)
from PySide6.QtCore import Qt   # Qt alignment and cursor constants
from PySide6.QtGui import QFont   # used for dialog headings

from ..theme import PALETTE as P, FONTS as F, DIMS as D   # P=colours, F=font sizes, D=spacing tokens
from ..widgets import (
    qfont, Card, section_header, make_table, table_clear,
    table_insert, table_selected_id, badge_text, styled_button, Toast,
    STATUS_COLORS,   # STATUS_COLORS maps Vacant/Occupied/Maintenance to colour strings
)
from .. import database as db   # all SQL queries for apartments and locations


def _get_locations():
    locs = db.get_all_locations()   # fetches all city names that currently have apartments in the DB
    return locs if locs else ["Bristol", "London", "Manchester", "Cardiff"]   # fallback list if the DB is empty


TYPES    = ["Studio", "1-Bedroom", "2-Bedroom", "3-Bedroom", "Penthouse"]   # all valid apartment type options
STATUSES = ["Vacant", "Occupied", "Maintenance", "Reserved"]   # all valid apartment status options


class ApartmentView(QWidget):
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self._user = user   # full user dict containing role and location for permission checks
        self._loc = user.get("location")   # branch filter applied to apartment DB queries
        self._selected_id = None   # tracks which apartment row is currently selected
        self._build()   # constructs toolbar, filter row, and table card
        self._reload()   # loads all apartment rows from the database

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)   # no outer margin so layout fills the scroll area
        lay.setSpacing(8)

        section_header(lay, "Apartment Management",
                       "Register, assign, and manage property units")   # page title bar

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(D.pad_lg, D.pad_sm, D.pad_lg, D.pad_sm)

        search_icon = QLabel("🔍")
        search_icon.setStyleSheet(f"color: {P.text_muted};")
        toolbar.addWidget(search_icon)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search apartments...")
        self._search.setFixedHeight(38)
        self._search.setFixedWidth(230)   # fixed 230px so it doesn't crowd the filter radio buttons
        self._search.textChanged.connect(self._reload)   # filters the table live as the user types
        toolbar.addWidget(self._search)

        # Status filter
        self._status_filter = "All"   # default shows all apartments regardless of status
        self._filter_group = QButtonGroup(self)   # groups the radio buttons so only one can be selected at a time
        for s in ["All", "Vacant", "Occupied"]:
            rb = QRadioButton(s)
            rb.setStyleSheet(f"color: {P.text_secondary};")
            if s == "All":
                rb.setChecked(True)   # 'All' is selected by default when the view first opens
            rb.toggled.connect(lambda checked, st=s: self._set_filter(st, checked))   # updates filter on toggle
            self._filter_group.addButton(rb)
            toolbar.addWidget(rb)

        role = self._user["role"]
        if role in ("Administrator", "Manager"):   # add/edit/delete only visible to Admin and Manager
            btn_add = styled_button("+ Add Apartment", "primary")   # primary button to open the add dialog
            btn_add.clicked.connect(self._open_add)
            toolbar.addWidget(btn_add)
            btn_edit = styled_button("Edit", "outline")   # outline button to edit the selected apartment
            btn_edit.clicked.connect(self._open_edit)
            toolbar.addWidget(btn_edit)
            btn_del = styled_button("Delete", "danger")   # red button to permanently delete the selected apartment
            btn_del.clicked.connect(self._delete)
            toolbar.addWidget(btn_del)

        if role == "Manager":   # only the Manager can expand to new cities
            btn_city = styled_button("+ Add City", "outline")   # outline button opens the 'Add City' text input dialog
            btn_city.clicked.connect(self._add_city)
            toolbar.addWidget(btn_city)

        toolbar.addStretch()   # pushes the count label to the far right
        self._count_lbl = QLabel("")
        self._count_lbl.setFont(qfont(F.small))
        self._count_lbl.setStyleSheet(f"color: {P.text_muted};")
        toolbar.addWidget(self._count_lbl)
        lay.addLayout(toolbar)

        # ── Table ──
        card = Card(title="", accent_color=P.accent2)   # violet accent card with no title text
        cols = [
            ("#", 40), ("Apt #", 80), ("City", 90), ("Type", 100),
            ("Rooms", 55), ("Monthly £", 100), ("Floor", 50),
            ("Status", 90), ("Description", 200),   # 9 columns covering all key apartment fields
        ]
        self._table, self._model = make_table(card.body_layout(), cols)   # styled read-only table
        self._table.clicked.connect(self._on_select)   # records which row was clicked
        lay.addWidget(card, 1)   # card stretches to fill remaining vertical space

    def _set_filter(self, status, checked):
        if checked:
            self._status_filter = status   # stores the newly selected status filter
            self._reload()   # re-queries and repaints the table with the new filter

    def _reload(self):
        table_clear(self._model)   # removes all existing rows from the table model
        apts = db.get_all_apartments(self._loc)   # fetches all apartments for the branch from the DB
        q = self._search.text().lower()   # search query lowercased for case-insensitive matching
        sf = self._status_filter   # current status filter ('All', 'Vacant', or 'Occupied')
        cnt = 0   # counts visible rows for the record label
        for a in apts:
            if q and q not in (a["apt_number"] + a["location"] + a["type"]).lower():
                continue   # skips apartments not matching the search text
            if sf != "All" and a["status"] != sf:
                continue   # skips apartments not matching the status filter
            cnt += 1
            color = STATUS_COLORS.get(a["status"], P.text_muted)   # row text colour based on apartment status
            table_insert(self._model, [
                str(cnt), a["apt_number"], a["location"],
                a["type"], str(a["rooms"]),
                f"£{a['monthly_rent']:,.0f}",   # £1,200 format with comma thousands separator
                str(a["floor"]),
                badge_text(a["status"]),   # badge symbol for Vacant/Occupied/Maintenance
                a.get("description") or "—",   # dash if no description recorded
            ], color, row_id=a["id"])   # stores DB id for selection
        self._count_lbl.setText(f"{cnt} unit(s)")   # updates the record count at the right of the toolbar
        self._selected_id = None   # clears any previous selection

    def _on_select(self, index):
        tid = table_selected_id(self._table, self._model, 0)   # reads the apartment ID from column 0
        if tid is not None:
            try:
                self._selected_id = int(tid)   # stores the selected apartment ID as an integer
            except ValueError:
                self._selected_id = None

    def _open_add(self):
        dlg = _AptDialog(self)   # opens an empty add dialog
        if dlg.exec() == QDialog.Accepted:
            self._reload()   # refreshes the table only if Save was clicked

    def _open_edit(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select an apartment first.")
            return   # prevents opening edit dialog with no row selected
        apts = db.get_all_apartments()   # fetches all apartments (no location filter) to find the selected one
        apt = next((a for a in apts if a["id"] == self._selected_id), None)   # finds the dict matching the selected ID
        if apt:
            dlg = _AptDialog(self, apt=apt)   # opens the dialog pre-filled with existing data
            if dlg.exec() == QDialog.Accepted:
                self._reload()

    def _delete(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select an apartment first.")
            return
        ans = QMessageBox.question(self, "Delete",
                                   "Permanently delete this apartment?")   # asks for confirmation before deleting
        if ans == QMessageBox.Yes:
            db.delete_apartment(self._selected_id)   # removes the apartment record from the database
            self._reload()
            Toast(self.window(), "Apartment deleted.", kind="info")   # brief info toast confirming deletion

    def _add_city(self):
        city, ok = QInputDialog.getText(
            self, "Expand Business",
            "Enter the name of the new city to expand operations to:")   # single-line text prompt for the new city name
        if ok and city.strip():
            city = city.strip().title()   # capitalises each word (e.g. 'north london' → 'North London')
            existing = db.get_all_locations()
            if city in existing:
                QMessageBox.information(self, "Info", f"{city} already exists.")   # prevents duplicate cities
            else:
                db.expandBusiness(city)   # inserts the new city record into the DB
                Toast(self.window(),
                      f"New city '{city}' added. You can now register apartments there.")
                self._reload()


# ──────────────────────────────────────────────────────────
# APT ADD/EDIT DIALOG
# ──────────────────────────────────────────────────────────
class _AptDialog(QDialog):
    def __init__(self, parent, apt=None):
        super().__init__(parent)
        self._apt = apt   # None in add mode; dict of existing apartment data in edit mode
        self.setWindowTitle("Edit Apartment" if apt else "Add Apartment")   # title bar reflects the current mode
        self.setMinimumSize(500, 500)
        self.resize(500, 600)   # default opening size for the apartment form
        self._build()   # constructs all input fields and buttons
        if apt:
            self._populate(apt)   # fills in existing values when editing

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)

        title = QLabel("Apartment Details")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))   # large heading inside the dialog
        title.setStyleSheet(f"color: {P.text_primary};")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)   # allows the form to expand to fill the scroll area
        scroll.setFrameShape(QFrame.NoFrame)   # removes the scroll area border
        form = QWidget()
        fl = QVBoxLayout(form)
        fl.setSpacing(4)

        # Apt Number
        fl.addWidget(self._lbl("Apt Number"))
        self._apt_num = QLineEdit()
        self._apt_num.setPlaceholderText("APT-101")   # example apartment number format
        self._apt_num.setFixedHeight(38)
        fl.addWidget(self._apt_num)

        # Location
        fl.addWidget(self._lbl("City / Location"))
        self._loc_combo = QComboBox()
        self._loc_combo.addItems(_get_locations())   # populates with all known cities from the DB
        fl.addWidget(self._loc_combo)

        # Type
        fl.addWidget(self._lbl("Type"))
        self._type_combo = QComboBox()
        self._type_combo.addItems(TYPES)   # Studio / 1-Bedroom / 2-Bedroom / 3-Bedroom / Penthouse
        fl.addWidget(self._type_combo)

        # Rooms, Rent, Floor
        self._entries = {}   # stores the three numeric input widgets
        for label, key, ph in [
            ("Number of Rooms", "rooms", "2"),   # default hint is 2 rooms
            ("Monthly Rent (£)", "rent", "1200"),   # default hint is £1,200
            ("Floor", "floor", "1"),   # default hint is floor 1
        ]:
            fl.addWidget(self._lbl(label))
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setFixedHeight(38)
            fl.addWidget(e)
            self._entries[key] = e   # saves widget keyed by 'rooms', 'rent', or 'floor'

        # Status (edit only)
        if self._apt:   # status picker only shown in edit mode (new apartments start as Vacant automatically)
            fl.addWidget(self._lbl("Status"))
            self._status_combo = QComboBox()
            self._status_combo.addItems(STATUSES)   # Vacant / Occupied / Maintenance / Reserved
            fl.addWidget(self._status_combo)

        # Description
        fl.addWidget(self._lbl("Description"))
        self._desc = QLineEdit()
        self._desc.setPlaceholderText("Optional description")
        self._desc.setFixedHeight(38)
        fl.addWidget(self._desc)

        scroll.setWidget(form)   # places the form inside the scrollable viewport
        lay.addWidget(scroll, 1)   # scroll area fills remaining dialog space

        # Buttons
        btn_row = QHBoxLayout()
        btn_save = styled_button("Save", "primary")
        btn_save.setFixedHeight(42)
        btn_save.setFixedWidth(180)
        btn_save.clicked.connect(self._save)   # wires Save to validation and DB write
        btn_row.addWidget(btn_save)
        btn_cancel = styled_button("Cancel", "outline")
        btn_cancel.setFixedHeight(42)
        btn_cancel.setFixedWidth(120)
        btn_cancel.clicked.connect(self.reject)   # closes dialog without saving
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def _lbl(self, text):
        l = QLabel(text)
        l.setFont(qfont(F.label))
        l.setStyleSheet(f"color: {P.text_secondary};")   # secondary grey for all form field labels
        return l   # returns the configured label widget for insertion into the form layout

    def _populate(self, a):
        self._apt_num.setText(a.get("apt_number", ""))   # fills the apartment number field
        idx = self._loc_combo.findText(a.get("location", ""))
        if idx >= 0:
            self._loc_combo.setCurrentIndex(idx)   # selects the existing city in the dropdown
        idx = self._type_combo.findText(a.get("type", ""))
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)   # selects the existing type (e.g. 2-Bedroom)
        self._entries["rooms"].setText(str(a.get("rooms", "")))
        self._entries["rent"].setText(str(a.get("monthly_rent", "")))
        self._entries["floor"].setText(str(a.get("floor", "")))
        self._desc.setText(a.get("description", ""))
        if hasattr(self, "_status_combo"):
            idx = self._status_combo.findText(a.get("status", "Vacant"))
            if idx >= 0:
                self._status_combo.setCurrentIndex(idx)   # selects the current status in the combo box

    def _save(self):
        num = self._apt_num.text().strip()   # reads the apartment unit number
        loc = self._loc_combo.currentText().strip()   # reads the selected city
        atype = self._type_combo.currentText().strip()   # reads the selected type
        desc = self._desc.text().strip()   # reads the optional description

        if not num or not loc or not atype:
            QMessageBox.critical(self, "Validation",
                                 "Number, City and Type are required.")
            return   # stops save if any required field is empty
        try:
            rooms = int(self._entries["rooms"].text() or 1)   # defaults to 1 room if empty
            rent = float(self._entries["rent"].text() or 0)   # defaults to £0 if empty
            floor = int(self._entries["floor"].text() or 1)   # defaults to floor 1 if empty
        except ValueError:
            QMessageBox.critical(self, "Validation",
                                 "Rooms, Rent and Floor must be numbers.")
            return

        if self._apt:
            st = (self._status_combo.currentText()
                  if hasattr(self, "_status_combo") else self._apt["status"])   # keeps existing status if combo not present
            db.update_apartment(self._apt["id"], num, loc, atype,
                                rooms, rent, st, floor, desc)   # updates all fields for the existing apartment
            msg = "Apartment updated."
        else:
            db.add_apartment(num, loc, atype, rooms, rent, floor, desc)   # inserts a new apartment record as Vacant
            msg = "Apartment added."

        Toast(self.window(), msg)   # brief success toast confirming the save
        self.accept()   # closes the dialog and triggers a table reload
