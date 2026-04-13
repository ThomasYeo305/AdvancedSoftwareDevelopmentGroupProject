# ============================================================
# PAMS — views/complaint_view.py
# Complaints Management CRUD View (PySide6)
#
# Contributors (UI):
#   Chouaib Hakim       — Student ID: 24018717
#   Sinoli Rodrigo      — Student ID: 24055025
# ============================================================
from __future__ import annotations   # enables forward-reference type hints without quote wrapping

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QRadioButton, QButtonGroup,
    QDialog, QMessageBox, QFrame,
)   # all Qt widget and layout classes needed to build the complaints screen and its dialogs
from PySide6.QtCore import Qt   # Qt alignment and window flag constants
from PySide6.QtGui import QFont   # QFont used to apply bold fonts to dialog headings

from ..theme import PALETTE as P, FONTS as F, DIMS as D   # P = brand colours, F = font sizes, D = spacing/padding constants
from ..widgets import (
    qfont, Card, section_header, make_table, table_clear,
    table_insert, table_selected_id, badge_text, styled_button, Toast,
    STATUS_COLORS, fmt_date,
)   # shared UI helpers: font builder, card panel, table factory, toast notification, status colour map
from .. import database as db   # all database operations for complaints (get, add, updateStatus)


class ComplaintView(QWidget):   # main complaints panel shown inside the main app's tab area
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)   # registers this widget with Qt's parent-child ownership system
        self._user = user   # stores the logged-in user dict (role, location, etc.)
        self._loc = user.get("location")   # stores the user's branch city for filtering complaints
        self._selected_id = None   # tracks which complaint row is currently highlighted (None = none selected)
        self._build()   # constructs all child widgets and layouts
        self._reload()   # fetches complaint data from the DB and populates the table

    def _build(self):
        lay = QVBoxLayout(self)   # stacks the header, toolbar, and body vertically
        lay.setContentsMargins(0, 0, 0, 0)   # removes outer padding so the view fills its container edge-to-edge
        lay.setSpacing(8)   # 8 px gap between the header, toolbar, and body

        section_header(lay, "Complaints Management",
                       "Register, track and resolve tenant complaints")   # adds the amber page title and subtitle strip

        # ── Toolbar ──
        toolbar = QHBoxLayout()   # lays out the filter radio buttons and action buttons side by side
        toolbar.setContentsMargins(D.pad_lg, D.pad_sm, D.pad_lg, D.pad_sm)   # applies horizontal and vertical padding to the toolbar

        self._filter_val = "All"   # default filter shows all complaints regardless of status
        self._filter_group = QButtonGroup(self)   # groups the radio buttons so only one can be checked at a time
        for s in ["All", "Open", "In Progress", "Resolved"]:
            rb = QRadioButton(s)   # creates one radio button per status option
            rb.setStyleSheet(f"color: {P.text_secondary};")   # colours the radio button label in secondary text colour
            if s == "All":
                rb.setChecked(True)   # pre-selects "All" so all complaints are shown on first load
            rb.toggled.connect(
                lambda checked, st=s: self._set_filter(st, checked))   # calls _set_filter when this radio button is toggled on
            self._filter_group.addButton(rb)   # adds this radio button to the exclusive group
            toolbar.addWidget(rb)   # adds the radio button to the toolbar

        btn_add = styled_button("+ Log Complaint", "warning")   # amber button for logging a new tenant complaint
        btn_add.clicked.connect(self._open_add)   # opens the Log Complaint dialog when clicked
        toolbar.addWidget(btn_add)   # adds the log button to the toolbar

        if self._user["role"] in ("Administrator", "Front-Desk Staff"):
            btn_status = styled_button("Update Status", "primary")   # blue button for changing a complaint's status (admin/front-desk only)
            btn_status.clicked.connect(self._update_status)   # opens the status change dialog when clicked
            toolbar.addWidget(btn_status)   # adds the update status button to the toolbar

            btn_resolve = styled_button("Resolve", "success")   # green button for marking a complaint as fully resolved
            btn_resolve.clicked.connect(self._resolve)   # triggers the quick-resolve confirmation when clicked
            toolbar.addWidget(btn_resolve)   # adds the resolve button to the toolbar

        toolbar.addStretch()   # pushes all buttons to the left and count label to the right
        self._count_lbl = QLabel("")   # small muted label showing how many complaints match the filter
        self._count_lbl.setFont(qfont(F.small))   # applies the small font size to the count label
        self._count_lbl.setStyleSheet(f"color: {P.text_muted};")   # colours the count label in the muted text colour
        toolbar.addWidget(self._count_lbl)   # adds the count label to the far right of the toolbar
        lay.addLayout(toolbar)   # adds the toolbar row to the main vertical layout

        # ── Body: table + detail ──
        body = QHBoxLayout()   # places the complaints table and detail panel side by side
        body.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)   # adds horizontal and bottom padding to the body area
        body.setSpacing(D.pad_sm)   # small gap between the table card and the detail card

        # Table
        card = Card(title="", accent_color=P.warning)   # amber-accented card container holding the complaints table
        cols = [
            ("#", 40), ("Subject", 180), ("Tenant", 140), ("Apartment", 90),
            ("City", 80), ("Status", 90), ("Reported", 100), ("Resolved", 100),
        ]   # column name and pixel-width pairs for the 8-column complaints table
        self._table, self._model = make_table(card.body_layout(), cols)   # creates the table widget and its data model inside the card
        self._table.clicked.connect(self._on_select)   # fires _on_select whenever the user clicks a row
        body.addWidget(card, 3)   # table card takes 3 parts of the horizontal space

        # Detail panel
        self._detail_card = Card(title="Complaint Detail", accent_color=P.warning)   # amber-accented card showing info for the selected complaint
        self._detail_layout = self._detail_card.body_layout()   # gets the inner layout to dynamically insert detail rows
        body.addWidget(self._detail_card, 1)   # detail card takes 1 part of the horizontal space

        lay.addLayout(body, 1)   # adds the body row to the main layout, giving it all remaining vertical space

    def _set_filter(self, status, checked):
        if checked:
            self._filter_val = status   # updates the active filter to the newly selected status string
            self._reload()   # reloads the table so only complaints matching the new filter are shown

    def _reload(self):
        table_clear(self._model)   # clears all existing rows from the complaints table
        items = db.get_all_complaints(self._loc)   # fetches all complaints filtered to the user's branch city
        filt = self._filter_val   # stores the current filter value for use in the loop
        cnt = 0   # counter tracking how many complaints pass the active filter
        for c in items:
            if filt != "All" and c["status"] != filt:
                continue   # skips this complaint if it doesn't match the active status filter
            color = STATUS_COLORS.get(c["status"], P.text_muted)   # looks up the row text colour for this complaint's status
            table_insert(self._model, [
                str(c["id"]),
                c["title"],
                c.get("full_name") or "—",   # shows tenant name or a dash if not linked
                c.get("apt_number") or "—",   # shows apartment number or a dash if not linked
                c.get("location") or "—",   # shows city or a dash if not recorded
                badge_text(c["status"]),   # wraps the status value in a badge-style label
                fmt_date(c.get("created_at")),   # report date in UK DD/MM/YYYY format
                fmt_date(c.get("resolved_at")),   # resolution date or dash if not resolved
            ], color)   # inserts this row into the table model with its status colour
            cnt += 1   # increments the visible row counter
        self._count_lbl.setText(f"{cnt} complaint(s)")   # updates the count label with how many complaints are visible
        self._selected_id = None   # clears the selection after a reload

    def _on_select(self, index):
        tid = table_selected_id(self._table, self._model, 0)   # reads the complaint ID from column 0 of the clicked row
        if tid is None:
            return   # exits early if no row ID could be read
        try:
            self._selected_id = int(tid)   # converts the ID string to an integer and stores it for action methods
        except ValueError:
            return   # exits if the ID couldn't be parsed (should not happen with valid table data)

        # Populate detail
        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)   # removes the first layout item repeatedly until the panel is empty
            w = item.widget()
            if w:
                w.deleteLater()   # schedules the old widget for deletion to free memory

        items = db.get_all_complaints()   # fetches all complaints (unfiltered) to find the selected one
        c = next((x for x in items if x["id"] == self._selected_id), None)   # finds the dict for this specific complaint ID
        if not c:
            return   # exits if the complaint no longer exists in the database

        details = [
            ("Subject",   c["title"],                    P.text_primary),
            ("Tenant",    c.get("full_name") or "—",     P.text_secondary),
            ("Apartment", c.get("apt_number") or "—",    P.text_secondary),
            ("City",      c.get("location") or "—",      P.text_secondary),
            ("Status",    badge_text(c["status"]),        P.text_primary),
            ("Reported",  fmt_date(c.get("created_at")), P.text_secondary),
            ("Resolved",  fmt_date(c.get("resolved_at")),   P.text_secondary),
        ]   # list of (label, value, colour) tuples that define every detail row shown in the right panel
        for label, value, color in details:
            row = QHBoxLayout()   # each detail item is a horizontal pair: label on left, value on right
            lbl = QLabel(f"{label}:")   # creates the field name label (e.g. "Subject:")
            lbl.setFixedWidth(80)   # fixes the label column to 80 px so values all align vertically
            lbl.setFont(qfont(F.small_bold))   # applies the small bold font to the field name label
            lbl.setStyleSheet(f"color: {P.text_muted};")   # colours the field name in the muted text colour
            row.addWidget(lbl)   # adds the field name label to the left of the row
            vlbl = QLabel(str(value))   # creates the value label showing the actual complaint data
            vlbl.setFont(qfont(F.small))   # applies the small font to the value label
            vlbl.setStyleSheet(f"color: {color};")   # colours the value in its designated status colour
            vlbl.setWordWrap(True)   # allows long values to wrap within the detail panel width
            row.addWidget(vlbl, 1)   # value label stretches to fill remaining row width
            self._detail_layout.addLayout(row)   # adds the label-value pair row to the detail panel

        if c.get("description"):
            div = QFrame()
            div.setFrameShape(QFrame.HLine)   # horizontal divider line before the full description block
            div.setStyleSheet(f"color: {P.divider};")
            self._detail_layout.addWidget(div)   # adds the divider to the detail panel
            dlbl = QLabel("Description:")   # bold "Description:" heading above the full complaint text
            dlbl.setFont(qfont(F.small_bold))   # applies the small bold font to the description heading
            dlbl.setStyleSheet(f"color: {P.text_muted};")   # colours the description heading in the muted text colour
            self._detail_layout.addWidget(dlbl)   # adds the description heading to the panel
            desc = QLabel(c["description"])   # label showing the full complaint description text
            desc.setFont(qfont(F.small))   # applies the small font to the description text
            desc.setStyleSheet(f"color: {P.text_secondary};")   # colours the description in secondary text colour
            desc.setWordWrap(True)   # wraps long description text within the panel width
            self._detail_layout.addWidget(desc)   # adds the description text label to the panel

        self._detail_layout.addStretch()   # pushes all detail rows to the top of the panel

    def _open_add(self):
        dlg = _ComplaintDialog(self)   # opens the Log Complaint dialog
        if dlg.exec() == QDialog.Accepted:
            self._reload()   # refreshes the table if a new complaint was successfully submitted

    def _update_status(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a complaint first.")   # blocks action if no row is selected
            return
        dlg = _StatusDialog(self, cid=self._selected_id)   # opens the status dropdown dialog for the selected complaint
        if dlg.exec() == QDialog.Accepted:
            self._reload()   # refreshes the table after the status was changed

    def _resolve(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a complaint first.")   # blocks action if no row is selected
            return
        ans = QMessageBox.question(self, "Confirm",
                                   "Mark this complaint as Resolved?")   # shows a Yes/No confirmation dialog before resolving
        if ans == QMessageBox.Yes:
            db.updateStatus(self._selected_id, "Resolved")   # writes "Resolved" status to the database for this complaint
            self._reload()   # refreshes the table to reflect the updated status
            Toast(self.window(), "Complaint resolved.", kind="success")   # shows a green success notification


# ──────────────────────────────────────────────────────────
# ADD COMPLAINT DIALOG
# ──────────────────────────────────────────────────────────
class _ComplaintDialog(QDialog):   # popup dialog for logging a brand-new tenant complaint
    def __init__(self, parent):
        super().__init__(parent)   # attaches this dialog to the parent window so it stays on top
        self.setWindowTitle("Log Complaint")   # sets the dialog title in the OS title bar
        self.setMinimumSize(480, 380)   # prevents the dialog from being shrunk below 480×380 px
        self.resize(480, 420)   # opens the dialog at 480 wide by 420 tall
        self._build()   # draws all the widgets inside the dialog

    def _build(self):
        lay = QVBoxLayout(self)   # stacks all dialog sections vertically
        lay.setSpacing(6)   # 6 px gap between each stacked section

        title = QLabel("Log Tenant Complaint")   # bold heading shown at the top of the dialog
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))   # 18pt bold heading font
        title.setStyleSheet(f"color: {P.text_primary};")   # colours the heading in the primary text colour
        title.setAlignment(Qt.AlignCenter)   # centres the heading horizontally
        lay.addWidget(title)   # adds the heading to the top of the dialog layout

        # Tenant
        lay.addWidget(self._lbl("Tenant"))   # adds a grey "Tenant" section label above the dropdown
        tenants = db.get_all_tenants()   # fetches every tenant record from the database
        self._tenant_combo = QComboBox()   # dropdown for selecting which tenant raised the complaint
        self._tenant_combo.addItems(
            [f"{t['id']} — {t['full_name']}" for t in tenants])   # populates dropdown with "ID — Full Name" entries
        lay.addWidget(self._tenant_combo)   # adds the tenant dropdown to the dialog layout

        # Subject
        lay.addWidget(self._lbl("Subject"))   # adds a grey "Subject" section label above the title input
        self._title_e = QLineEdit()   # single-line text input for the short complaint subject (required)
        self._title_e.setPlaceholderText("Brief subject")   # ghost text shown when the subject field is empty
        self._title_e.setFixedHeight(38)   # fixes input height to 38 px to match other fields
        lay.addWidget(self._title_e)   # adds the subject input to the dialog layout

        # Description
        lay.addWidget(self._lbl("Full Description"))   # adds a grey "Full Description" section label
        self._desc_e = QLineEdit()   # single-line input for a longer explanation of the complaint
        self._desc_e.setPlaceholderText("Detailed description of complaint")   # ghost text shown when the description field is empty
        self._desc_e.setFixedHeight(38)   # fixes description input height to 38 px
        lay.addWidget(self._desc_e)   # adds the description input to the dialog layout

        lay.addStretch()   # pushes all form fields to the top and the button row to the bottom

        btn_row = QHBoxLayout()   # horizontal row for the action buttons at the bottom
        btn_save = styled_button("Submit Complaint", "warning")   # amber "Submit Complaint" button that triggers _save
        btn_save.setFixedHeight(42)   # fixes button height to 42 px
        btn_save.setFixedWidth(200)   # fixes button width to 200 px
        btn_save.clicked.connect(self._save)   # connects the button click to the _save method
        btn_row.addWidget(btn_save)   # adds the save button to the button row
        btn_cancel = styled_button("Cancel", "outline")   # outlined "Cancel" button that dismisses the dialog
        btn_cancel.setFixedHeight(42)   # fixes cancel button height to 42 px
        btn_cancel.setFixedWidth(120)   # fixes cancel button width to 120 px
        btn_cancel.clicked.connect(self.reject)   # clicking Cancel closes the dialog with Rejected result
        btn_row.addWidget(btn_cancel)   # adds the cancel button to the button row
        btn_row.addStretch()   # pushes both buttons to the left
        lay.addLayout(btn_row)   # adds the button row to the bottom of the dialog layout

    def _lbl(self, text):
        l = QLabel(text)   # creates a plain text label for a form section heading
        l.setFont(qfont(F.label))   # applies the standard label font size
        l.setStyleSheet(f"color: {P.text_secondary};")   # colours the label in the muted secondary text colour
        return l   # returns the ready-to-use label widget

    def _save(self):
        t_str = self._tenant_combo.currentText()   # reads the selected "ID — Name" string from the tenant dropdown
        title = self._title_e.text().strip()   # reads and trims the complaint subject from its input field
        desc = self._desc_e.text().strip()   # reads and trims the full description from its input field

        if not title:
            QMessageBox.critical(self, "Validation", "Subject is required.")   # blocks save if no subject was entered
            return
        try:
            tid = int(t_str.split("—")[0].strip()) if t_str else None   # parses the numeric tenant ID from before the "—"
        except ValueError:
            tid = None   # falls back to None if parsing fails
        if not tid:
            QMessageBox.critical(self, "Validation", "Please select a tenant.")   # blocks save if no valid tenant was selected
            return

        db.add_complaint(tid, title, desc)   # inserts the new complaint record into the database
        Toast(self.window(), "Complaint logged successfully.")   # shows a brief success notification
        self.accept()   # closes the dialog with Accepted result, triggering a table reload in the parent


# ──────────────────────────────────────────────────────────
# UPDATE STATUS DIALOG
# ──────────────────────────────────────────────────────────
class _StatusDialog(QDialog):   # small popup dialog for quickly changing the status of a complaint
    def __init__(self, parent, cid: int):
        super().__init__(parent)   # attaches this dialog to the parent window
        self._cid = cid   # stores the complaint ID whose status will be updated
        self.setWindowTitle("Update Complaint Status")   # sets the dialog title in the OS title bar
        self.setFixedSize(360, 200)   # locks the dialog to exactly 360×200 px (cannot be resized)
        self._build()   # draws all the widgets inside the dialog

    def _build(self):
        lay = QVBoxLayout(self)   # stacks the heading, dropdown, and button vertically
        lbl = QLabel("New Status")   # bold heading telling the user what the dropdown is for
        lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))   # 14pt bold heading font
        lbl.setStyleSheet(f"color: {P.text_primary};")   # colours the heading in the primary text colour
        lbl.setAlignment(Qt.AlignCenter)   # centres the heading horizontally
        lay.addWidget(lbl)   # adds the heading to the top of the dialog layout

        self._combo = QComboBox()   # dropdown listing the three possible complaint statuses
        self._combo.addItems(["Open", "In Progress", "Resolved"])   # adds all three status options
        self._combo.setCurrentIndex(1)   # pre-selects "In Progress" as the most common next step
        lay.addWidget(self._combo)   # adds the status dropdown to the layout

        btn = styled_button("Apply", "primary")   # blue "Apply" button that triggers _apply
        btn.setFixedHeight(38)   # fixes the apply button height to 38 px
        btn.clicked.connect(self._apply)   # connects the button click to the _apply method
        lay.addWidget(btn)   # adds the apply button to the bottom of the layout

    def _apply(self):
        db.updateStatus(self._cid, self._combo.currentText())   # saves the newly selected status to the database for this complaint
        Toast(self.window(),
              f"Status updated to '{self._combo.currentText()}'")   # shows a brief notification confirming the status change
        self.accept()   # closes the dialog with Accepted result, triggering a table reload in the parent
