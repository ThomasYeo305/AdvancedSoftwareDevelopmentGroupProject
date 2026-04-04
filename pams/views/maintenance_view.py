# ============================================================
# PAMS — views/maintenance_view.py
# Maintenance Request Management View (PySide6)
# ============================================================
from __future__ import annotations
import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QRadioButton, QButtonGroup,
    QDialog, QMessageBox, QScrollArea, QFrame, QSplitter,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..theme import PALETTE as P, FONTS as F, DIMS as D
from ..widgets import (
    qfont, Card, section_header, make_table, table_clear,
    table_insert, table_selected_id, badge_text, styled_button, Toast,
    PRIORITY_COLORS,
)
from .. import database as db


class MaintenanceView(QWidget):
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self._user = user
        self._loc = user.get("location")
        self._role = user["role"]
        self._selected_id = None
        self._build()
        self._reload()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        section_header(lay, "Maintenance Management",
                       "Log, prioritise, assign and resolve maintenance issues")

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(D.pad_lg, D.pad_sm, D.pad_lg, D.pad_sm)

        # Status filter
        self._filter_val = "All"
        self._filter_group = QButtonGroup(self)
        for s in ["All", "Open", "In Progress", "Resolved"]:
            rb = QRadioButton(s)
            rb.setStyleSheet(f"color: {P.text_secondary};")
            if s == "All":
                rb.setChecked(True)
            rb.toggled.connect(
                lambda checked, st=s: self._set_filter("status", st, checked))
            self._filter_group.addButton(rb)
            toolbar.addWidget(rb)

        # Priority filter
        sep = QLabel("  Priority:")
        sep.setFont(qfont(F.small))
        sep.setStyleSheet(f"color: {P.text_muted};")
        toolbar.addWidget(sep)

        self._pri_val = "All"
        self._pri_group = QButtonGroup(self)
        for p in ["All", "High", "Medium", "Low"]:
            rb = QRadioButton(p)
            rb.setStyleSheet(f"color: {P.text_secondary};")
            if p == "All":
                rb.setChecked(True)
            rb.toggled.connect(
                lambda checked, pr=p: self._set_filter("priority", pr, checked))
            self._pri_group.addButton(rb)
            toolbar.addWidget(rb)

        toolbar.addStretch()

        btn_add = styled_button("+ Log Request", "danger")
        btn_add.clicked.connect(self._open_add)
        toolbar.addWidget(btn_add)

        if self._role in ("Maintenance Staff", "Administrator"):
            btn_resolve = styled_button("Resolve", "success")
            btn_resolve.clicked.connect(self._open_resolve)
            toolbar.addWidget(btn_resolve)

            btn_status = styled_button("Update Status", "primary")
            btn_status.clicked.connect(self._update_status)
            toolbar.addWidget(btn_status)

            btn_sched = styled_button("Schedule & Notify", "warning")
            btn_sched.clicked.connect(self._schedule_notify)
            toolbar.addWidget(btn_sched)

        lay.addLayout(toolbar)

        # ── Body: table + detail panel ──
        body = QHBoxLayout()
        body.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)
        body.setSpacing(D.pad_sm)

        # Table card
        card = Card(title="", accent_color=P.danger)
        cols = [
            ("#", 40), ("Issue", 160), ("Tenant", 120), ("Apt", 70),
            ("City", 80), ("Priority", 80), ("Status", 100),
            ("Assigned To", 130), ("Reported", 90), ("Scheduled", 90),
            ("Resolved", 90), ("Cost £", 70),
        ]
        self._table, self._model = make_table(card.body_layout(), cols)
        self._table.clicked.connect(self._on_select)
        body.addWidget(card, 3)

        # Detail panel
        self._detail_card = Card(title="Request Detail", accent_color=P.danger)
        self._detail_layout = self._detail_card.body_layout()
        body.addWidget(self._detail_card, 1)

        lay.addLayout(body, 1)

    def _set_filter(self, kind, val, checked):
        if not checked:
            return
        if kind == "status":
            self._filter_val = val
        else:
            self._pri_val = val
        self._reload()

    def _reload(self):
        table_clear(self._model)
        items = db.get_all_maintenance(self._loc)
        filt = self._filter_val
        pfilt = self._pri_val
        for m in items:
            if filt != "All" and m["status"] != filt:
                continue
            if pfilt != "All" and m["priority"] != pfilt:
                continue
            pri = m["priority"]
            color = PRIORITY_COLORS.get(pri, P.text_muted)
            table_insert(self._model, [
                str(m["id"]),
                m["title"],
                m.get("full_name") or "—",
                m.get("apt_number") or "—",
                m.get("location") or "—",
                m["priority"],
                badge_text(m["status"]),
                m.get("staff_name") or "Unassigned",
                m["reported_date"],
                m.get("scheduled_date") or "—",
                m.get("resolved_date") or "—",
                f"£{m.get('cost') or 0:,.0f}",
            ], color)
        self._selected_id = None

    def _on_select(self, index):
        tid = table_selected_id(self._table, self._model, 0)
        if tid is None:
            return
        try:
            self._selected_id = int(tid)
        except ValueError:
            return

        # Populate detail panel
        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        items = db.get_all_maintenance()
        m = next((x for x in items if x["id"] == self._selected_id), None)
        if not m:
            return

        pri_color = PRIORITY_COLORS.get(m["priority"], P.accent)
        details = [
            ("Issue",       m["title"],                     P.text_primary),
            ("Priority",    m["priority"],                   pri_color),
            ("Status",      badge_text(m["status"]),         P.text_primary),
            ("Tenant",      m.get("full_name") or "—",      P.text_secondary),
            ("Reported",    m["reported_date"],              P.text_secondary),
            ("Scheduled",   m.get("scheduled_date") or "—", P.info),
            ("Notified",    "Yes" if m.get("communication_sent") else "No", P.info),
            ("Resolved",    m.get("resolved_date") or "—",  P.text_secondary),
            ("Cost (£)",    f"£{m.get('cost') or 0:,.2f}",  P.warning),
            ("Time (hrs)",  str(m.get("time_spent") or 0),  P.text_secondary),
            ("Assigned To", m.get("staff_name") or "—",     P.text_secondary),
        ]
        for label, value, color in details:
            row = QHBoxLayout()
            lbl = QLabel(f"{label}:")
            lbl.setFixedWidth(90)
            lbl.setFont(qfont(F.small_bold))
            lbl.setStyleSheet(f"color: {P.text_muted};")
            row.addWidget(lbl)
            vlbl = QLabel(str(value))
            vlbl.setFont(qfont(F.small))
            vlbl.setStyleSheet(f"color: {color};")
            vlbl.setWordWrap(True)
            row.addWidget(vlbl, 1)
            self._detail_layout.addLayout(row)

        if m.get("description"):
            div = QFrame()
            div.setFrameShape(QFrame.HLine)
            div.setStyleSheet(f"color: {P.divider};")
            self._detail_layout.addWidget(div)
            desc = QLabel(m["description"])
            desc.setFont(qfont(F.small))
            desc.setStyleSheet(f"color: {P.text_secondary};")
            desc.setWordWrap(True)
            self._detail_layout.addWidget(desc)

        self._detail_layout.addStretch()

    def _open_add(self):
        dlg = _MaintDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._reload()

    def _open_resolve(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a request first.")
            return
        dlg = _ResolveDialog(self, mid=self._selected_id)
        if dlg.exec() == QDialog.Accepted:
            self._reload()

    def _update_status(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a request first.")
            return
        dlg = _StatusDialog(self, mid=self._selected_id)
        if dlg.exec() == QDialog.Accepted:
            self._reload()

    def _schedule_notify(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a request first.")
            return
        dlg = _ScheduleDialog(self, mid=self._selected_id)
        if dlg.exec() == QDialog.Accepted:
            self._reload()


# ──────────────────────────────────────────────────────────
# LOG MAINTENANCE DIALOG
# ──────────────────────────────────────────────────────────
class _MaintDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Log Maintenance Request")
        self.setMinimumSize(480, 540)
        self.resize(480, 540)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)

        title = QLabel("Log Maintenance Request")
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

        # Apartment
        fl.addWidget(self._lbl("Apartment"))
        apts = db.get_all_apartments()
        self._apt_combo = QComboBox()
        self._apt_combo.addItems(
            [f"{a['id']} — {a['apt_number']} ({a['location']})" for a in apts])
        fl.addWidget(self._apt_combo)

        # Title
        fl.addWidget(self._lbl("Issue Title"))
        self._title_e = QLineEdit()
        self._title_e.setPlaceholderText("Brief description")
        self._title_e.setFixedHeight(38)
        fl.addWidget(self._title_e)

        # Description
        fl.addWidget(self._lbl("Full Description"))
        self._desc_e = QLineEdit()
        self._desc_e.setPlaceholderText("Detailed description")
        self._desc_e.setFixedHeight(38)
        fl.addWidget(self._desc_e)

        # Priority
        fl.addWidget(self._lbl("Priority"))
        self._pri_combo = QComboBox()
        self._pri_combo.addItems(["High", "Medium", "Low"])
        self._pri_combo.setCurrentIndex(1)
        fl.addWidget(self._pri_combo)

        # Assign To
        fl.addWidget(self._lbl("Assign To"))
        staff = db.get_maintenance_staff()
        self._staff_combo = QComboBox()
        self._staff_combo.addItems(
            [f"{s[0]} — {s[1]}" for s in staff])
        fl.addWidget(self._staff_combo)

        # Scheduled Date
        fl.addWidget(self._lbl("Scheduled Date"))
        self._sched_e = QLineEdit()
        self._sched_e.setPlaceholderText("YYYY-MM-DD (optional)")
        self._sched_e.setFixedHeight(38)
        fl.addWidget(self._sched_e)

        scroll.setWidget(form)
        lay.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        btn_save = styled_button("Log Request", "danger")
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
        a_str = self._apt_combo.currentText()
        title = self._title_e.text().strip()
        desc = self._desc_e.text().strip()
        pri = self._pri_combo.currentText()

        if not title:
            QMessageBox.critical(self, "Validation", "Issue title is required.")
            return
        try:
            tid = int(t_str.split("—")[0].strip()) if t_str else None
            aid = int(a_str.split("—")[0].strip()) if a_str else None
        except ValueError:
            tid = aid = None

        s_str = self._staff_combo.currentText()
        try:
            assigned = int(s_str.split("—")[0].strip()) if s_str else None
        except ValueError:
            assigned = None
        sched = self._sched_e.text().strip() or None
        db.add_maintenance(tid, aid, title, desc, pri, assigned, sched)
        Toast(self.window(), "Maintenance request logged.")
        self.accept()


# ──────────────────────────────────────────────────────────
# RESOLVE DIALOG
# ──────────────────────────────────────────────────────────
class _ResolveDialog(QDialog):
    def __init__(self, parent, mid: int):
        super().__init__(parent)
        self._mid = mid
        self.setWindowTitle("Resolve Request")
        self.setMinimumSize(400, 320)
        self.resize(400, 340)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)

        title = QLabel("Resolve Maintenance Request")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {P.text_primary};")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        for label, attr, ph in [
            ("Cost Incurred (£)", "_cost", "0.00"),
            ("Time Spent (hours)", "_time", "0.0"),
            ("Resolution Notes", "_notes", "What was done to fix the issue"),
        ]:
            lbl = QLabel(label)
            lbl.setFont(qfont(F.label))
            lbl.setStyleSheet(f"color: {P.text_secondary};")
            lay.addWidget(lbl)
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setFixedHeight(38)
            lay.addWidget(e)
            setattr(self, attr, e)

        btn_row = QHBoxLayout()
        btn_save = styled_button("Mark Resolved", "success")
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

    def _save(self):
        try:
            cost = float(self._cost.text() or 0)
            time = float(self._time.text() or 0)
        except ValueError:
            QMessageBox.critical(self, "Validation",
                                 "Cost and Time must be numbers.")
            return
        notes = self._notes.text().strip()
        db.resolveIssue(self._mid, cost, time, notes)
        Toast(self.window(), "Request resolved successfully!", kind="success")
        self.accept()


# ──────────────────────────────────────────────────────────
# UPDATE STATUS DIALOG
# ──────────────────────────────────────────────────────────
class _StatusDialog(QDialog):
    def __init__(self, parent, mid: int):
        super().__init__(parent)
        self._mid = mid
        self.setWindowTitle("Update Status")
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
        db.update_maintenance_status(self._mid, self._combo.currentText())
        Toast(self.window(),
              f"Status updated to '{self._combo.currentText()}'")
        self.accept()


# ──────────────────────────────────────────────────────────
# SCHEDULE & NOTIFY DIALOG
# ──────────────────────────────────────────────────────────
class _ScheduleDialog(QDialog):
    def __init__(self, parent, mid: int):
        super().__init__(parent)
        self._mid = mid
        self.setWindowTitle("Schedule & Notify Tenant")
        self.setMinimumSize(420, 300)
        self.resize(420, 320)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)

        title = QLabel("Schedule Maintenance")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet(f"color: {P.text_primary};")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        lbl1 = QLabel("Scheduled Date (YYYY-MM-DD)")
        lbl1.setFont(qfont(F.label))
        lbl1.setStyleSheet(f"color: {P.text_secondary};")
        lay.addWidget(lbl1)
        self._sched = QLineEdit()
        self._sched.setPlaceholderText("YYYY-MM-DD")
        self._sched.setFixedHeight(38)
        lay.addWidget(self._sched)

        lbl2 = QLabel("Notes / Communication")
        lbl2.setFont(qfont(F.label))
        lbl2.setStyleSheet(f"color: {P.text_secondary};")
        lay.addWidget(lbl2)
        self._notes = QLineEdit()
        self._notes.setPlaceholderText("Details to communicate to tenant")
        self._notes.setFixedHeight(38)
        lay.addWidget(self._notes)

        btn_row = QHBoxLayout()
        btn_apply = styled_button("Schedule & Notify", "primary")
        btn_apply.setFixedHeight(42)
        btn_apply.setFixedWidth(200)
        btn_apply.clicked.connect(self._apply)
        btn_row.addWidget(btn_apply)
        btn_cancel = styled_button("Cancel", "outline")
        btn_cancel.setFixedHeight(42)
        btn_cancel.setFixedWidth(120)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def _apply(self):
        sd = self._sched.text().strip()
        if not sd:
            QMessageBox.critical(self, "Validation",
                                 "Scheduled date is required.")
            return
        notes = self._notes.text().strip()
        db.update_maintenance_schedule(self._mid, sd, notes)
        Toast(self.window(), "Scheduled and tenant notified", kind="success")
        self.accept()
