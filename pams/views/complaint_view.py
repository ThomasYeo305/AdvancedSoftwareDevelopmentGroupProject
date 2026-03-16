# ============================================================
# PAMS — views/complaint_view.py
# Complaints Management CRUD View (PySide6)
# ============================================================
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QRadioButton, QButtonGroup,
    QDialog, QMessageBox, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..theme import PALETTE as P, FONTS as F, DIMS as D
from ..widgets import (
    qfont, Card, section_header, make_table, table_clear,
    table_insert, table_selected_id, badge_text, styled_button, Toast,
    STATUS_COLORS,
)
from .. import database as db


class ComplaintView(QWidget):
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

        section_header(lay, "Complaints Management",
                       "Register, track and resolve tenant complaints")

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(D.pad_lg, D.pad_sm, D.pad_lg, D.pad_sm)

        self._filter_val = "All"
        self._filter_group = QButtonGroup(self)
        for s in ["All", "Open", "In Progress", "Resolved"]:
            rb = QRadioButton(s)
            rb.setStyleSheet(f"color: {P.text_secondary};")
            if s == "All":
                rb.setChecked(True)
            rb.toggled.connect(
                lambda checked, st=s: self._set_filter(st, checked))
            self._filter_group.addButton(rb)
            toolbar.addWidget(rb)

        btn_add = styled_button("+ Log Complaint", "warning")
        btn_add.clicked.connect(self._open_add)
        toolbar.addWidget(btn_add)

        if self._user["role"] in ("Administrator", "Front-Desk Staff"):
            btn_status = styled_button("Update Status", "primary")
            btn_status.clicked.connect(self._update_status)
            toolbar.addWidget(btn_status)

            btn_resolve = styled_button("Resolve", "success")
            btn_resolve.clicked.connect(self._resolve)
            toolbar.addWidget(btn_resolve)

        toolbar.addStretch()
        self._count_lbl = QLabel("")
        self._count_lbl.setFont(qfont(F.small))
        self._count_lbl.setStyleSheet(f"color: {P.text_muted};")
        toolbar.addWidget(self._count_lbl)
        lay.addLayout(toolbar)

        # ── Body: table + detail ──
        body = QHBoxLayout()
        body.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)
        body.setSpacing(D.pad_sm)

        # Table
        card = Card(title="", accent_color=P.warning)
        cols = [
            ("#", 40), ("Subject", 180), ("Tenant", 140), ("Apartment", 90),
            ("City", 80), ("Status", 90), ("Reported", 100), ("Resolved", 100),
        ]
        self._table, self._model = make_table(card.body_layout(), cols)
        self._table.clicked.connect(self._on_select)
        body.addWidget(card, 3)

        # Detail panel
        self._detail_card = Card(title="Complaint Detail", accent_color=P.warning)
        self._detail_layout = self._detail_card.body_layout()
        body.addWidget(self._detail_card, 1)

        lay.addLayout(body, 1)

    def _set_filter(self, status, checked):
        if checked:
            self._filter_val = status
            self._reload()

    def _reload(self):
        table_clear(self._model)
        items = db.get_all_complaints(self._loc)
        filt = self._filter_val
        cnt = 0
        for c in items:
            if filt != "All" and c["status"] != filt:
                continue
            color = STATUS_COLORS.get(c["status"], P.text_muted)
            table_insert(self._model, [
                str(c["id"]),
                c["title"],
                c.get("full_name") or "—",
                c.get("apt_number") or "—",
                c.get("location") or "—",
                badge_text(c["status"]),
                (c.get("created_at") or "")[:10],
                c.get("resolved_at") or "—",
            ], color)
            cnt += 1
        self._count_lbl.setText(f"{cnt} complaint(s)")
        self._selected_id = None

    def _on_select(self, index):
        tid = table_selected_id(self._table, self._model, 0)
        if tid is None:
            return
        try:
            self._selected_id = int(tid)
        except ValueError:
            return

        # Populate detail
        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        items = db.get_all_complaints()
        c = next((x for x in items if x["id"] == self._selected_id), None)
        if not c:
            return

        details = [
            ("Subject",   c["title"],                    P.text_primary),
            ("Tenant",    c.get("full_name") or "—",     P.text_secondary),
            ("Apartment", c.get("apt_number") or "—",    P.text_secondary),
            ("City",      c.get("location") or "—",      P.text_secondary),
            ("Status",    badge_text(c["status"]),        P.text_primary),
            ("Reported",  (c.get("created_at") or "")[:10], P.text_secondary),
            ("Resolved",  c.get("resolved_at") or "—",   P.text_secondary),
        ]
        for label, value, color in details:
            row = QHBoxLayout()
            lbl = QLabel(f"{label}:")
            lbl.setFixedWidth(80)
            lbl.setFont(qfont(F.small_bold))
            lbl.setStyleSheet(f"color: {P.text_muted};")
            row.addWidget(lbl)
            vlbl = QLabel(str(value))
            vlbl.setFont(qfont(F.small))
            vlbl.setStyleSheet(f"color: {color};")
            vlbl.setWordWrap(True)
            row.addWidget(vlbl, 1)
            self._detail_layout.addLayout(row)

        if c.get("description"):
            div = QFrame()
            div.setFrameShape(QFrame.HLine)
            div.setStyleSheet(f"color: {P.divider};")
            self._detail_layout.addWidget(div)
            dlbl = QLabel("Description:")
            dlbl.setFont(qfont(F.small_bold))
            dlbl.setStyleSheet(f"color: {P.text_muted};")
            self._detail_layout.addWidget(dlbl)
            desc = QLabel(c["description"])
            desc.setFont(qfont(F.small))
            desc.setStyleSheet(f"color: {P.text_secondary};")
            desc.setWordWrap(True)
            self._detail_layout.addWidget(desc)

        self._detail_layout.addStretch()

    def _open_add(self):
        dlg = _ComplaintDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._reload()

    def _update_status(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a complaint first.")
            return
        dlg = _StatusDialog(self, cid=self._selected_id)
        if dlg.exec() == QDialog.Accepted:
            self._reload()

    def _resolve(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a complaint first.")
            return
        ans = QMessageBox.question(self, "Confirm",
                                   "Mark this complaint as Resolved?")
        if ans == QMessageBox.Yes:
            db.updateStatus(self._selected_id, "Resolved")
            self._reload()
            Toast(self.window(), "Complaint resolved.", kind="success")


# ──────────────────────────────────────────────────────────
# ADD COMPLAINT DIALOG
# ──────────────────────────────────────────────────────────
class _ComplaintDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Log Complaint")
        self.setMinimumSize(480, 380)
        self.resize(480, 420)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)

        title = QLabel("Log Tenant Complaint")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"color: {P.text_primary};")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        # Tenant
        lay.addWidget(self._lbl("Tenant"))
        tenants = db.get_all_tenants()
        self._tenant_combo = QComboBox()
        self._tenant_combo.addItems(
            [f"{t['id']} — {t['full_name']}" for t in tenants])
        lay.addWidget(self._tenant_combo)

        # Subject
        lay.addWidget(self._lbl("Subject"))
        self._title_e = QLineEdit()
        self._title_e.setPlaceholderText("Brief subject")
        self._title_e.setFixedHeight(38)
        lay.addWidget(self._title_e)

        # Description
        lay.addWidget(self._lbl("Full Description"))
        self._desc_e = QLineEdit()
        self._desc_e.setPlaceholderText("Detailed description of complaint")
        self._desc_e.setFixedHeight(38)
        lay.addWidget(self._desc_e)

        lay.addStretch()

        btn_row = QHBoxLayout()
        btn_save = styled_button("Submit Complaint", "warning")
        btn_save.setFixedHeight(42)
        btn_save.setFixedWidth(200)
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
        title = self._title_e.text().strip()
        desc = self._desc_e.text().strip()

        if not title:
            QMessageBox.critical(self, "Validation", "Subject is required.")
            return
        try:
            tid = int(t_str.split("—")[0].strip()) if t_str else None
        except ValueError:
            tid = None
        if not tid:
            QMessageBox.critical(self, "Validation", "Please select a tenant.")
            return

        db.add_complaint(tid, title, desc)
        Toast(self.window(), "Complaint logged successfully.")
        self.accept()


# ──────────────────────────────────────────────────────────
# UPDATE STATUS DIALOG
# ──────────────────────────────────────────────────────────
class _StatusDialog(QDialog):
    def __init__(self, parent, cid: int):
        super().__init__(parent)
        self._cid = cid
        self.setWindowTitle("Update Complaint Status")
        self.setFixedSize(360, 200)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lbl = QLabel("New Status")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        lbl.setStyleSheet(f"color: {P.text_primary};")
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl)

        self._combo = QComboBox()
        self._combo.addItems(["Open", "In Progress", "Resolved"])
        self._combo.setCurrentIndex(1)
        lay.addWidget(self._combo)

        btn = styled_button("Apply", "primary")
        btn.setFixedHeight(38)
        btn.clicked.connect(self._apply)
        lay.addWidget(btn)

    def _apply(self):
        db.updateStatus(self._cid, self._combo.currentText())
        Toast(self.window(),
              f"Status updated to '{self._combo.currentText()}'")
        self.accept()
