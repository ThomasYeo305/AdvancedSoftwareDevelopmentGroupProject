# ============================================================
# PAMS — views/dashboard_view.py
# Role-aware dashboard with KPIs, city rings, quick forms (PySide6)
# ============================================================
from __future__ import annotations
import datetime, random

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QLineEdit, QComboBox, QPushButton,
    QSizePolicy, QScrollArea,
)
from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QPen,
)

from ..theme import PALETTE as P, FONTS as F, DIMS as D, ROLE_COLORS, lerp_color
from ..widgets import (
    qfont, Card, StatCard, StatusRing, GradientProgressBar,
    section_header, make_table, table_insert, badge_text,
    styled_button, _blend, Toast,
    STATUS_COLORS, PRIORITY_COLORS,
)
from .. import database as db


class DashboardView(QWidget):
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self._user = user
        self._role = user["role"]
        self._loc = user.get("location")
        self._stats = db.dashboard_stats(user)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        role = self._role
        if role == "Manager":
            self._build_manager(lay)
        elif role == "Front-Desk Staff":
            self._build_frontdesk(lay)
        elif role == "Finance Manager":
            self._build_finance(lay)
        elif role == "Maintenance Staff":
            self._build_maintenance(lay)
        else:
            self._build_admin(lay)

    # ──────────────────────────────────────────────────────
    # WELCOME BANNER
    # ──────────────────────────────────────────────────────
    def _welcome_banner(self, parent_layout, color=None):
        color = color or ROLE_COLORS.get(self._role, P.accent)
        banner = _BannerWidget(self._user, self._role, self._loc, color)
        banner.setFixedHeight(120)
        parent_layout.addWidget(banner)

    # ──────────────────────────────────────────────────────
    # KPI ROW
    # ──────────────────────────────────────────────────────
    def _kpi_row(self, parent_layout):
        s = self._stats
        occ = s["occupied_apts"]
        tot = s["total_apts"] or 1

        kpis = [
            ("🏢", f"{occ}/{tot}", "Apartments Occupied", P.accent),
            ("👥", str(s["total_tenants"]),  "Active Tenants",      P.success),
            ("🛠️", str(s["active_maint"]),   "Open Maintenance",    P.warning),
            ("⚠️", f"£{s['pending_rent']:,.0f}", "Overdue Rent",    P.danger),
            ("💰", f"£{s['collected_rent']:,.0f}", "Rent Collected", P.info),
        ]
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(D.pad_lg, D.pad_sm, D.pad_lg, D.pad_md)
        rl.setSpacing(14)
        for icon, val, lbl, col in kpis:
            sc = StatCard(icon=icon, value=val, label=lbl, color=col)
            rl.addWidget(sc, 1)
        parent_layout.addWidget(row)

    # ──────────────────────────────────────────────────────
    # ADMIN
    # ──────────────────────────────────────────────────────
    def _build_admin(self, lay):
        section_header(lay, "Administrator Dashboard",
                       f"Location: {self._loc}  •  {datetime.date.today():%d %b %Y}",
                       accent=ROLE_COLORS["Administrator"])
        self._welcome_banner(lay, ROLE_COLORS["Administrator"])
        self._kpi_row(lay)

        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)
        bl.setSpacing(10)

        bl.addWidget(self._tenants_card(), 3)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(D.pad_sm)
        rl.addWidget(self._city_performance_widget())
        rl.addWidget(self._financial_snapshot_widget())
        bl.addWidget(right, 2)

        lay.addWidget(body, 1)

    # ──────────────────────────────────────────────────────
    # MANAGER
    # ──────────────────────────────────────────────────────
    def _build_manager(self, lay):
        section_header(lay, "Manager Dashboard",
                       "All-city occupancy & performance overview",
                       accent=ROLE_COLORS["Manager"])
        self._welcome_banner(lay, ROLE_COLORS["Manager"])
        self._kpi_row(lay)

        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)
        bl.setSpacing(10)
        bl.addWidget(self._city_performance_widget(), 5)
        bl.addWidget(self._financial_snapshot_widget(), 4)
        lay.addWidget(body, 1)

    # ──────────────────────────────────────────────────────
    # FRONT DESK
    # ──────────────────────────────────────────────────────
    def _build_frontdesk(self, lay):
        section_header(lay, "Front-Desk Dashboard",
                       "Register tenants & manage inquiries quickly",
                       accent=ROLE_COLORS["Front-Desk Staff"])
        self._welcome_banner(lay, ROLE_COLORS["Front-Desk Staff"])
        self._kpi_row(lay)

        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)
        bl.setSpacing(10)
        bl.addWidget(self._quick_tenant_form(), 2)
        bl.addWidget(self._tenants_card(), 3)
        lay.addWidget(body, 1)

    # ──────────────────────────────────────────────────────
    # FINANCE
    # ──────────────────────────────────────────────────────
    def _build_finance(self, lay):
        section_header(lay, "Finance Dashboard",
                       "Payment overview & billing summary",
                       accent=ROLE_COLORS["Finance Manager"])
        self._welcome_banner(lay, ROLE_COLORS["Finance Manager"])
        self._kpi_row(lay)

        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)
        bl.setSpacing(10)
        bl.addWidget(self._recent_payments_widget(), 3)
        bl.addWidget(self._financial_snapshot_widget(), 2)
        lay.addWidget(body, 1)

    # ──────────────────────────────────────────────────────
    # MAINTENANCE
    # ──────────────────────────────────────────────────────
    def _build_maintenance(self, lay):
        section_header(lay, "Maintenance Dashboard",
                       "Active requests & workload overview",
                       accent=ROLE_COLORS["Maintenance Staff"])
        self._welcome_banner(lay, ROLE_COLORS["Maintenance Staff"])
        self._kpi_row(lay)

        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)
        bl.setSpacing(10)
        bl.addWidget(self._maintenance_card(), 1)
        lay.addWidget(body, 1)

    # ──────────────────────────────────────────────────────
    # WIDGET BUILDERS
    # ──────────────────────────────────────────────────────
    def _tenants_card(self) -> Card:
        card = Card(title="Recent Tenants", accent_color=P.accent)
        cols = [("Tenant", 160), ("Apartment", 90), ("Lease End", 90), ("Status", 80)]
        table, model = make_table(card.body_layout(), cols)
        tenants = db.get_all_tenants(self._loc)[:12]
        for t in tenants:
            color = STATUS_COLORS.get(t["status"], P.text_muted)
            table_insert(model, [
                t["full_name"],
                t.get("apt_number") or "—",
                t.get("lease_end") or "—",
                badge_text(t["status"]),
            ], color)
        return card

    def _city_performance_widget(self) -> Card:
        card = Card(title="City Performance", accent_color=P.info)
        inner = card.body_layout()
        occ_data = db.getOccupancyByCity()

        if not occ_data:
            lbl = QLabel("No data available.")
            lbl.setFont(qfont(F.body))
            lbl.setStyleSheet(f"color: {P.text_muted};")
            inner.addWidget(lbl)
            return card

        city_colors = {
            "Bristol": P.accent, "London": P.accent2,
            "Manchester": P.success, "Cardiff": P.warning,
        }

        ring_row = QHBoxLayout()
        for row in occ_data:
            loc = row["location"]
            tot = row["total"] or 1
            occ = row["occupied"]
            pct = occ / tot
            color = city_colors.get(loc, P.info)

            col_w = QWidget()
            cl = QVBoxLayout(col_w)
            cl.setAlignment(Qt.AlignCenter)
            cl.setSpacing(2)

            ring = StatusRing(110, 12, color, pct)
            cl.addWidget(ring, 0, Qt.AlignCenter)

            nm = QLabel(loc)
            nm.setFont(qfont(F.small_bold))
            nm.setStyleSheet(f"color: {color};")
            nm.setAlignment(Qt.AlignCenter)
            cl.addWidget(nm)

            un = QLabel(f"{occ}/{tot} units")
            un.setFont(qfont(F.small))
            un.setStyleSheet(f"color: {P.text_secondary};")
            un.setAlignment(Qt.AlignCenter)
            cl.addWidget(un)

            ring_row.addWidget(col_w, 1)
        inner.addLayout(ring_row)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"color: {P.divider};")
        inner.addWidget(div)

        # Bar breakdown
        for row in occ_data:
            loc = row["location"]
            tot = max(row["total"], 1)
            occ = row["occupied"]
            pct = occ / tot
            color = city_colors.get(loc, P.info)

            bar_row = QHBoxLayout()
            nm = QLabel(loc)
            nm.setFixedWidth(100)
            nm.setFont(qfont(F.small_bold))
            nm.setStyleSheet(f"color: {P.text_primary};")
            bar_row.addWidget(nm)

            pb = GradientProgressBar(pct, color, h=9, w=180)
            bar_row.addWidget(pb)

            pct_lbl = QLabel(f"{int(pct*100)}%")
            pct_lbl.setFont(qfont(F.small))
            pct_lbl.setStyleSheet(f"color: {color};")
            bar_row.addWidget(pct_lbl)
            bar_row.addStretch()
            inner.addLayout(bar_row)

        return card

    def _financial_snapshot_widget(self) -> Card:
        card = Card(title="Financial Snapshot", accent_color=P.success)
        inner = card.body_layout()

        fin = db.compareCollectedVsPending(self._loc)
        collected = fin.get("collected") or 0
        pending = fin.get("pending") or 0
        total = collected + pending or 1
        pct_col = collected / total

        big = QLabel(f"£{collected:,.0f}")
        big.setFont(QFont("Segoe UI", 28, QFont.Bold))
        big.setStyleSheet(f"color: {P.success};")
        inner.addWidget(big)
        sub = QLabel("Total Collected")
        sub.setFont(qfont(F.small))
        sub.setStyleSheet(f"color: {P.text_muted};")
        inner.addWidget(sub)

        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"color: {P.divider};")
        inner.addWidget(div)

        lbl = QLabel("Collection Rate")
        lbl.setFont(qfont(F.label))
        lbl.setStyleSheet(f"color: {P.text_secondary};")
        inner.addWidget(lbl)
        pb = GradientProgressBar(pct_col, P.success, h=10, w=250)
        inner.addWidget(pb)
        pct_lbl = QLabel(f"{int(pct_col*100)}% collected")
        pct_lbl.setFont(qfont(F.small_bold))
        pct_lbl.setStyleSheet(f"color: {P.success};")
        inner.addWidget(pct_lbl)

        div2 = QFrame(); div2.setFrameShape(QFrame.HLine)
        div2.setStyleSheet(f"color: {P.divider};")
        inner.addWidget(div2)

        # Overdue
        r1 = QHBoxLayout()
        r1l = QLabel("Overdue Rent")
        r1l.setFont(qfont(F.label))
        r1l.setStyleSheet(f"color: {P.text_secondary};")
        r1.addWidget(r1l)
        r1.addStretch()
        r1v = QLabel(f"£{pending:,.0f}")
        r1v.setFont(qfont(F.body_bold))
        r1v.setStyleSheet(f"color: {P.danger};")
        r1.addWidget(r1v)
        inner.addLayout(r1)

        # Maintenance costs
        mc = db.trackCostsByLocation(self._loc)
        total_mc = sum(r.get("total_cost") or 0 for r in mc)
        r2 = QHBoxLayout()
        r2l = QLabel("Maintenance Spend")
        r2l.setFont(qfont(F.label))
        r2l.setStyleSheet(f"color: {P.text_secondary};")
        r2.addWidget(r2l)
        r2.addStretch()
        r2v = QLabel(f"£{total_mc:,.0f}")
        r2v.setFont(qfont(F.body_bold))
        r2v.setStyleSheet(f"color: {P.warning};")
        r2.addWidget(r2v)
        inner.addLayout(r2)

        return card

    def _quick_tenant_form(self) -> Card:
        card = Card(title="Quick Tenant Entry",
                    accent_color=ROLE_COLORS["Front-Desk Staff"])
        inner = card.body_layout()

        fields = [
            ("NI Number",    "e.g. AB123456C"),
            ("Full Name",    "Full legal name"),
            ("Phone",        "07xxx xxxxxx"),
            ("Email",        "name@email.com"),
            ("Occupation",   "Job title"),
            ("Reference",    "Reference contact"),
            ("Apt Requirements", "e.g. 2-Bedroom"),
            ("Deposit (£)",  "e.g. 1200.00"),
            ("Monthly Rent (£)", "e.g. 1200.00"),
        ]
        self._qf_entries: dict[str, QLineEdit] = {}
        for label, ph in fields:
            lbl = QLabel(label)
            lbl.setFont(qfont(F.label))
            lbl.setStyleSheet(f"color: {P.text_secondary};")
            inner.addWidget(lbl)
            e = QLineEdit()
            e.setPlaceholderText(ph)
            e.setFixedHeight(36)
            inner.addWidget(e)
            self._qf_entries[label] = e

        # Apartment picker
        lbl = QLabel("Apartment")
        lbl.setFont(qfont(F.label))
        lbl.setStyleSheet(f"color: {P.text_secondary};")
        inner.addWidget(lbl)
        apts = db.get_vacant_apartments()
        self._qf_apt_combo = QComboBox()
        apt_labels = [f"{aid} — {alabel}" for aid, alabel in apts]
        if not apt_labels:
            apt_labels = ["No vacant apartments"]
        self._qf_apt_combo.addItems(apt_labels)
        inner.addWidget(self._qf_apt_combo)

        # Lease
        lbl2 = QLabel("Lease Period (months)")
        lbl2.setFont(qfont(F.label))
        lbl2.setStyleSheet(f"color: {P.text_secondary};")
        inner.addWidget(lbl2)
        self._qf_lease = QLineEdit()
        self._qf_lease.setPlaceholderText("12")
        self._qf_lease.setFixedHeight(36)
        inner.addWidget(self._qf_lease)

        self._qf_result = QLabel("")
        self._qf_result.setFont(qfont(F.small))
        self._qf_result.setWordWrap(True)
        inner.addWidget(self._qf_result)

        btn = styled_button("Register Tenant", "primary")
        btn.setFixedHeight(D.btn_h)
        btn.clicked.connect(self._submit_quick_tenant)
        inner.addWidget(btn)

        return card

    def _submit_quick_tenant(self):
        ni    = self._qf_entries["NI Number"].text().strip()
        name  = self._qf_entries["Full Name"].text().strip()
        phone = self._qf_entries["Phone"].text().strip()
        email = self._qf_entries["Email"].text().strip()
        occ   = self._qf_entries["Occupation"].text().strip()
        ref   = self._qf_entries["Reference"].text().strip()
        apt_req = self._qf_entries["Apt Requirements"].text().strip()
        lease_str = self._qf_lease.text().strip()

        if not all([ni, name, phone]):
            self._qf_result.setStyleSheet(f"color: {P.danger};")
            self._qf_result.setText("⚠  NI Number, Name & Phone are required.")
            return

        try:
            deposit = float(self._qf_entries["Deposit (£)"].text() or "0")
            monthly_rent = float(self._qf_entries["Monthly Rent (£)"].text() or "0")
        except ValueError:
            self._qf_result.setStyleSheet(f"color: {P.danger};")
            self._qf_result.setText("⚠  Deposit and Rent must be numbers.")
            return

        try:
            months = int(lease_str or "12")
        except ValueError:
            self._qf_result.setStyleSheet(f"color: {P.danger};")
            self._qf_result.setText("⚠  Lease must be a number.")
            return

        today = datetime.date.today()
        end = (today + datetime.timedelta(days=30 * months)).isoformat()
        apt_str = self._qf_apt_combo.currentText()
        apt_id = None
        if apt_str and "—" in apt_str:
            try:
                apt_id = int(apt_str.split("—")[0].strip())
            except Exception:
                pass

        try:
            db.add_tenant(ni, name, phone, email, occ, ref,
                          apt_req, apt_id, today.isoformat(), end,
                          deposit, monthly_rent)
            self._qf_result.setStyleSheet(f"color: {P.success};")
            self._qf_result.setText(f"✔  Tenant '{name}' registered successfully!")
            for e in self._qf_entries.values():
                e.clear()
        except Exception as ex:
            self._qf_result.setStyleSheet(f"color: {P.danger};")
            self._qf_result.setText(f"⚠  {ex}")

    def _recent_payments_widget(self) -> Card:
        card = Card(title="Recent Payments", accent_color=P.warning)
        cols = [("Tenant", 150), ("Amount", 80), ("Due", 90), ("Status", 80)]
        table, model = make_table(card.body_layout(), cols)
        payments = db.get_all_payments(self._loc)[:14]
        for p in payments:
            color = STATUS_COLORS.get(p["status"], P.text_muted)
            table_insert(model, [
                p["full_name"],
                f"£{p['amount']:,.0f}",
                p["due_date"],
                badge_text(p["status"]),
            ], color)
        return card

    def _maintenance_card(self) -> Card:
        card = Card(title="Active Maintenance Requests",
                    accent_color=ROLE_COLORS["Maintenance Staff"])
        cols = [("Issue", 180), ("Tenant", 130), ("Priority", 80),
                ("Status", 100), ("Reported", 90)]
        table, model = make_table(card.body_layout(), cols)
        items = db.get_all_maintenance(self._loc)[:20]
        for m in items:
            pri = m["priority"]
            color = PRIORITY_COLORS.get(pri, P.text_muted)
            table_insert(model, [
                m["title"],
                m.get("full_name") or "—",
                m["priority"],
                badge_text(m["status"]),
                m["reported_date"],
            ], color)
        return card


# ──────────────────────────────────────────────────────────
# BANNER (QPainter)
# ──────────────────────────────────────────────────────────
class _BannerWidget(QWidget):
    def __init__(self, user, role, loc, color, parent=None):
        super().__init__(parent)
        self._user = user
        self._role = role
        self._loc = loc
        self._color = color

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        color = self._color

        # Gradient
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(_blend(color, P.bg_card, 0.04)))
        grad.setColorAt(1.0, QColor(_blend(color, P.bg_card, 0.72)))
        p.fillRect(0, 0, w, h, grad)

        # Decorative background circles
        p.setPen(Qt.NoPen)
        for cx_f, cy_f, cr, alpha in [
            (0.85, 0.3, 60, 20), (0.75, 0.7, 40, 15),
            (0.92, 0.6, 30, 18), (0.70, 0.2, 25, 12),
        ]:
            dc = QColor("#FFFFFF")
            dc.setAlpha(alpha)
            p.setBrush(dc)
            p.drawEllipse(QRectF(cx_f * w - cr, cy_f * h - cr, cr * 2, cr * 2))

        # Decorative buildings (right side)
        bx = w - 200
        for rect, dark in [
            ((bx+60, 20, 45, h-20), 0.55),
            ((bx+15, 42, 43, h-42), 0.65),
            ((bx+107, 34, 38, h-34), 0.60),
            ((bx+148, 58, 24, h-58), 0.70),
        ]:
            p.setBrush(QColor(_blend(color, "#000000", dark)))
            p.drawRect(*rect)

        # Windows
        rng = random.Random(77)
        win_col = QColor(_blend(color, P.bg_card, 0.25))
        p.setBrush(win_col)
        for row in range(3):
            for col in range(2):
                p.drawRect(bx+68 + col*18, 26 + row*22, 10, 14)
        for row in range(2):
            for col in range(2):
                p.drawRect(bx+22 + col*16, 48 + row*20, 10, 12)

        # Text — larger and bolder
        name = self._user.get("full_name", "").split()[0]
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Segoe UI", 22, QFont.Bold))
        p.drawText(QRectF(40, 14, w-220, 38), Qt.AlignVCenter | Qt.AlignLeft,
                   f"Welcome back, {name}")
        p.setPen(QColor(_blend("#FFFFFF", color, 0.22)))
        p.setFont(QFont("Segoe UI", 12))
        p.drawText(QRectF(40, 52, w-220, 22), Qt.AlignVCenter | Qt.AlignLeft,
                   f"{self._role}  •  {self._loc}")
        p.setPen(QColor(_blend("#FFFFFF", color, 0.40)))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(QRectF(40, 76, w-220, 20), Qt.AlignVCenter | Qt.AlignLeft,
                   f"{datetime.date.today():%A, %d %B %Y}")

        # Bottom accent line
        for i in range(min(280, w)):
            t = i / 280
            lc = QColor(_blend(P.bg_card, color, 0.4*(1-t)))
            p.setPen(lc)
            p.drawLine(i, h-3, i, h)

        p.end()
