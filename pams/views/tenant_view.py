# ============================================================
# PAMS — views/tenant_view.py
# Full Tenant Management CRUD View (PySide6)
# ============================================================
from __future__ import annotations
import datetime, re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDialog, QMessageBox, QFormLayout,
    QScrollArea, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..theme import PALETTE as P, FONTS as F, DIMS as D, lerp_color
from ..widgets import (
    qfont, Card, section_header, make_table, table_clear,
    table_insert, table_selected_id, badge_text, styled_button, Toast,
    STATUS_COLORS,
)
from .. import database as db

_NI_RE    = re.compile(r'^(NI-)?[A-Z]{2}\d{6}[A-Z]$', re.IGNORECASE)
_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


class TenantView(QWidget):
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

        section_header(lay, "Tenant Management",
                       "View, add, update and remove tenant records")

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(D.pad_lg, D.pad_sm, D.pad_lg, D.pad_sm)

        search_icon = QLabel("🔍")
        search_icon.setStyleSheet(f"color: {P.text_muted};")
        toolbar.addWidget(search_icon)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search tenants...")
        self._search.setFixedHeight(38)
        self._search.setFixedWidth(260)
        self._search.textChanged.connect(self._reload)
        toolbar.addWidget(self._search)

        btn_add = styled_button("+ Add Tenant", "primary")
        btn_add.clicked.connect(self._open_add_dialog)
        toolbar.addWidget(btn_add)

        if self._user["role"] in ("Administrator", "Manager"):
            btn_edit = styled_button("Edit", "outline")
            btn_edit.clicked.connect(self._open_edit_dialog)
            toolbar.addWidget(btn_edit)

            btn_rm = styled_button("Remove", "danger")
            btn_rm.clicked.connect(self._remove_tenant)
            toolbar.addWidget(btn_rm)

        btn_early = styled_button("Early Leave", "warning")
        btn_early.clicked.connect(self._early_leave)
        toolbar.addWidget(btn_early)

        btn_hist = styled_button("Payment History", "outline")
        btn_hist.clicked.connect(self._payment_history)
        toolbar.addWidget(btn_hist)

        toolbar.addStretch()
        self._count_lbl = QLabel("")
        self._count_lbl.setFont(qfont(F.small))
        self._count_lbl.setStyleSheet(f"color: {P.text_muted};")
        toolbar.addWidget(self._count_lbl)
        lay.addLayout(toolbar)

        # ── Table card ──
        card = Card(title="", accent_color=P.accent)
        cols = [
            ("#", 40), ("NI Number", 110), ("Full Name", 160),
            ("Phone", 110), ("Apartment", 90), ("City", 90),
            ("Lease Start", 90), ("Lease End", 90),
            ("Monthly Rent", 100), ("Status", 90),
        ]
        self._table, self._model = make_table(card.body_layout(), cols)
        self._table.clicked.connect(self._on_select)
        lay.addWidget(card, 1)

    def _reload(self):
        table_clear(self._model)
        tenants = db.get_all_tenants(self._loc)
        q = self._search.text().lower()
        shown = 0
        for t in tenants:
            if q and q not in (t["full_name"] + t["ni_number"]).lower():
                continue
            color = STATUS_COLORS.get(t["status"], P.text_muted)
            table_insert(self._model, [
                str(t["id"]),
                t["ni_number"],
                t["full_name"],
                t.get("phone") or "—",
                t.get("apt_number") or "—",
                t.get("location") or "—",
                t.get("lease_start") or "—",
                t.get("lease_end") or "—",
                f"£{t.get('monthly_rent') or 0:,.0f}",
                badge_text(t["status"]),
            ], color)
            shown += 1
        self._count_lbl.setText(f"{shown} record(s)")
        self._selected_id = None

    def _on_select(self, index):
        tid = table_selected_id(self._table, self._model, 0)
        if tid is not None:
            try:
                self._selected_id = int(tid)
            except ValueError:
                self._selected_id = None

    def _open_add_dialog(self):
        dlg = _TenantDialog(self, mode="add")
        if dlg.exec() == QDialog.Accepted:
            self._reload()

    def _open_edit_dialog(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Please select a tenant first.")
            return
        tenant = db.get_tenant_by_id(self._selected_id)
        if tenant:
            dlg = _TenantDialog(self, mode="edit", tenant=tenant)
            if dlg.exec() == QDialog.Accepted:
                self._reload()

    def _remove_tenant(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Please select a tenant first.")
            return
        ans = QMessageBox.question(
            self, "Confirm", "Remove this tenant and free their apartment?")
        if ans == QMessageBox.Yes:
            db.delete_tenant(self._selected_id)
            self._reload()
            Toast(self.window(), "Tenant removed.", kind="info")

    def _early_leave(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Please select a tenant first.")
            return
        tenant = db.get_tenant_by_id(self._selected_id)
        if not tenant:
            return
        if tenant["status"] != "Active":
            QMessageBox.warning(self, "Status",
                                "Only active tenants can request early leave.")
            return
        monthly = tenant.get("monthly_rent") or 0
        penalty = round(monthly * 0.05, 2)
        leave_date = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
        msg = (
            f"Tenant: {tenant['full_name']}\n"
            f"Monthly Rent: £{monthly:,.2f}\n"
            f"Early Leave Penalty (5%): £{penalty:,.2f}\n"
            f"Notice Period: 1 month\n"
            f"Leave Date: {leave_date}\n\n"
            f"A penalty invoice of £{penalty:,.2f} will be created.\n"
            f"Proceed with early termination?"
        )
        ans = QMessageBox.question(
            self, "Early Leave — Contract Termination", msg)
        if ans == QMessageBox.Yes:
            result, info = db.terminateEarly(self._selected_id)
            if result is not None:
                self._reload()
                Toast(self.window(),
                      f"Early leave processed. Penalty: £{result:,.2f}. "
                      f"Leave date: {info}")
            else:
                QMessageBox.critical(self, "Error", info)

    def _payment_history(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Please select a tenant first.")
            return
        tenant = db.get_tenant_by_id(self._selected_id)
        if not tenant:
            return
        payments = db.get_tenant_payments(self._selected_id)
        dlg = _PaymentHistoryDialog(self, tenant, payments)
        dlg.exec()


# ──────────────────────────────────────────────────────────
# TENANT ADD / EDIT DIALOG
# ──────────────────────────────────────────────────────────
class _TenantDialog(QDialog):
    def __init__(self, parent, mode="add", tenant=None):
        super().__init__(parent)
        self._mode = mode
        self._tenant = tenant
        self.setWindowTitle("Add Tenant" if mode == "add" else "Edit Tenant")
        self.setMinimumSize(540, 680)
        self.resize(540, 780)
        self._build()
        if tenant:
            self._populate(tenant)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)

        title = QLabel("Add Tenant" if self._mode == "add" else "Edit Tenant")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"color: {P.text_primary};")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        form_w = QWidget()
        fl = QVBoxLayout(form_w)
        fl.setSpacing(4)

        fields = [
            ("NI Number",       "ni",         "e.g. AB123456C"),
            ("Full Name",       "name",       "Full legal name"),
            ("Phone",           "phone",      "07xxx xxxxxx"),
            ("Email",           "email",      "email@domain.com"),
            ("Occupation",      "occupation", "Role / Job title"),
            ("Reference",       "reference",  "Reference contact name"),
            ("Apt Requirements","apt_req",    "e.g. 2-Bedroom house"),
            ("Lease Start",     "lease_start","YYYY-MM-DD"),
            ("Lease End Date",  "lease_end",  "YYYY-MM-DD"),
            ("Deposit (£)",     "deposit",    "e.g. 1200.00"),
            ("Monthly Rent (£)","monthly_rent","e.g. 1200.00"),
            ("Notes",           "notes",      "Any additional notes"),
        ]
        self._entries: dict[str, QLineEdit] = {}
        for label, key, ph in fields:
            lbl = QLabel(label)
            lbl.setFont(qfont(F.label))
            lbl.setStyleSheet(f"color: {P.text_secondary};")
            fl.addWidget(lbl)
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setFixedHeight(38)
            fl.addWidget(e)
            self._entries[key] = e

        # Apartment picker (add mode)
        if self._mode == "add":
            lbl = QLabel("Assign Apartment")
            lbl.setFont(qfont(F.label))
            lbl.setStyleSheet(f"color: {P.text_secondary};")
            fl.addWidget(lbl)
            apts = db.get_vacant_apartments()
            self._apt_combo = QComboBox()
            apt_labels = [f"{aid} — {alabel}" for aid, alabel in apts]
            if not apt_labels:
                apt_labels = ["No vacant apartments"]
            self._apt_combo.addItems(apt_labels)
            fl.addWidget(self._apt_combo)

        # Status (edit mode)
        if self._mode == "edit":
            lbl = QLabel("Status")
            lbl.setFont(qfont(F.label))
            lbl.setStyleSheet(f"color: {P.text_secondary};")
            fl.addWidget(lbl)
            self._status_combo = QComboBox()
            self._status_combo.addItems(["Active", "Inactive", "Leaving"])
            fl.addWidget(self._status_combo)

        scroll.setWidget(form_w)
        lay.addWidget(scroll, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_save = styled_button("Save", "primary")
        btn_save.setFixedHeight(42)
        btn_save.setFixedWidth(200)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)
        btn_cancel = styled_button("Cancel", "outline")
        btn_cancel.setFixedHeight(42)
        btn_cancel.setFixedWidth(130)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def _populate(self, t: dict):
        self._entries["ni"].setText(t.get("ni_number", ""))
        self._entries["name"].setText(t.get("full_name", ""))
        self._entries["phone"].setText(t.get("phone", ""))
        self._entries["email"].setText(t.get("email", ""))
        self._entries["occupation"].setText(t.get("occupation", ""))
        self._entries["reference"].setText(t.get("reference", ""))
        self._entries["apt_req"].setText(t.get("apartment_requirements", ""))
        self._entries["lease_start"].setText(t.get("lease_start", ""))
        self._entries["lease_end"].setText(t.get("lease_end", ""))
        self._entries["deposit"].setText(str(t.get("deposit") or ""))
        self._entries["monthly_rent"].setText(str(t.get("monthly_rent") or ""))
        self._entries["notes"].setText(t.get("notes", ""))
        if hasattr(self, "_status_combo"):
            idx = self._status_combo.findText(t.get("status", "Active"))
            if idx >= 0:
                self._status_combo.setCurrentIndex(idx)

    def _save(self):
        ni       = self._entries["ni"].text().strip()
        name     = self._entries["name"].text().strip()
        phone    = self._entries["phone"].text().strip()
        email    = self._entries["email"].text().strip()
        occ      = self._entries["occupation"].text().strip()
        ref      = self._entries["reference"].text().strip()
        apt_req  = self._entries["apt_req"].text().strip()
        le_start = self._entries["lease_start"].text().strip()
        le       = self._entries["lease_end"].text().strip()
        deposit_s= self._entries["deposit"].text().strip()
        rent_s   = self._entries["monthly_rent"].text().strip()
        notes    = self._entries["notes"].text().strip()
        status   = (self._status_combo.currentText()
                    if hasattr(self, "_status_combo") else "Active")

        if not ni or not name:
            QMessageBox.critical(self, "Validation",
                                 "NI Number and Name are required.")
            return
        if not _NI_RE.match(ni):
            QMessageBox.critical(self, "Validation",
                "Invalid NI Number format.\n"
                "Expected: 2 letters + 6 digits + 1 letter (e.g. AB123456C)\n"
                "Prefix 'NI-' is optional.")
            return
        if email and not _EMAIL_RE.match(email):
            QMessageBox.critical(self, "Validation", "Invalid email format.")
            return

        try:
            deposit = float(deposit_s) if deposit_s else 0.0
        except ValueError:
            QMessageBox.critical(self, "Validation", "Deposit must be a number.")
            return
        try:
            monthly_rent = float(rent_s) if rent_s else 0.0
        except ValueError:
            QMessageBox.critical(self, "Validation", "Monthly Rent must be a number.")
            return

        if self._mode == "add":
            today = le_start or datetime.date.today().isoformat()
            end = le or (datetime.date.today() +
                         datetime.timedelta(days=365)).isoformat()
            apt_str = (self._apt_combo.currentText()
                       if hasattr(self, "_apt_combo") else "")
            apt_id = None
            if apt_str and "—" in apt_str:
                try:
                    apt_id = int(apt_str.split("—")[0].strip())
                except Exception:
                    pass
            try:
                db.add_tenant(ni, name, phone, email, occ, ref,
                              apt_req, apt_id, today, end, deposit, monthly_rent)
            except Exception as ex:
                QMessageBox.critical(self, "Error", str(ex))
                return
        else:
            le_start_val = le_start or self._tenant.get("lease_start", "")
            le_val = le or self._tenant.get("lease_end", "")
            db.update_tenant(self._tenant["id"], ni, name, phone, email,
                             occ, ref, apt_req, le_start_val, le_val,
                             deposit, monthly_rent, status, notes)

        Toast(self.window(),
              f"Tenant {'added' if self._mode=='add' else 'updated'} successfully!")
        self.accept()


# ──────────────────────────────────────────────────────────
# PAYMENT HISTORY DIALOG
# ──────────────────────────────────────────────────────────
class _PaymentHistoryDialog(QDialog):
    def __init__(self, parent, tenant: dict, payments: list):
        super().__init__(parent)
        self.setWindowTitle(f"Payment History — {tenant['full_name']}")
        self.setMinimumSize(600, 450)
        self.resize(600, 450)

        lay = QVBoxLayout(self)
        title = QLabel(f"Payment History: {tenant['full_name']}")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {P.text_primary};")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        sub = QLabel(f"NI: {tenant['ni_number']}  |  "
                     f"Rent: £{tenant.get('monthly_rent') or 0:,.2f}/month")
        sub.setFont(qfont(F.small))
        sub.setStyleSheet(f"color: {P.text_secondary};")
        sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(sub)

        cols = [("#", 40), ("Amount", 90), ("Type", 110),
                ("Due", 90), ("Paid", 90), ("Status", 80)]
        table, model = make_table(lay, cols)
        for p in payments:
            color = STATUS_COLORS.get(p["status"], P.text_muted)
            table_insert(model, [
                str(p["id"]),
                f"£{p['amount']:,.2f}",
                p.get("type") or "Rent",
                p["due_date"],
                p.get("paid_date") or "—",
                badge_text(p["status"]),
            ], color)

        btn = styled_button("Close", "outline")
        btn.setFixedHeight(38)
        btn.setFixedWidth(120)
        btn.clicked.connect(self.accept)
        lay.addWidget(btn, 0, Qt.AlignCenter)
