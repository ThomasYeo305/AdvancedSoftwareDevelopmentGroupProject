# ============================================================
# PAMS — views/payment_view.py
# Payment & Billing View (PySide6)
#
# Contributors (UI):
#   Chouaib Hakim       — Student ID: 24018717
#   Sinoli Rodrigo      — Student ID: 24055025
# ============================================================
from __future__ import annotations   # allows forward type hints
import datetime   # used to calculate today's date for the default due-date placeholder

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QRadioButton, QButtonGroup,
    QDialog, QMessageBox, QScrollArea, QFrame,   # QScrollArea for the invoice form; QButtonGroup for the status filter radios
)
from PySide6.QtCore import Qt   # Qt alignment constants
from PySide6.QtGui import QFont   # used for dialog title headings

from ..theme import PALETTE as P, FONTS as F, DIMS as D   # design tokens
from ..widgets import (
    qfont, Card, section_header, make_table, table_clear,
    table_insert, table_selected_id, badge_text, styled_button,
    GradientProgressBar, Toast, STATUS_COLORS, fmt_date,   # GradientProgressBar used for the collection-rate bar strip
)
from .. import database as db   # all payment and tenant SQL queries


class PaymentView(QWidget):
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self._user = user   # full user dict for role and location checks
        self._loc = user.get("location")   # branch filter for payment queries
        self._selected_id = None   # tracks the currently selected payment row
        self._build()   # constructs the summary strip, toolbar and table
        self._reload()   # loads all payment rows and summary figures

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        section_header(lay, "Payment & Billing",
                       "Manage invoices, payments, and late notices")   # page title and subtitle bar

        # ── Summary strip ──
        self._summary_layout = QHBoxLayout()   # row of summary KPI boxes (Collected, Overdue, Total) rebuilt on every reload
        self._summary_layout.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_md)
        self._summary_widget = QWidget()
        self._summary_widget.setLayout(self._summary_layout)
        lay.addWidget(self._summary_widget)

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(D.pad_lg, D.pad_sm, D.pad_lg, D.pad_sm)

        self._filter_val = "All"   # default filter shows all payment statuses
        self._filter_group = QButtonGroup(self)   # ensures only one radio button is active at a time
        for s in ["All", "Paid", "Overdue", "Pending"]:
            rb = QRadioButton(s)
            rb.setStyleSheet(f"color: {P.text_secondary};")
            if s == "All":
                rb.setChecked(True)   # 'All' is pre-selected when the view opens
            rb.toggled.connect(lambda checked, st=s: self._set_filter(st, checked))   # updates filter on toggle
            self._filter_group.addButton(rb)
            toolbar.addWidget(rb)

        btn_add = styled_button("+ New Invoice", "warning")   # amber button to open the invoice creation dialog
        btn_add.clicked.connect(self._open_add)
        toolbar.addWidget(btn_add)

        btn_paid = styled_button("Mark Paid", "success")   # green button to mark the selected payment as Paid
        btn_paid.clicked.connect(self._mark_paid)
        toolbar.addWidget(btn_paid)

        btn_late = styled_button("Late Notices", "danger")   # red button to open the overdue-payments notice dialog
        btn_late.clicked.connect(self._late_notices)
        toolbar.addWidget(btn_late)

        toolbar.addStretch()   # pushes the count label to the far right
        self._count_lbl = QLabel("")
        self._count_lbl.setFont(qfont(F.small))
        self._count_lbl.setStyleSheet(f"color: {P.text_muted};")
        toolbar.addWidget(self._count_lbl)
        lay.addLayout(toolbar)

        # ── Table ──
        card = Card(title="", accent_color=P.warning)   # amber-accented card for the payments table
        cols = [
            ("#", 40), ("Tenant", 160), ("City", 80), ("Type", 80),
            ("Amount", 90), ("Due Date", 90), ("Paid Date", 90), ("Status", 90),   # 8 columns for payment details
        ]
        self._table, self._model = make_table(card.body_layout(), cols)   # styled read-only table
        self._table.clicked.connect(self._on_select)   # records the clicked row ID
        lay.addWidget(card, 1)   # table card fills remaining vertical space

    def _set_filter(self, status, checked):
        if checked:
            self._filter_val = status   # saves the newly selected filter value
            self._reload()   # refreshes the table to show only the matching status

    def _reload(self):
        # ── Summary ──
        while self._summary_layout.count():
            item = self._summary_layout.takeAt(0)   # removes all existing widgets from the summary strip
            w = item.widget()
            if w:
                w.deleteLater()   # schedules the old widget for memory cleanup

        fin = db.compareCollectedVsPending(self._loc)   # fetches collected vs pending rent totals
        col = fin.get("collected") or 0   # total amount collected
        pen = fin.get("pending") or 0   # total amount still overdue
        tot = col + pen or 1   # combined total (minimum 1 to prevent division-by-zero)

        for label, val, color in [
            ("Collected", f"£{col:,.0f}", P.success),   # green KPI box for collected rent
            ("Overdue",   f"£{pen:,.0f}", P.danger),   # red KPI box for overdue rent
            ("Total Billed", f"£{tot:,.0f}", P.accent),   # indigo KPI box for the total billed
        ]:
            box = QWidget()
            box.setStyleSheet(f"background-color: {P.bg_card}; border-radius: 8px; padding: 8px 14px;")   # rounded card style for each KPI
            bl = QVBoxLayout(box)
            bl.setContentsMargins(8, 6, 8, 6)
            bl.setSpacing(2)
            lbl = QLabel(label)
            lbl.setFont(qfont(F.small))
            lbl.setStyleSheet(f"color: {P.text_secondary};")   # muted label above the amount
            bl.addWidget(lbl)
            vlbl = QLabel(val)
            vlbl.setFont(QFont("Segoe UI", 16, QFont.Bold))   # large 16pt bold for the monetary value
            vlbl.setStyleSheet(f"color: {color};")   # colour matches the box's role (green/red/indigo)
            bl.addWidget(vlbl)
            self._summary_layout.addWidget(box)

        # Collection rate bar
        bar_box = QWidget()
        bbl = QVBoxLayout(bar_box)
        bbl.setContentsMargins(8, 4, 8, 4)
        rlbl = QLabel(f"Collection Rate  {int(col/tot*100)}%")   # shows the percentage collected out of total billed
        rlbl.setFont(qfont(F.small))
        rlbl.setStyleSheet(f"color: {P.text_secondary};")
        bbl.addWidget(rlbl)
        bbl.addWidget(GradientProgressBar(col/tot, P.success, h=8, w=220))   # 8px tall green bar showing the collection fraction
        self._summary_layout.addWidget(bar_box)
        self._summary_layout.addStretch()   # fills remaining space after the bar

        # ── Table ──
        table_clear(self._model)   # clears old payment rows before repopulating
        payments = db.get_all_payments(self._loc)   # fetches all payments for the branch
        filt = self._filter_val   # current status filter
        cnt = 0
        for p in payments:
            if filt != "All" and p["status"] != filt:
                continue   # skips payments not matching the current filter
            color = STATUS_COLORS.get(p["status"], P.text_muted)   # text colour based on payment status
            table_insert(self._model, [
                str(p["id"]),
                p.get("full_name") or "—",   # tenant name, dash if not linked
                p.get("location") or "—",   # city, dash if not recorded
                p.get("type") or "Rent",   # defaults to 'Rent' if no type set
                f"£{p['amount']:,.0f}",   # amount formatted with £ and comma separator
                fmt_date(p["due_date"]),
                fmt_date(p.get("paid_date")),   # dash if payment hasn't been paid yet
                badge_text(p["status"]),   # badge symbol for Paid/Overdue/Pending
            ], color)
            cnt += 1
        self._count_lbl.setText(f"{cnt} record(s)")   # updates the record count label
        self._selected_id = None   # clears selection on reload

    def _on_select(self, index):
        tid = table_selected_id(self._table, self._model, 0)   # reads the payment ID from column 0
        if tid is not None:
            try:
                self._selected_id = int(tid)   # stores it as an integer for action buttons
            except ValueError:
                self._selected_id = None

    def _mark_paid(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a payment row first.")
            return   # blocks action if nothing is selected
        db.markAsPaid(self._selected_id)   # sets the payment status to 'Paid' and records today as the paid date
        self._reload()
        Toast(self.window(), "Payment marked as Paid.")   # brief confirmation toast

    def _open_add(self):
        dlg = _PaymentDialog(self)   # opens the new invoice creation dialog
        if dlg.exec() == QDialog.Accepted:
            self._reload()   # refreshes the table if the invoice was saved

    def _late_notices(self):
        late = db.get_late_payments(self._loc)   # fetches all overdue payments for the branch
        if not late:
            QMessageBox.information(self, "Late Notices", "No overdue payments found.")
            return   # exits early if there are no overdue items to show
        dlg = _LateNoticeDialog(self, late)   # shows the overdue payments list with a 'Generate Notices' button
        if dlg.exec() == QDialog.Accepted:
            self._reload()   # refreshes after notices are generated


# ──────────────────────────────────────────────────────────
# NEW INVOICE DIALOG
# ──────────────────────────────────────────────────────────
class _PaymentDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("New Invoice")
        self.setMinimumSize(480, 480)
        self.resize(480, 520)   # default dialog size for the invoice form
        self._build()   # constructs tenant picker, amount, due date, type and notes fields

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)

        title = QLabel("Create New Invoice")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))   # large bold heading inside the dialog
        title.setStyleSheet(f"color: {P.text_primary};")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)   # allows form widget to resize with the scroll area
        scroll.setFrameShape(QFrame.NoFrame)   # removes the scroll area border
        form = QWidget()
        fl = QVBoxLayout(form)
        fl.setSpacing(4)

        # Tenant
        fl.addWidget(self._lbl("Tenant"))
        tenants = db.get_all_tenants()   # fetches all tenants (no location filter) so any tenant can be billed
        self._tenant_combo = QComboBox()
        self._tenant_combo.addItems(
            [f"{t['id']} — {t['full_name']}" for t in tenants])   # "ID — Full Name" format for each tenant option
        fl.addWidget(self._tenant_combo)

        # Amount
        fl.addWidget(self._lbl("Amount (£)"))
        self._amount = QLineEdit()
        self._amount.setPlaceholderText("1200.00")   # example amount format hint
        self._amount.setFixedHeight(38)
        fl.addWidget(self._amount)

        # Due date
        fl.addWidget(self._lbl("Due Date (YYYY-MM-DD)"))
        self._due = QLineEdit()
        self._due.setPlaceholderText(datetime.date.today().isoformat())   # defaults placeholder to today's date
        self._due.setFixedHeight(38)
        fl.addWidget(self._due)

        # Type
        fl.addWidget(self._lbl("Type"))
        self._type_combo = QComboBox()
        self._type_combo.addItems(
            ["Rent", "Deposit", "Late Fee", "Maintenance", "Other"])   # all valid invoice type options
        fl.addWidget(self._type_combo)

        # Notes
        fl.addWidget(self._lbl("Notes"))
        self._notes = QLineEdit()
        self._notes.setPlaceholderText("Optional notes")
        self._notes.setFixedHeight(38)
        fl.addWidget(self._notes)

        scroll.setWidget(form)   # places the form inside the scrollable viewport
        lay.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        btn_save = styled_button("Create Invoice", "warning")   # amber button to create the invoice
        btn_save.setFixedHeight(42)
        btn_save.setFixedWidth(180)
        btn_save.clicked.connect(self._save)   # wires to the validation and DB creation logic
        btn_row.addWidget(btn_save)
        btn_cancel = styled_button("Cancel", "outline")
        btn_cancel.setFixedHeight(42)
        btn_cancel.setFixedWidth(120)
        btn_cancel.clicked.connect(self.reject)   # closes without saving
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def _lbl(self, text):
        l = QLabel(text)
        l.setFont(qfont(F.label))
        l.setStyleSheet(f"color: {P.text_secondary};")   # secondary grey for form labels
        return l

    def _save(self):
        t_str = self._tenant_combo.currentText()   # reads the selected tenant string "ID — Name"
        if not t_str:
            QMessageBox.critical(self, "Validation", "Select a tenant.")
            return   # blocks save if no tenant is selected
        try:
            tid = int(t_str.split("—")[0].strip())   # extracts the tenant ID from the "ID — Name" format
            amount = float(self._amount.text())   # converts the amount string to a float
        except ValueError:
            QMessageBox.critical(self, "Validation", "Amount must be a number.")
            return
        due = self._due.text().strip() or datetime.date.today().isoformat()   # defaults to today if field is empty
        ptype = self._type_combo.currentText()   # reads the selected payment type
        notes = self._notes.text().strip()

        db.generateInvoice(tid, amount, due, ptype, notes)   # inserts the new invoice as a Pending payment in the DB
        Toast(self.window(), "Invoice created successfully!")   # brief success toast
        self.accept()   # closes and triggers a table reload


# ──────────────────────────────────────────────────────────
# LATE NOTICE DIALOG
# ──────────────────────────────────────────────────────────
class _LateNoticeDialog(QDialog):
    def __init__(self, parent, late: list):
        super().__init__(parent)
        self._late = late   # list of overdue payment dicts passed in from the parent view
        self.setWindowTitle("Late Payment Notifications")
        self.setMinimumSize(620, 480)
        self.resize(620, 480)   # wide enough to show all payment table columns
        self._build()   # constructs the overdue payments table and the 'Generate Notices' button

    def _build(self):
        lay = QVBoxLayout(self)

        title = QLabel(f"Overdue Payments ({len(self._late)})")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))   # bold heading with the count of overdue items
        title.setStyleSheet(f"color: {P.danger};")   # red to emphasise the overdue state
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        cols = [("#", 40), ("Tenant", 140), ("Apt", 70),
                ("Amount", 80), ("Due Date", 90), ("Notified", 60)]   # columns for the overdue payments list
        table, model = make_table(lay, cols)   # read-only table embedded directly in the dialog
        for p in self._late:
            table_insert(model, [
                str(p["id"]),
                p.get("full_name") or "—",   # tenant name, dash if missing
                p.get("apt_number") or "—",   # apartment unit, dash if missing
                f"£{p['amount']:,.0f}",   # overdue amount with £ prefix
                fmt_date(p["due_date"]),
                "Yes" if p.get("late_notified") else "No",   # shows whether a notice was already sent
            ], P.danger)   # all rows in red as they are all overdue

        ids = [p["id"] for p in self._late]   # collects all overdue payment IDs for the bulk notification

        btn_row = QHBoxLayout()
        btn_gen = styled_button(f"Generate Notices ({len(ids)})", "danger")   # red button shows how many notices will be sent
        btn_gen.setFixedHeight(42)
        btn_gen.clicked.connect(lambda: self._generate(ids))   # passes the full list of IDs to the generation function
        btn_row.addWidget(btn_gen)
        btn_close = styled_button("Close", "outline")
        btn_close.setFixedHeight(42)
        btn_close.setFixedWidth(120)
        btn_close.clicked.connect(self.reject)   # closes without generating notices
        btn_row.addWidget(btn_close)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def _generate(self, ids):
        db.mark_late_notifications_sent(ids)   # flags each overdue payment as notified in the database
        Toast(self.window(),
              f"Late notices generated for {len(ids)} payment(s).",
              kind="warning")   # amber warning toast confirms how many notices were sent
        self.accept()   # closes the dialog and triggers a table reload in the parent view
