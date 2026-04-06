# ============================================================
# PAMS — views/tenant_view.py
# Full Tenant Management CRUD View (PySide6)
# ============================================================
from __future__ import annotations   # allows forward type hints in older Python versions
import datetime, re   # datetime for lease date calculations; re for NI and email regex validation

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDialog, QMessageBox, QFormLayout,
    QScrollArea, QFrame, QSizePolicy,   # QScrollArea for scrollable dialogs; QFrame for divider lines
)
from PySide6.QtCore import Qt   # Qt namespace for alignment flags and cursor shapes
from PySide6.QtGui import QFont   # QFont for setting bold title fonts in dialogs

from ..theme import PALETTE as P, FONTS as F, DIMS as D, lerp_color   # P=colours, F=font sizes, D=spacing/size tokens
from ..widgets import (
    qfont, Card, section_header, make_table, table_clear,
    table_insert, table_selected_id, badge_text, styled_button, Toast,
    STATUS_COLORS,   # STATUS_COLORS maps Active/Inactive/Leaving to green/red/amber text colours
)
from .. import database as db   # db module provides all SQL queries for tenants, payments and apartments

_NI_RE    = re.compile(r'^(NI-)?[A-Z]{2}\d{6}[A-Z]$', re.IGNORECASE)   # regex that accepts NI numbers like 'AB123456C' with optional 'NI-' prefix
_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')   # standard email format validator


class TenantView(QWidget):
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self._user = user   # the full user dict (contains role, location, name)
        self._loc = user.get("location")   # branch location filter applied to all DB queries
        self._selected_id = None   # tracks which tenant row is currently selected in the table
        self._build()   # constructs the toolbar and table layout
        self._reload()   # loads all tenant rows from the database on first open

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)   # no outer padding so the card stretches edge to edge
        lay.setSpacing(8)   # 8px gap between the section header, toolbar and card

        section_header(lay, "Tenant Management",
                       "View, add, update and remove tenant records")   # draws the page title and subtitle bar

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(D.pad_lg, D.pad_sm, D.pad_lg, D.pad_sm)   # large horizontal padding, small vertical padding

        search_icon = QLabel("🔍")
        search_icon.setStyleSheet(f"color: {P.text_muted};")   # muted magnifier icon sits to the left of the search field
        toolbar.addWidget(search_icon)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search tenants...")   # hint text inside the search box
        self._search.setFixedHeight(38)   # standardised 38px height for the search field
        self._search.setFixedWidth(260)   # fixed 260px width so it doesn't crowd the action buttons
        self._search.textChanged.connect(self._reload)   # re-filters the table every time the user types a character
        toolbar.addWidget(self._search)

        btn_add = styled_button("+ Add Tenant", "primary")   # indigo primary button to open the add-tenant dialog
        btn_add.clicked.connect(self._open_add_dialog)   # wires click to the dialog launcher
        toolbar.addWidget(btn_add)

        if self._user["role"] in ("Administrator", "Manager"):   # edit and delete are hidden from front-desk and other lower roles
            btn_edit = styled_button("Edit", "outline")   # outline button to open the edit dialog for the selected tenant
            btn_edit.clicked.connect(self._open_edit_dialog)
            toolbar.addWidget(btn_edit)

            btn_rm = styled_button("Remove", "danger")   # red danger button to permanently delete the selected tenant
            btn_rm.clicked.connect(self._remove_tenant)
            toolbar.addWidget(btn_rm)

        btn_early = styled_button("Early Leave", "warning")   # amber button to trigger an early contract termination with 5% penalty
        btn_early.clicked.connect(self._early_leave)
        toolbar.addWidget(btn_early)

        btn_hist = styled_button("Payment History", "outline")   # outline button to open a read-only payment history dialog
        btn_hist.clicked.connect(self._payment_history)
        toolbar.addWidget(btn_hist)

        toolbar.addStretch()   # pushes the record count label to the far right
        self._count_lbl = QLabel("")
        self._count_lbl.setFont(qfont(F.small))
        self._count_lbl.setStyleSheet(f"color: {P.text_muted};")   # muted small font shows how many rows are visible
        toolbar.addWidget(self._count_lbl)
        lay.addLayout(toolbar)

        # ── Table card ──
        card = Card(title="", accent_color=P.accent)   # borderless card container (no title text) with the indigo accent stripe
        cols = [
            ("#", 40), ("NI Number", 110), ("Full Name", 160),
            ("Phone", 110), ("Apartment", 90), ("City", 90),
            ("Lease Start", 90), ("Lease End", 90),
            ("Monthly Rent", 100), ("Status", 90),   # 10 columns showing all key tenant fields
        ]
        self._table, self._model = make_table(card.body_layout(), cols)   # builds the read-only styled table; model holds row data
        self._table.clicked.connect(self._on_select)   # records which row the user has clicked on
        lay.addWidget(card, 1)   # card stretches to fill all remaining vertical space

    def _reload(self):
        table_clear(self._model)   # removes all existing rows before repopulating the table
        tenants = db.get_all_tenants(self._loc)   # fetches all tenants for this branch from the database
        q = self._search.text().lower()   # current search query in lowercase for case-insensitive matching
        shown = 0   # counter used to update the record-count label after filtering
        for t in tenants:
            if q and q not in (t["full_name"] + t["ni_number"]).lower():
                continue   # skips this tenant if neither their name nor NI number matches the search
            color = STATUS_COLORS.get(t["status"], P.text_muted)   # row text colour based on tenant status
            table_insert(self._model, [
                str(t["id"]),
                t["ni_number"],
                t["full_name"],
                t.get("phone") or "—",   # dash if no phone number recorded
                t.get("apt_number") or "—",   # dash if no apartment assigned
                t.get("location") or "—",   # dash if no city/location recorded
                t.get("lease_start") or "—",
                t.get("lease_end") or "—",
                f"£{t.get('monthly_rent') or 0:,.0f}",   # formats rent as £1,200 with comma thousands separator
                badge_text(t["status"]),   # converts status string to a coloured badge symbol
            ], color)
            shown += 1   # increments visible row counter
        self._count_lbl.setText(f"{shown} record(s)")   # updates the record count at the right of the toolbar
        self._selected_id = None   # clears selection whenever the table is reloaded

    def _on_select(self, index):
        tid = table_selected_id(self._table, self._model, 0)   # reads the value from column 0 (the ID) of the clicked row
        if tid is not None:
            try:
                self._selected_id = int(tid)   # converts the ID string to int and stores it for action buttons
            except ValueError:
                self._selected_id = None   # resets to None if the ID is somehow not a valid integer

    def _open_add_dialog(self):
        dlg = _TenantDialog(self, mode="add")   # creates an empty 'Add Tenant' dialog
        if dlg.exec() == QDialog.Accepted:   # only reloads if the user clicked Save (not Cancel)
            self._reload()

    def _open_edit_dialog(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Please select a tenant first.")
            return   # prevents opening the edit dialog with no row selected
        tenant = db.get_tenant_by_id(self._selected_id)   # fetches all fields for the selected tenant
        if tenant:
            dlg = _TenantDialog(self, mode="edit", tenant=tenant)   # pre-populates the dialog with existing data
            if dlg.exec() == QDialog.Accepted:
                self._reload()

    def _remove_tenant(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Please select a tenant first.")
            return
        ans = QMessageBox.question(
            self, "Confirm", "Remove this tenant and free their apartment?")   # asks for confirmation before deleting
        if ans == QMessageBox.Yes:
            db.delete_tenant(self._selected_id)   # deletes the tenant record and sets their apartment back to Vacant
            self._reload()
            Toast(self.window(), "Tenant removed.", kind="info")   # shows a brief info toast in the top-right corner

    def _early_leave(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Please select a tenant first.")
            return
        tenant = db.get_tenant_by_id(self._selected_id)   # fetches the full record to check status and monthly rent
        if not tenant:
            return
        if tenant["status"] != "Active":
            QMessageBox.warning(self, "Status",
                                "Only active tenants can request early leave.")
            return   # blocks early leave for tenants who are already inactive or leaving
        monthly = tenant.get("monthly_rent") or 0
        penalty = round(monthly * 0.05, 2)   # calculates the 5% early termination penalty on the monthly rent
        leave_date = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()   # sets a 30-day notice period from today
        msg = (
            f"Tenant: {tenant['full_name']}\n"
            f"Monthly Rent: £{monthly:,.2f}\n"
            f"Early Leave Penalty (5%): £{penalty:,.2f}\n"
            f"Notice Period: 1 month\n"
            f"Leave Date: {leave_date}\n\n"
            f"A penalty invoice of £{penalty:,.2f} will be created.\n"
            f"Proceed with early termination?"   # shows all early leave details in the confirmation dialog
        )
        ans = QMessageBox.question(
            self, "Early Leave — Contract Termination", msg)
        if ans == QMessageBox.Yes:
            result, info = db.terminateEarly(self._selected_id)   # calls the DB function that sets status to Leaving and logs the penalty
            if result is not None:
                self._reload()
                Toast(self.window(),
                      f"Early leave processed. Penalty: £{result:,.2f}. "
                      f"Leave date: {info}")   # confirms with the penalty amount and calculated leave date
            else:
                QMessageBox.critical(self, "Error", info)   # shows the DB error if the termination fails

    def _payment_history(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Please select a tenant first.")
            return
        tenant = db.get_tenant_by_id(self._selected_id)   # loads tenant name, NI, and rent for the dialog header
        if not tenant:
            return
        payments = db.get_tenant_payments(self._selected_id)   # fetches all payment records for this specific tenant
        dlg = _PaymentHistoryDialog(self, tenant, payments)   # opens the read-only payment history dialog
        dlg.exec()


# ──────────────────────────────────────────────────────────
# TENANT ADD / EDIT DIALOG
# ──────────────────────────────────────────────────────────
class _TenantDialog(QDialog):
    def __init__(self, parent, mode="add", tenant=None):
        super().__init__(parent)
        self._mode = mode   # "add" creates a new record; "edit" updates an existing one
        self._tenant = tenant   # dict of existing tenant data used to pre-fill the form in edit mode
        self.setWindowTitle("Add Tenant" if mode == "add" else "Edit Tenant")   # dialog title bar shows the current mode
        self.setMinimumSize(540, 680)   # minimum size prevents the form fields from being clipped
        self.resize(540, 780)   # default opening size is 540×780 pixels
        self._build()   # constructs all form labels, inputs and buttons
        if tenant:
            self._populate(tenant)   # fills in existing values when editing

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)   # 6px gap between each form row

        title = QLabel("Add Tenant" if self._mode == "add" else "Edit Tenant")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))   # large 18pt bold heading inside the dialog
        title.setStyleSheet(f"color: {P.text_primary};")
        title.setAlignment(Qt.AlignCenter)   # centred heading at the top of the dialog
        lay.addWidget(title)

        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)   # allows the form widget to stretch to fill the scroll area
        scroll.setFrameShape(QFrame.NoFrame)   # removes the default border around the scroll area
        form_w = QWidget()
        fl = QVBoxLayout(form_w)
        fl.setSpacing(4)   # tight 4px spacing between label-input pairs

        fields = [
            ("NI Number",       "ni",         "e.g. AB123456C"),   # National Insurance number (required, validated by regex)
            ("Full Name",       "name",       "Full legal name"),   # tenant's full legal name (required)
            ("Phone",           "phone",      "07xxx xxxxxx"),
            ("Email",           "email",      "email@domain.com"),
            ("Occupation",      "occupation", "Role / Job title"),
            ("Reference",       "reference",  "Reference contact name"),
            ("Apt Requirements","apt_req",    "e.g. 2-Bedroom house"),   # free-text preference for apartment type
            ("Lease Start",     "lease_start","YYYY-MM-DD"),   # ISO date format for lease start
            ("Lease End Date",  "lease_end",  "YYYY-MM-DD"),   # ISO date format for lease end
            ("Deposit (£)",     "deposit",    "e.g. 1200.00"),   # numeric deposit amount (converted to float on save)
            ("Monthly Rent (£)","monthly_rent","e.g. 1200.00"),   # numeric monthly rent (converted to float on save)
            ("Notes",           "notes",      "Any additional notes"),   # optional free-text notes field
        ]
        self._entries: dict[str, QLineEdit] = {}   # stores each input widget keyed by field name for easy access on save
        for label, key, ph in fields:
            lbl = QLabel(label)
            lbl.setFont(qfont(F.label))
            lbl.setStyleSheet(f"color: {P.text_secondary};")   # secondary grey label above each input
            fl.addWidget(lbl)
            e = QLineEdit()
            e.setPlaceholderText(ph)   # shows the expected format as grey hint text
            e.setFixedHeight(38)   # all inputs are 38px tall for visual consistency
            fl.addWidget(e)
            self._entries[key] = e   # saves the widget keyed by the field's internal name

        # Apartment picker (add mode)
        if self._mode == "add":   # only shown when adding a new tenant, not when editing
            lbl = QLabel("Assign Apartment")
            lbl.setFont(qfont(F.label))
            lbl.setStyleSheet(f"color: {P.text_secondary};")
            fl.addWidget(lbl)
            apts = db.get_vacant_apartments()   # queries the DB for all apartments with 'Vacant' status
            self._apt_combo = QComboBox()
            apt_labels = [f"{aid} — {alabel}" for aid, alabel in apts]   # "ID — Unit Label" format for each vacant apartment
            if not apt_labels:
                apt_labels = ["No vacant apartments"]   # placeholder when there are no available units
            self._apt_combo.addItems(apt_labels)   # populates the dropdown with vacant apartment options
            fl.addWidget(self._apt_combo)

        # Status (edit mode)
        if self._mode == "edit":   # status picker is only shown when editing an existing tenant
            lbl = QLabel("Status")
            lbl.setFont(qfont(F.label))
            lbl.setStyleSheet(f"color: {P.text_secondary};")
            fl.addWidget(lbl)
            self._status_combo = QComboBox()
            self._status_combo.addItems(["Active", "Inactive", "Leaving"])   # the three valid tenant status values
            fl.addWidget(self._status_combo)

        scroll.setWidget(form_w)   # places the form widget inside the scrollable viewport
        lay.addWidget(scroll, 1)   # scroll area stretches to fill all remaining dialog space

        # Buttons
        btn_row = QHBoxLayout()
        btn_save = styled_button("Save", "primary")   # primary indigo Save button
        btn_save.setFixedHeight(42)   # slightly taller than normal for the main action button
        btn_save.setFixedWidth(200)
        btn_save.clicked.connect(self._save)   # wires Save button to the validation and DB write logic
        btn_row.addWidget(btn_save)
        btn_cancel = styled_button("Cancel", "outline")   # outline Cancel button dismisses the dialog without saving
        btn_cancel.setFixedHeight(42)
        btn_cancel.setFixedWidth(130)
        btn_cancel.clicked.connect(self.reject)   # reject() closes the dialog and returns QDialog.Rejected
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()   # pushes buttons to the left
        lay.addLayout(btn_row)

    def _populate(self, t: dict):
        self._entries["ni"].setText(t.get("ni_number", ""))   # fills the NI field with the existing NI number
        self._entries["name"].setText(t.get("full_name", ""))
        self._entries["phone"].setText(t.get("phone", ""))
        self._entries["email"].setText(t.get("email", ""))
        self._entries["occupation"].setText(t.get("occupation", ""))
        self._entries["reference"].setText(t.get("reference", ""))
        self._entries["apt_req"].setText(t.get("apartment_requirements", ""))
        self._entries["lease_start"].setText(t.get("lease_start", ""))
        self._entries["lease_end"].setText(t.get("lease_end", ""))
        self._entries["deposit"].setText(str(t.get("deposit") or ""))   # converts numeric deposit to string for the line edit
        self._entries["monthly_rent"].setText(str(t.get("monthly_rent") or ""))
        self._entries["notes"].setText(t.get("notes", ""))
        if hasattr(self, "_status_combo"):
            idx = self._status_combo.findText(t.get("status", "Active"))   # finds the matching status option in the dropdown
            if idx >= 0:
                self._status_combo.setCurrentIndex(idx)   # selects the tenant's current status in the combo box

    def _save(self):
        ni       = self._entries["ni"].text().strip()   # reads and trims the NI number
        name     = self._entries["name"].text().strip()   # reads the full name
        phone    = self._entries["phone"].text().strip()
        email    = self._entries["email"].text().strip()
        occ      = self._entries["occupation"].text().strip()
        ref      = self._entries["reference"].text().strip()
        apt_req  = self._entries["apt_req"].text().strip()
        le_start = self._entries["lease_start"].text().strip()
        le       = self._entries["lease_end"].text().strip()
        deposit_s= self._entries["deposit"].text().strip()   # raw string from the deposit field before float conversion
        rent_s   = self._entries["monthly_rent"].text().strip()
        notes    = self._entries["notes"].text().strip()
        status   = (self._status_combo.currentText()
                    if hasattr(self, "_status_combo") else "Active")   # defaults to Active in add mode where there's no combo

        if not ni or not name:
            QMessageBox.critical(self, "Validation",
                                 "NI Number and Name are required.")
            return   # stops submission if required fields are empty
        if not _NI_RE.match(ni):
            QMessageBox.critical(self, "Validation",
                "Invalid NI Number format.\n"
                "Expected: 2 letters + 6 digits + 1 letter (e.g. AB123456C)\n"
                "Prefix 'NI-' is optional.")
            return   # rejects NI numbers that don't match the AB123456C pattern
        if email and not _EMAIL_RE.match(email):
            QMessageBox.critical(self, "Validation", "Invalid email format.")
            return   # only validates email if the user actually entered one

        try:
            deposit = float(deposit_s) if deposit_s else 0.0   # converts deposit string to float or defaults to 0
        except ValueError:
            QMessageBox.critical(self, "Validation", "Deposit must be a number.")
            return
        try:
            monthly_rent = float(rent_s) if rent_s else 0.0   # converts rent string to float or defaults to 0
        except ValueError:
            QMessageBox.critical(self, "Validation", "Monthly Rent must be a number.")
            return

        if self._mode == "add":
            today = le_start or datetime.date.today().isoformat()   # uses entered date or today as the lease start
            end = le or (datetime.date.today() +
                         datetime.timedelta(days=365)).isoformat()   # defaults to 12 months from today if no end date given
            apt_str = (self._apt_combo.currentText()
                       if hasattr(self, "_apt_combo") else "")   # reads the selected apartment text
            apt_id = None
            if apt_str and "—" in apt_str:
                try:
                    apt_id = int(apt_str.split("—")[0].strip())   # parses the apartment ID from the "ID — label" format
                except Exception:
                    pass
            try:
                db.add_tenant(ni, name, phone, email, occ, ref,
                              apt_req, apt_id, today, end, deposit, monthly_rent)   # inserts the new tenant into the DB
            except Exception as ex:
                QMessageBox.critical(self, "Error", str(ex))   # shows the DB error if the insert fails
                return
        else:
            le_start_val = le_start or self._tenant.get("lease_start", "")   # keeps original start date if field is cleared
            le_val = le or self._tenant.get("lease_end", "")   # keeps original end date if field is cleared
            db.update_tenant(self._tenant["id"], ni, name, phone, email,
                             occ, ref, apt_req, le_start_val, le_val,
                             deposit, monthly_rent, status, notes)   # updates all fields for the existing tenant record

        Toast(self.window(),
              f"Tenant {'added' if self._mode=='add' else 'updated'} successfully!")   # brief success toast in the top-right corner
        self.accept()   # accept() closes the dialog and returns QDialog.Accepted to trigger a table reload


# ──────────────────────────────────────────────────────────
# PAYMENT HISTORY DIALOG
# ──────────────────────────────────────────────────────────
class _PaymentHistoryDialog(QDialog):
    def __init__(self, parent, tenant: dict, payments: list):
        super().__init__(parent)
        self.setWindowTitle(f"Payment History — {tenant['full_name']}")   # dialog title includes the tenant's name
        self.setMinimumSize(600, 450)
        self.resize(600, 450)   # default size gives enough space for the payment table

        lay = QVBoxLayout(self)
        title = QLabel(f"Payment History: {tenant['full_name']}")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))   # 16pt bold heading with the tenant name
        title.setStyleSheet(f"color: {P.text_primary};")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        sub = QLabel(f"NI: {tenant['ni_number']}  |  "
                     f"Rent: £{tenant.get('monthly_rent') or 0:,.2f}/month")   # subtitle shows NI and monthly rent
        sub.setFont(qfont(F.small))
        sub.setStyleSheet(f"color: {P.text_secondary};")
        sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(sub)

        cols = [("#", 40), ("Amount", 90), ("Type", 110),
                ("Due", 90), ("Paid", 90), ("Status", 80)]   # payment table columns
        table, model = make_table(lay, cols)   # builds a read-only payment table directly in the dialog layout
        for p in payments:
            color = STATUS_COLORS.get(p["status"], P.text_muted)   # text colour for this payment row based on status
            table_insert(model, [
                str(p["id"]),
                f"£{p['amount']:,.2f}",   # formats amount with £ prefix and 2 decimal places
                p.get("type") or "Rent",   # defaults to 'Rent' if no payment type is set
                p["due_date"],
                p.get("paid_date") or "—",   # shows dash if the payment has not been paid yet
                badge_text(p["status"]),   # badge symbol for the payment status
            ], color)

        btn = styled_button("Close", "outline")   # outline button to close the dialog
        btn.setFixedHeight(38)
        btn.setFixedWidth(120)
        btn.clicked.connect(self.accept)   # accept() closes the dialog returning QDialog.Accepted
        lay.addWidget(btn, 0, Qt.AlignCenter)   # centred below the table
