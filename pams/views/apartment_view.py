# ============================================================
# PAMS — views/apartment_view.py
# Apartment Management CRUD View (PySide6)
# ============================================================
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QRadioButton, QButtonGroup,
    QDialog, QMessageBox, QScrollArea, QFrame, QInputDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..theme import PALETTE as P, FONTS as F, DIMS as D
from ..widgets import (
    qfont, Card, section_header, make_table, table_clear,
    table_insert, table_selected_id, badge_text, styled_button, Toast,
    STATUS_COLORS,
)
from .. import database2 as db


def _get_locations():
    locs = db.get_all_locations()
    return locs if locs else ["Bristol", "London", "Manchester", "Cardiff"]


TYPES    = ["Studio", "1-Bedroom", "2-Bedroom", "3-Bedroom", "Penthouse"]
STATUSES = ["Vacant", "Occupied", "Maintenance", "Reserved"]


class ApartmentView(QWidget):
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self._user = user
        self._loc = user.get("location")
        self._selected_id = None
        self._build()
        self._reload()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        section_header(lay, "Apartment Management",
                       "Register, assign, and manage property units")

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(D.pad_lg, D.pad_sm, D.pad_lg, D.pad_sm)

        search_icon = QLabel("🔍")
        search_icon.setStyleSheet(f"color: {P.text_muted};")
        toolbar.addWidget(search_icon)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search apartments...")
        self._search.setFixedHeight(38)
        self._search.setFixedWidth(230)
        self._search.textChanged.connect(self._reload)
        toolbar.addWidget(self._search)

        # Status filter
        self._status_filter = "All"
        self._filter_group = QButtonGroup(self)
        for s in ["All", "Vacant", "Occupied"]:
            rb = QRadioButton(s)
            rb.setStyleSheet(f"color: {P.text_secondary};")
            if s == "All":
                rb.setChecked(True)
            rb.toggled.connect(lambda checked, st=s: self._set_filter(st, checked))
            self._filter_group.addButton(rb)
            toolbar.addWidget(rb)

        role = self._user["role"]
        if role in ("Administrator", "Manager"):
            btn_add = styled_button("+ Add Apartment", "primary")
            btn_add.clicked.connect(self._open_add)
            toolbar.addWidget(btn_add)
            btn_edit = styled_button("Edit", "outline")
            btn_edit.clicked.connect(self._open_edit)
            toolbar.addWidget(btn_edit)
            btn_del = styled_button("Delete", "danger")
            btn_del.clicked.connect(self._delete)
            toolbar.addWidget(btn_del)

        if role == "Manager":
            btn_city = styled_button("+ Add City", "outline")
            btn_city.clicked.connect(self._add_city)
            toolbar.addWidget(btn_city)

        toolbar.addStretch()
        self._count_lbl = QLabel("")
        self._count_lbl.setFont(qfont(F.small))
        self._count_lbl.setStyleSheet(f"color: {P.text_muted};")
        toolbar.addWidget(self._count_lbl)
        lay.addLayout(toolbar)

        # ── Table ──
        card = Card(title="", accent_color=P.accent2)
        cols = [
            ("#", 40), ("Apt #", 80), ("City", 90), ("Type", 100),
            ("Rooms", 55), ("Monthly £", 100), ("Floor", 50),
            ("Status", 90), ("Description", 200),
        ]
        self._table, self._model = make_table(card.body_layout(), cols)
        self._table.clicked.connect(self._on_select)
        lay.addWidget(card, 1)

    def _set_filter(self, status, checked):
        if checked:
            self._status_filter = status
            self._reload()

    def _reload(self):
        table_clear(self._model)
        apts = db.get_all_apartments(self._loc)
        q = self._search.text().lower()
        sf = self._status_filter
        cnt = 0
        for a in apts:
            if q and q not in (a["apt_number"] + a["location"] + a["type"]).lower():
                continue
            if sf != "All" and a["status"] != sf:
                continue
            color = STATUS_COLORS.get(a["status"], P.text_muted)
            table_insert(self._model, [
                str(a["id"]), a["apt_number"], a["location"],
                a["type"], str(a["rooms"]),
                f"£{a['monthly_rent']:,.0f}",
                str(a["floor"]),
                badge_text(a["status"]),
                a.get("description") or "—",
            ], color)
            cnt += 1
        self._count_lbl.setText(f"{cnt} unit(s)")
        self._selected_id = None

    def _on_select(self, index):
        tid = table_selected_id(self._table, self._model, 0)
        if tid is not None:
            try:
                self._selected_id = int(tid)
            except ValueError:
                self._selected_id = None

    def _open_add(self):
        dlg = _AptDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._reload()

    def _open_edit(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select an apartment first.")
            return
        apts = db.get_all_apartments()
        apt = next((a for a in apts if a["id"] == self._selected_id), None)
        if apt:
            dlg = _AptDialog(self, apt=apt)
            if dlg.exec() == QDialog.Accepted:
                self._reload()

    def _delete(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select an apartment first.")
            return
        ans = QMessageBox.question(self, "Delete",
                                   "Permanently delete this apartment?")
        if ans == QMessageBox.Yes:
            db.delete_apartment(self._selected_id)
            self._reload()
            Toast(self.window(), "Apartment deleted.", kind="info")

    def _add_city(self):
        city, ok = QInputDialog.getText(
            self, "Expand Business",
            "Enter the name of the new city to expand operations to:")
        if ok and city.strip():
            city = city.strip().title()
            existing = db.get_all_locations()
            if city in existing:
                QMessageBox.information(self, "Info", f"{city} already exists.")
            else:
                db.expandBusiness(city)
                Toast(self.window(),
                      f"New city '{city}' added. You can now register apartments there.")
                self._reload()


# ──────────────────────────────────────────────────────────
# APT ADD/EDIT DIALOG
# ──────────────────────────────────────────────────────────
class _AptDialog(QDialog):
    def __init__(self, parent, apt=None):
        super().__init__(parent)
        self._apt = apt
        self.setWindowTitle("Edit Apartment" if apt else "Add Apartment")
        self.setMinimumSize(500, 500)
        self.resize(500, 600)
        self._build()
        if apt:
            self._populate(apt)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)

        title = QLabel("Apartment Details")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"color: {P.text_primary};")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        form = QWidget()
        fl = QVBoxLayout(form)
        fl.setSpacing(4)

        # Apt Number
        fl.addWidget(self._lbl("Apt Number"))
        self._apt_num = QLineEdit()
        self._apt_num.setPlaceholderText("APT-101")
        self._apt_num.setFixedHeight(38)
        fl.addWidget(self._apt_num)

        # Location
        fl.addWidget(self._lbl("City / Location"))
        self._loc_combo = QComboBox()
        self._loc_combo.addItems(_get_locations())
        fl.addWidget(self._loc_combo)

        # Type
        fl.addWidget(self._lbl("Type"))
        self._type_combo = QComboBox()
        self._type_combo.addItems(TYPES)
        fl.addWidget(self._type_combo)

        # Rooms, Rent, Floor
        self._entries = {}
        for label, key, ph in [
            ("Number of Rooms", "rooms", "2"),
            ("Monthly Rent (£)", "rent", "1200"),
            ("Floor", "floor", "1"),
        ]:
            fl.addWidget(self._lbl(label))
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setFixedHeight(38)
            fl.addWidget(e)
            self._entries[key] = e

        # Status (edit only)
        if self._apt:
            fl.addWidget(self._lbl("Status"))
            self._status_combo = QComboBox()
            self._status_combo.addItems(STATUSES)
            fl.addWidget(self._status_combo)

        # Description
        fl.addWidget(self._lbl("Description"))
        self._desc = QLineEdit()
        self._desc.setPlaceholderText("Optional description")
        self._desc.setFixedHeight(38)
        fl.addWidget(self._desc)

        scroll.setWidget(form)
        lay.addWidget(scroll, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_save = styled_button("Save", "primary")
        btn_save.setFixedHeight(42)
        btn_save.setFixedWidth(180)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)
        btn_cancel = styled_button("Cancel", "outline")
        btn_cancel.setFixedHeight(42)
        btn_cancel.setFixedWidth(120)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def _lbl(self, text):
        l = QLabel(text)
        l.setFont(qfont(F.label))
        l.setStyleSheet(f"color: {P.text_secondary};")
        return l

    def _populate(self, a):
        self._apt_num.setText(a.get("apt_number", ""))
        idx = self._loc_combo.findText(a.get("location", ""))
        if idx >= 0:
            self._loc_combo.setCurrentIndex(idx)
        idx = self._type_combo.findText(a.get("type", ""))
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        self._entries["rooms"].setText(str(a.get("rooms", "")))
        self._entries["rent"].setText(str(a.get("monthly_rent", "")))
        self._entries["floor"].setText(str(a.get("floor", "")))
        self._desc.setText(a.get("description", ""))
        if hasattr(self, "_status_combo"):
            idx = self._status_combo.findText(a.get("status", "Vacant"))
            if idx >= 0:
                self._status_combo.setCurrentIndex(idx)

    def _save(self):
        num = self._apt_num.text().strip()
        loc = self._loc_combo.currentText().strip()
        atype = self._type_combo.currentText().strip()
        desc = self._desc.text().strip()

        if not num or not loc or not atype:
            QMessageBox.critical(self, "Validation",
                                 "Number, City and Type are required.")
            return
        try:
            rooms = int(self._entries["rooms"].text() or 1)
            rent = float(self._entries["rent"].text() or 0)
            floor = int(self._entries["floor"].text() or 1)
        except ValueError:
            QMessageBox.critical(self, "Validation",
                                 "Rooms, Rent and Floor must be numbers.")
            return

        if self._apt:
            st = (self._status_combo.currentText()
                  if hasattr(self, "_status_combo") else self._apt["status"])
            db.update_apartment(self._apt["id"], num, loc, atype,
                                rooms, rent, st, floor, desc)
            msg = "Apartment updated."
        else:
            db.add_apartment(num, loc, atype, rooms, rent, floor, desc)
            msg = "Apartment added."

        Toast(self.window(), msg)
        self.accept()
