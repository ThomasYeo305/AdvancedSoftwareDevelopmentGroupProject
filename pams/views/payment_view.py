# ============================================================
# PAMS — views/payment_view.py
# Payment & Billing View (PySide6)
# ============================================================
from __future__ import annotations
import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QRadioButton, QButtonGroup,
    QDialog, QMessageBox, QScrollArea, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..theme import PALETTE as P, FONTS as F, DIMS as D
from ..widgets import (
    qfont, Card, section_header, make_table, table_clear,
    table_insert, table_selected_id, badge_text, styled_button,
    GradientProgressBar, Toast, STATUS_COLORS,
)
from .. import database2 as db


class PaymentView(QWidget):
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

        section_header(lay, "Payment & Billing",
                       "Manage invoices, payments, and late notices")

        # ── Summary strip ──
        self._summary_layout = QHBoxLayout()
        self._summary_layout.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_md)
        self._summary_widget = QWidget()
        self._summary_widget.setLayout(self._summary_layout)
        lay.addWidget(self._summary_widget)

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(D.pad_lg, D.pad_sm, D.pad_lg, D.pad_sm)

        self._filter_val = "All"
        self._filter_group = QButtonGroup(self)
        for s in ["All", "Paid", "Overdue", "Pending"]:
            rb = QRadioButton(s)
            rb.setStyleSheet(f"color: {P.text_secondary};")
            if s == "All":
                rb.setChecked(True)
            rb.toggled.connect(lambda checked, st=s: self._set_filter(st, checked))
            self._filter_group.addButton(rb)
            toolbar.addWidget(rb)

        btn_add = styled_button("+ New Invoice", "warning")
        btn_add.clicked.connect(self._open_add)
        toolbar.addWidget(btn_add)

        btn_paid = styled_button("Mark Paid", "success")
        btn_paid.clicked.connect(self._mark_paid)
        toolbar.addWidget(btn_paid)

        btn_late = styled_button("Late Notices", "danger")
        btn_late.clicked.connect(self._late_notices)
        toolbar.addWidget(btn_late)

        toolbar.addStretch()
        self._count_lbl = QLabel("")
        self._count_lbl.setFont(qfont(F.small))
        self._count_lbl.setStyleSheet(f"color: {P.text_muted};")
        toolbar.addWidget(self._count_lbl)
        lay.addLayout(toolbar)

        # ── Table ──
        card = Card(title="", accent_color=P.warning)
        cols = [
            ("#", 40), ("Tenant", 160), ("City", 80), ("Type", 80),
            ("Amount", 90), ("Due Date", 90), ("Paid Date", 90), ("Status", 90),
        ]
        self._table, self._model = make_table(card.body_layout(), cols)
        self._table.clicked.connect(self._on_select)
        lay.addWidget(card, 1)

    def _set_filter(self, status, checked):
        if checked:
            self._filter_val = status
            self._reload()

    def _reload(self):
        # ── Summary ──
        while self._summary_layout.count():
            item = self._summary_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        fin = db.compareCollectedVsPending(self._loc)
        col = fin.get("collected") or 0
        pen = fin.get("pending") or 0
        tot = col + pen or 1

        for label, val, color in [
            ("Collected", f"£{col:,.0f}", P.success),
            ("Overdue",   f"£{pen:,.0f}", P.danger),
            ("Total Billed", f"£{tot:,.0f}", P.accent),
        ]:
            box = QWidget()
            box.setStyleSheet(f"background-color: {P.bg_card}; border-radius: 8px; padding: 8px 14px;")
            bl = QVBoxLayout(box)
            bl.setContentsMargins(8, 6, 8, 6)
            bl.setSpacing(2)
            lbl = QLabel(label)
            lbl.setFont(qfont(F.small))
            lbl.setStyleSheet(f"color: {P.text_secondary};")
            bl.addWidget(lbl)
            vlbl = QLabel(val)
            vlbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
            vlbl.setStyleSheet(f"color: {color};")
            bl.addWidget(vlbl)
            self._summary_layout.addWidget(box)

        # Collection rate bar
        bar_box = QWidget()
        bbl = QVBoxLayout(bar_box)
        bbl.setContentsMargins(8, 4, 8, 4)
        rlbl = QLabel(f"Collection Rate  {int(col/tot*100)}%")
        rlbl.setFont(qfont(F.small))
        rlbl.setStyleSheet(f"color: {P.text_secondary};")
        bbl.addWidget(rlbl)
        bbl.addWidget(GradientProgressBar(col/tot, P.success, h=8, w=220))
        self._summary_layout.addWidget(bar_box)
        self._summary_layout.addStretch()

        # ── Table ──
        table_clear(self._model)
        payments = db.get_all_payments(self._loc)
        filt = self._filter_val
        cnt = 0
        for p in payments:
            if filt != "All" and p["status"] != filt:
                continue
            color = STATUS_COLORS.get(p["status"], P.text_muted)
            table_insert(self._model, [
                str(p["id"]),
                p.get("full_name") or "—",
                p.get("location") or "—",
                p.get("type") or "Rent",
                f"£{p['amount']:,.0f}",
                p["due_date"],
                p.get("paid_date") or "—",
                badge_text(p["status"]),
            ], color)
            cnt += 1
        self._count_lbl.setText(f"{cnt} record(s)")
        self._selected_id = None

    def _on_select(self, index):
        tid = table_selected_id(self._table, self._model, 0)
        if tid is not None:
            try:
                self._selected_id = int(tid)
            except ValueError:
                self._selected_id = None

    def _mark_paid(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a payment row first.")
            return
        db.markAsPaid(self._selected_id)
        self._reload()
        Toast(self.window(), "Payment marked as Paid.")

    def _open_add(self):
        dlg = _PaymentDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._reload()

    def _late_notices(self):
        late = db.get_late_payments(self._loc)
        if not late:
            QMessageBox.information(self, "Late Notices", "No overdue payments found.")
            return
        dlg = _LateNoticeDialog(self, late)
        if dlg.exec() == QDialog.Accepted:
            self._reload()


# ──────────────────────────────────────────────────────────
# NEW INVOICE DIALOG
# ──────────────────────────────────────────────────────────
class _PaymentDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("New Invoice")
        self.setMinimumSize(480, 480)
        self.resize(480, 520)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)

        title = QLabel("Create New Invoice")
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

        # Tenant
        fl.addWidget(self._lbl("Tenant"))
        tenants = db.get_all_tenants()
        self._tenant_combo = QComboBox()
        self._tenant_combo.addItems(
            [f"{t['id']} — {t['full_name']}" for t in tenants])
        fl.addWidget(self._tenant_combo)

        # Amount
        fl.addWidget(self._lbl("Amount (£)"))
        self._amount = QLineEdit()
        self._amount.setPlaceholderText("1200.00")
        self._amount.setFixedHeight(38)
        fl.addWidget(self._amount)

        # Due date
        fl.addWidget(self._lbl("Due Date (YYYY-MM-DD)"))
        self._due = QLineEdit()
        self._due.setPlaceholderText(datetime.date.today().isoformat())
        self._due.setFixedHeight(38)
        fl.addWidget(self._due)

        # Type
        fl.addWidget(self._lbl("Type"))
        self._type_combo = QComboBox()
        self._type_combo.addItems(
            ["Rent", "Deposit", "Late Fee", "Maintenance", "Other"])
        fl.addWidget(self._type_combo)

        # Notes
        fl.addWidget(self._lbl("Notes"))
        self._notes = QLineEdit()
        self._notes.setPlaceholderText("Optional notes")
        self._notes.setFixedHeight(38)
        fl.addWidget(self._notes)

        scroll.setWidget(form)
        lay.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        btn_save = styled_button("Create Invoice", "warning")
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

    def _save(self):
        t_str = self._tenant_combo.currentText()
        if not t_str:
            QMessageBox.critical(self, "Validation", "Select a tenant.")
            return
        try:
            tid = int(t_str.split("—")[0].strip())
            amount = float(self._amount.text())
        except ValueError:
            QMessageBox.critical(self, "Validation", "Amount must be a number.")
            return
        due = self._due.text().strip() or datetime.date.today().isoformat()
        ptype = self._type_combo.currentText()
        notes = self._notes.text().strip()

        db.generateInvoice(tid, amount, due, ptype, notes)
        Toast(self.window(), "Invoice created successfully!")
        self.accept()


# ──────────────────────────────────────────────────────────
# LATE NOTICE DIALOG
# ──────────────────────────────────────────────────────────
class _LateNoticeDialog(QDialog):
    def __init__(self, parent, late: list):
        super().__init__(parent)
        self._late = late
        self.setWindowTitle("Late Payment Notifications")
        self.setMinimumSize(620, 480)
        self.resize(620, 480)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)

        title = QLabel(f"Overdue Payments ({len(self._late)})")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {P.danger};")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        cols = [("#", 40), ("Tenant", 140), ("Apt", 70),
                ("Amount", 80), ("Due Date", 90), ("Notified", 60)]
        table, model = make_table(lay, cols)
        for p in self._late:
            table_insert(model, [
                str(p["id"]),
                p.get("full_name") or "—",
                p.get("apt_number") or "—",
                f"£{p['amount']:,.0f}",
                p["due_date"],
                "Yes" if p.get("late_notified") else "No",
            ], P.danger)

        ids = [p["id"] for p in self._late]

        btn_row = QHBoxLayout()
        btn_gen = styled_button(f"Generate Notices ({len(ids)})", "danger")
        btn_gen.setFixedHeight(42)
        btn_gen.clicked.connect(lambda: self._generate(ids))
        btn_row.addWidget(btn_gen)
        btn_close = styled_button("Close", "outline")
        btn_close.setFixedHeight(42)
        btn_close.setFixedWidth(120)
        btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_close)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def _generate(self, ids):
        db.mark_late_notifications_sent(ids)
        Toast(self.window(),
              f"Late notices generated for {len(ids)} payment(s).",
              kind="warning")
        self.accept()
