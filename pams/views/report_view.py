# ============================================================
# PAMS — views/report_view.py
# Reporting & Analytics View (PySide6)
# ============================================================
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QFrame, QGridLayout, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..theme import PALETTE as P, FONTS as F, DIMS as D
from ..widgets import (
    qfont, Card, StatCard, section_header, make_table, table_clear,
    table_insert, badge_text, StatusRing, GradientProgressBar, styled_button,
    STATUS_COLORS,
)
from .. import database as db

CITY_COLORS = {
    "Bristol":    P.accent,
    "London":     P.accent2,
    "Manchester": P.success,
    "Cardiff":    P.warning,
}


class ReportView(QWidget):
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self._user = user
        self._loc = user.get("location")
        self._current_tab = "occupancy"
        self._build()
        self._switch_tab("occupancy")

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        section_header(lay, "Reports & Analytics",
                       "Occupancy, financial and maintenance summaries")

        # ── Tab bar ──
        tab_bar = QHBoxLayout()
        tab_bar.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_md)
        self._tab_btns: dict[str, QPushButton] = {}

        for key, label in [
            ("occupancy",   "Occupancy"),
            ("financial",   "Financial Summary"),
            ("maintenance", "Maintenance Costs"),
            ("leases",      "Lease Tracking"),
        ]:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFont(qfont(F.body_bold))
            btn.setFlat(True)
            btn.clicked.connect(lambda _=False, k=key: self._switch_tab(k))
            tab_bar.addWidget(btn)
            self._tab_btns[key] = btn

        tab_bar.addStretch()
        lay.addLayout(tab_bar)

        # ── Content area ──
        self._content = QWidget()
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)
        self._content_lay.setSpacing(D.pad_sm)
        lay.addWidget(self._content, 1)

    def _switch_tab(self, key: str):
        self._current_tab = key
        # Style active tab
        for k, btn in self._tab_btns.items():
            if k == key:
                btn.setStyleSheet(
                    f"color: {P.accent}; border-bottom: 2px solid {P.accent}; "
                    f"padding: 4px 12px; background: transparent;")
            else:
                btn.setStyleSheet(
                    f"color: {P.text_muted}; padding: 4px 12px; "
                    f"background: transparent;")

        # Clear content
        while self._content_lay.count():
            item = self._content_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        builders = {
            "occupancy":   self._build_occupancy,
            "financial":   self._build_financial,
            "maintenance": self._build_maintenance,
            "leases":      self._build_leases,
        }
        builders[key]()

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                ReportView._clear_layout(item.layout())

    # ──────────────────────────────────────────────────────
    # OCCUPANCY REPORT
    # ──────────────────────────────────────────────────────
    def _build_occupancy(self):
        lay = self._content_lay

        body = QHBoxLayout()
        body.setSpacing(D.pad_sm)

        # LEFT — ring cards + bar breakdown
        left_card = Card(title="City Occupancy Rings", accent_color=P.accent)
        left_body = left_card.body_layout()

        occ_data = db.getOccupancyByCity()

        # Rings row
        ring_row = QHBoxLayout()
        ring_row.setSpacing(D.pad_md)
        for row in occ_data:
            loc = row["location"]
            tot = max(row["total"], 1)
            occ = row["occupied"]
            pct = occ / tot
            color = CITY_COLORS.get(loc, P.info)

            col = QVBoxLayout()
            col.setAlignment(Qt.AlignCenter)
            ring = StatusRing(size=110, thickness=10, color=color, value=pct)
            col.addWidget(ring, alignment=Qt.AlignCenter)

            nlbl = QLabel(loc)
            nlbl.setFont(qfont(F.small_bold))
            nlbl.setStyleSheet(f"color: {color};")
            nlbl.setAlignment(Qt.AlignCenter)
            col.addWidget(nlbl)

            clbl = QLabel(f"{occ}/{tot} occupied")
            clbl.setFont(qfont(F.small))
            clbl.setStyleSheet(f"color: {P.text_secondary};")
            clbl.setAlignment(Qt.AlignCenter)
            col.addWidget(clbl)
            ring_row.addLayout(col)

        left_body.addLayout(ring_row)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"color: {P.divider};")
        left_body.addWidget(div)

        bar_title = QLabel("Occupancy Breakdown by City")
        bar_title.setFont(qfont(F.h4))
        bar_title.setStyleSheet(f"color: {P.text_primary};")
        left_body.addWidget(bar_title)

        for row in occ_data:
            loc = row["location"]
            tot = max(row["total"], 1)
            occ = row["occupied"]
            vac = tot - occ
            pct = occ / tot
            color = CITY_COLORS.get(loc, P.info)

            br = QHBoxLayout()
            nlbl = QLabel(loc)
            nlbl.setFixedWidth(100)
            nlbl.setFont(qfont(F.small_bold))
            nlbl.setStyleSheet(f"color: {P.text_primary};")
            br.addWidget(nlbl)

            pb = GradientProgressBar(value=pct, color=color,
                                      width=260, height=12)
            br.addWidget(pb)

            info = QLabel(f"  {int(pct*100)}%  Occ:{occ}  Vac:{vac}")
            info.setFont(qfont(F.small))
            info.setStyleSheet(f"color: {P.text_secondary};")
            br.addWidget(info)
            br.addStretch()
            left_body.addLayout(br)

        left_body.addStretch()
        body.addWidget(left_card, 3)

        # RIGHT — apartment table
        right_card = Card(title="All Apartments", accent_color=P.info)
        cols = [
            ("Apt #", 70), ("City", 80), ("Type", 90),
            ("Status", 70), ("Rent £", 70),
        ]
        tbl, mdl = make_table(right_card.body_layout(), cols)
        for a in db.get_all_apartments(self._loc):
            color = STATUS_COLORS.get(a["status"], P.text_muted)
            table_insert(mdl, [
                a["apt_number"], a["location"], a["type"],
                badge_text(a["status"]),
                f"£{a['monthly_rent']:,.0f}",
            ], color)
        body.addWidget(right_card, 2)

        lay.addLayout(body, 1)

    # ──────────────────────────────────────────────────────
    # FINANCIAL REPORT
    # ──────────────────────────────────────────────────────
    def _build_financial(self):
        lay = self._content_lay

        occ_data = db.getOccupancyByCity()
        fin_all = db.compareCollectedVsPending()

        col_all = fin_all.get("collected") or 0
        pen_all = fin_all.get("pending") or 0
        total = col_all + pen_all or 1

        # Summary strip
        strip = QHBoxLayout()
        strip.setSpacing(D.pad_sm)
        for icon, title, val, color in [
            ("💰", "All-City Collected", f"£{col_all:,.0f}", P.success),
            ("⚠️", "All-City Overdue",   f"£{pen_all:,.0f}", P.danger),
            ("📈", "Collection Rate",    f"{int(col_all/total*100)}%", P.accent),
        ]:
            sc = StatCard(icon=icon, value=val, label=title, color=color)
            strip.addWidget(sc)
        lay.addLayout(strip)

        # Per-city table
        loc_card = Card(title="Per-City Financial Summary", accent_color=P.success)
        cols = [
            ("City", 100), ("Total Units", 90), ("Occupied", 80),
            ("Occ. Rate", 80),
        ]
        tbl, mdl = make_table(loc_card.body_layout(), cols)
        for row in occ_data:
            tot = max(row["total"], 1)
            occ = row["occupied"]
            table_insert(mdl, [
                row["location"], str(tot), str(occ),
                f"{int(occ/tot*100)}%",
            ])
        lay.addWidget(loc_card)

        # Payment table
        pay_card = Card(title="Recent Payments", accent_color=P.warning)
        cols2 = [
            ("Tenant", 150), ("Amount", 80), ("Due", 90),
            ("Type", 70), ("Status", 70),
        ]
        tbl2, mdl2 = make_table(pay_card.body_layout(), cols2)
        for p in db.get_all_payments(self._loc)[:30]:
            color = STATUS_COLORS.get(p["status"], P.text_muted)
            table_insert(mdl2, [
                p.get("full_name") or "—",
                f"£{p['amount']:,.0f}",
                p["due_date"],
                p.get("type") or "Rent",
                badge_text(p["status"]),
            ], color)
        lay.addWidget(pay_card, 1)

    # ──────────────────────────────────────────────────────
    # MAINTENANCE COST REPORT
    # ──────────────────────────────────────────────────────
    def _build_maintenance(self):
        lay = self._content_lay

        summary = db.trackCostsByLocation(self._loc)
        total_cost = sum(r.get("total_cost") or 0 for r in summary)

        color_map = {
            "Open": P.warning,
            "In Progress": P.info,
            "Resolved": P.success,
        }

        strip = QHBoxLayout()
        strip.setSpacing(D.pad_sm)
        status_icons = {"Open": "⭕", "In Progress": "⏳", "Resolved": "✅"}
        for row in summary:
            status = row.get("status", "—")
            cost = row.get("total_cost") or 0
            count = row.get("count") or 0
            color = color_map.get(status, P.accent)
            sc = StatCard(icon=status_icons.get(status, "🛠️"),
                          value=f"£{cost:,.0f}",
                          label=f"{status} — {count} request(s)",
                          color=color)
            strip.addWidget(sc)
        lay.addLayout(strip)

        # Total
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"color: {P.divider};")
        lay.addWidget(div)

        total_lbl = QLabel(f"Total Maintenance Spend:  £{total_cost:,.2f}")
        total_lbl.setFont(qfont(F.h3))
        total_lbl.setStyleSheet(f"color: {P.warning};")
        lay.addWidget(total_lbl)

        # Detailed table
        mc = Card(title="Maintenance Request Costs", accent_color=P.danger)
        cols = [
            ("Issue", 160), ("Priority", 70), ("Status", 80),
            ("Cost £", 70), ("Hours", 60), ("Resolved", 90),
        ]
        tbl, mdl = make_table(mc.body_layout(), cols)
        for m in db.get_all_maintenance(self._loc):
            table_insert(mdl, [
                m["title"],
                m["priority"],
                badge_text(m["status"]),
                f"£{m.get('cost') or 0:,.0f}",
                str(m.get("time_spent") or 0),
                m.get("resolved_date") or "—",
            ])
        lay.addWidget(mc, 1)

    # ──────────────────────────────────────────────────────
    # LEASE TRACKING REPORT
    # ──────────────────────────────────────────────────────
    def _build_leases(self):
        lay = self._content_lay

        # Day filter
        filter_row = QHBoxLayout()
        self._lease_days = 30
        self._lease_group = QButtonGroup(self)
        for d in [30, 60, 90]:
            rb = QRadioButton(f"Within {d} days")
            rb.setStyleSheet(f"color: {P.text_secondary};")
            if d == 30:
                rb.setChecked(True)
            rb.toggled.connect(
                lambda checked, dd=d: self._set_lease_days(dd, checked))
            self._lease_group.addButton(rb)
            filter_row.addWidget(rb)
        filter_row.addStretch()
        lay.addLayout(filter_row)

        self._lease_summary_lbl = QLabel("")
        self._lease_summary_lbl.setFont(qfont(F.h4))
        self._lease_summary_lbl.setStyleSheet(f"color: {P.warning};")
        lay.addWidget(self._lease_summary_lbl)

        card = Card(title="Expiring Leases", accent_color=P.warning)
        cols = [
            ("Tenant", 150), ("NI Number", 100), ("Apartment", 80),
            ("City", 80), ("Lease End", 90), ("Status", 70),
        ]
        self._lease_tbl, self._lease_mdl = make_table(
            card.body_layout(), cols)
        lay.addWidget(card, 1)

        self._reload_leases()

    def _set_lease_days(self, days, checked):
        if checked:
            self._lease_days = days
            self._reload_leases()

    def _reload_leases(self):
        days = self._lease_days
        leases = db.get_expiring_leases(days, self._loc)
        table_clear(self._lease_mdl)
        for t in leases:
            table_insert(self._lease_mdl, [
                t["full_name"],
                t["ni_number"],
                t.get("apt_number") or "—",
                t.get("location") or "—",
                t.get("lease_end") or "—",
                badge_text(t["status"]),
            ], P.warning)
        self._lease_summary_lbl.setText(
            f"{len(leases)} lease(s) expiring within {days} days")
