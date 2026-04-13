# ============================================================
# PAMS — views/dashboard_view.py
# Role-aware dashboard with KPIs, city rings, quick forms (PySide6)
#
# Contributors (UI):
#   Chouaib Hakim       — Student ID: 24018717
#   Sinoli Rodrigo      — Student ID: 24055025
# ============================================================
from __future__ import annotations
import datetime, random   # datetime for today's date in banners and lease calc; random for decorative building windows

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QLineEdit, QComboBox, QPushButton,
    QSizePolicy, QScrollArea,
)   # all Qt widget classes used across the dashboard and its sub-widgets
from PySide6.QtCore import Qt, QRectF, QTimer   # Qt flags, float rectangle, and timer for animations
from PySide6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient, QPen,
)   # painting primitives used in the custom banner and other painted widgets

from ..theme import PALETTE as P, FONTS as F, DIMS as D, ROLE_COLORS, lerp_color   # design tokens: colours, fonts, sizes, and the per-role colour map
from ..widgets import (
    qfont, Card, StatCard, StatusRing, GradientProgressBar,
    section_header, make_table, table_insert, badge_text,
    styled_button, _blend, Toast,
    STATUS_COLORS, PRIORITY_COLORS, fmt_date,
)   # all shared widget builders and helpers used to build the dashboard panels
from .. import database as db   # the database module for fetching live data for all dashboard KPIs and tables


class DashboardView(QWidget):
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self._user = user   # stores the full user dict (name, role, location) for personalising the dashboard
        self._role = user["role"]   # extracts the role string for deciding which dashboard layout to build
        self._loc = user.get("location")   # extracts the branch location for filtering DB queries
        self._stats = db.dashboard_stats(user)   # queries the DB once for all KPI counters used across the entire dashboard
        self._build()   # builds the appropriate role-specific dashboard layout

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)   # no outer padding so the dashboard fills the scroll area edge to edge
        lay.setSpacing(8)   # 8px gap between the section header, banner, KPI row, and body
        role = self._role
        if role == "Manager":
            self._build_manager(lay)   # city performance rings + financial snapshot layout
        elif role == "Front-Desk Staff":
            self._build_frontdesk(lay)   # quick tenant registration form + recent tenants layout
        elif role == "Finance Manager":
            self._build_finance(lay)   # recent payments table + financial snapshot layout
        elif role == "Maintenance Staff":
            self._build_maintenance(lay)   # active maintenance requests table layout
        else:
            self._build_admin(lay)   # full admin layout with tenants + city + financial panels

    # ──────────────────────────────────────────────────────
    # WELCOME BANNER
    # ──────────────────────────────────────────────────────
    def _welcome_banner(self, parent_layout, color=None):
        color = color or ROLE_COLORS.get(self._role, P.accent)   # uses the role-specific accent colour or falls back to the global accent
        banner = _BannerWidget(self._user, self._role, self._loc, color)   # creates the custom-painted welcome banner widget
        banner.setFixedHeight(120)   # locks the banner to exactly 120px tall
        parent_layout.addWidget(banner)

    # ──────────────────────────────────────────────────────
    # KPI ROW
    # ──────────────────────────────────────────────────────
    def _kpi_row(self, parent_layout):
        s = self._stats   # shorthand for the pre-fetched dashboard stats dict
        occ = s["occupied_apts"]   # number of apartments currently occupied
        tot = s["total_apts"] or 1   # total apartments (minimum 1 to avoid division by zero)

        kpis = [
            ("AP", f"{occ}/{tot}", "Apartments Occupied", P.accent),   # occupancy fraction KPI in accent colour
            ("TN", str(s["total_tenants"]),  "Active Tenants",      P.success),   # tenant count KPI in green
            ("MT", str(s["active_maint"]),   "Open Maintenance",    P.warning),   # open maintenance jobs KPI in amber
            ("OD", f"£{s['pending_rent']:,.0f}", "Overdue Rent",    P.danger),   # overdue rent total KPI in red
            ("RC", f"£{s['collected_rent']:,.0f}", "Rent Collected", P.info),   # total collected rent KPI in cyan
        ]
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(D.pad_lg, D.pad_sm, D.pad_lg, D.pad_md)   # large left/right, small top, medium bottom padding for the KPI row
        rl.setSpacing(14)   # 14px gap between each KPI card
        for icon, val, lbl, col in kpis:
            sc = StatCard(icon=icon, value=val, label=lbl, color=col)   # builds a KPI card with animated icon badge, large value, and caption
            rl.addWidget(sc, 1)   # each KPI card gets equal stretch so they share the row width evenly
        parent_layout.addWidget(row)

    # ──────────────────────────────────────────────────────
    # ADMIN
    # ──────────────────────────────────────────────────────
    def _build_admin(self, lay):
        section_header(lay, "Administrator Dashboard",
                       f"Location: {self._loc} | {datetime.date.today():%d %b %Y}",
                       accent=ROLE_COLORS["Administrator"])   # displays the section header with today's date for the admin role
        self._welcome_banner(lay, ROLE_COLORS["Administrator"])   # adds the painted welcome banner in the admin emerald colour
        self._kpi_row(lay)   # adds the 5 KPI stat cards below the banner

        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)   # padding on the sides and bottom of the body area
        bl.setSpacing(10)   # 10px gap between the tenants card and the right-side panel

        bl.addWidget(self._tenants_card(), 3)   # recent tenants table takes 3 stretch units (wider)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(D.pad_sm)   # small gap between the city performance and financial snapshot cards
        rl.addWidget(self._city_performance_widget())   # city occupancy rings stacked on top
        rl.addWidget(self._financial_snapshot_widget())   # financial summary below the rings
        bl.addWidget(right, 2)   # right column takes 2 stretch units (narrower)

        lay.addWidget(body, 1)   # the body expands to fill all remaining vertical space

    # ──────────────────────────────────────────────────────
    # MANAGER
    # ──────────────────────────────────────────────────────
    def _build_manager(self, lay):
        section_header(lay, "Manager Dashboard",
                       "All-city occupancy & performance overview",
                       accent=ROLE_COLORS["Manager"])   # manager header in the manager-role indigo colour
        self._welcome_banner(lay, ROLE_COLORS["Manager"])   # painted welcome banner with manager colour
        self._kpi_row(lay)   # KPI row showing occupancy, revenue and tenant counts

        body = QWidget()   # container widget that holds the two side-by-side panels
        bl = QHBoxLayout(body)   # horizontal layout places city performance left and financial snapshot right
        bl.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)   # large side padding and bottom padding for the body area
        bl.setSpacing(10)   # 10px gap between the city performance and financial snapshot panels
        bl.addWidget(self._city_performance_widget(), 5)   # city rings + bar chart takes 5 stretch units
        bl.addWidget(self._financial_snapshot_widget(), 4)   # financial summary takes 4 stretch units
        lay.addWidget(body, 1)   # body fills all remaining vertical space

    # ──────────────────────────────────────────────────────
    # FRONT DESK
    # ──────────────────────────────────────────────────────
    def _build_frontdesk(self, lay):
        section_header(lay, "Front-Desk Dashboard",
                       "Register tenants & manage inquiries quickly",
                       accent=ROLE_COLORS["Front-Desk Staff"])   # front-desk header in the rose-pink role colour
        self._welcome_banner(lay, ROLE_COLORS["Front-Desk Staff"])   # painted welcome banner for front-desk staff
        self._kpi_row(lay)   # KPI row shared by all roles

        body = QWidget()   # container widget that holds the form and tenants table side by side
        bl = QHBoxLayout(body)   # horizontal layout places the quick form on the left and tenants table on the right
        bl.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)   # large side padding and bottom padding for the body area
        bl.setSpacing(10)   # 10px gap between the quick form and the tenants table
        bl.addWidget(self._quick_tenant_form(), 2)   # quick tenant entry form takes 2 stretch units (narrower)
        bl.addWidget(self._tenants_card(), 3)   # recent tenants table takes 3 stretch units (wider)
        lay.addWidget(body, 1)   # body fills all remaining vertical space

    # ──────────────────────────────────────────────────────
    # FINANCE
    # ──────────────────────────────────────────────────────
    def _build_finance(self, lay):
        section_header(lay, "Finance Dashboard",
                       "Payment overview & billing summary",
                       accent=ROLE_COLORS["Finance Manager"])   # finance header in the amber role colour
        self._welcome_banner(lay, ROLE_COLORS["Finance Manager"])   # welcome banner in amber
        self._kpi_row(lay)   # KPI row showing payments, overdue and collection stats

        body = QWidget()   # container widget holding the payments table and financial summary side by side
        bl = QHBoxLayout(body)   # horizontal layout places payments on the left and financial snapshot on the right
        bl.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)   # large side padding and bottom padding for the body area
        bl.setSpacing(10)   # 10px gap between the payments table and financial summary
        bl.addWidget(self._recent_payments_widget(), 3)   # recent payments table takes 3 stretch units
        bl.addWidget(self._financial_snapshot_widget(), 2)   # financial summary card takes 2 stretch units
        lay.addWidget(body, 1)   # body fills all remaining vertical space

    # ──────────────────────────────────────────────────────
    # MAINTENANCE
    # ──────────────────────────────────────────────────────
    def _build_maintenance(self, lay):
        section_header(lay, "Maintenance Dashboard",
                       "Active requests & workload overview",
                       accent=ROLE_COLORS["Maintenance Staff"])   # maintenance header in the orange role colour
        self._welcome_banner(lay, ROLE_COLORS["Maintenance Staff"])   # welcome banner in orange
        self._kpi_row(lay)   # KPI row showing open, in-progress and completed maintenance counts

        body = QWidget()   # container widget holding the full-width maintenance table
        bl = QHBoxLayout(body)   # horizontal layout (single child stretches to fill the full width)
        bl.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)   # large side padding and bottom padding for the body area
        bl.setSpacing(10)   # spacing token kept consistent even with a single child widget
        bl.addWidget(self._maintenance_card(), 1)   # maintenance requests table fills the full body width
        lay.addWidget(body, 1)   # body fills all remaining vertical space

    # ──────────────────────────────────────────────────────
    # WIDGET BUILDERS
    # ──────────────────────────────────────────────────────
    def _tenants_card(self) -> Card:
        card = Card(title="Recent Tenants", accent_color=P.accent)   # creates a titled card panel with the indigo accent stripe
        cols = [("Tenant", 160), ("Apartment", 90), ("Lease End", 90), ("Status", 80)]   # column names with hint widths for the tenants table
        table, model = make_table(card.body_layout(), cols)   # builds a styled read-only table and returns the view and data model
        tenants = db.get_all_tenants(self._loc)[:12]   # fetches the 12 most-recent tenants filtered to the user's location
        for t in tenants:
            color = STATUS_COLORS.get(t["status"], P.text_muted)   # picks the row text colour based on tenant status (green/red/etc.)
            table_insert(model, [
                t["full_name"],
                t.get("apt_number") or "—",   # shows a dash if the tenant has no apartment assigned
                fmt_date(t.get("lease_end")),   # lease end in UK DD/MM/YYYY format
                badge_text(t["status"]),   # converts status to a coloured circle badge symbol
            ], color)
        return card

    def _city_performance_widget(self) -> Card:
        card = Card(title="City Performance", accent_color=P.info)   # card with cyan info accent stripe
        inner = card.body_layout()
        occ_data = db.getOccupancyByCity()   # fetches occupancy counts grouped by city/branch location

        if not occ_data:
            lbl = QLabel("No data available.")
            lbl.setFont(qfont(F.body))
            lbl.setStyleSheet(f"color: {P.text_muted};")   # muted placeholder message when no data exists
            inner.addWidget(lbl)
            return card

        city_colors = {
            "Bristol": P.accent, "London": P.accent2,   # Bristol=indigo, London=violet
            "Manchester": P.success, "Cardiff": P.warning,   # Manchester=green, Cardiff=amber
        }

        ring_row = QHBoxLayout()
        for row in occ_data:
            loc = row["location"]
            tot = row["total"] or 1   # at least 1 to prevent division-by-zero
            occ = row["occupied"]
            pct = occ / tot   # occupancy fraction 0.0-1.0 for the ring fill
            color = city_colors.get(loc, P.info)   # falls back to cyan if the city is not in the map

            col_w = QWidget()
            cl = QVBoxLayout(col_w)
            cl.setAlignment(Qt.AlignCenter)   # keeps ring, name, and unit count centred
            cl.setSpacing(2)

            ring = StatusRing(110, 12, color, pct)   # 110px diameter ring, 12px track, filled to occupancy %
            cl.addWidget(ring, 0, Qt.AlignCenter)

            nm = QLabel(loc)
            nm.setFont(qfont(F.small_bold))
            nm.setStyleSheet(f"color: {color};")   # city name in the same colour as its ring
            nm.setAlignment(Qt.AlignCenter)
            cl.addWidget(nm)

            un = QLabel(f"{occ}/{tot} units")
            un.setFont(qfont(F.small))
            un.setStyleSheet(f"color: {P.text_secondary};")   # secondary grey for the unit fraction text
            un.setAlignment(Qt.AlignCenter)
            cl.addWidget(un)

            ring_row.addWidget(col_w, 1)   # equal stretch so all city columns share the width evenly
        inner.addLayout(ring_row)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)   # horizontal separator line between the rings and the bar chart
        div.setStyleSheet(f"color: {P.divider};")
        inner.addWidget(div)

        # Bar breakdown
        for row in occ_data:
            loc = row["location"]
            tot = max(row["total"], 1)   # guards against zero total apartments
            occ = row["occupied"]
            pct = occ / tot
            color = city_colors.get(loc, P.info)

            bar_row = QHBoxLayout()
            nm = QLabel(loc)
            nm.setFixedWidth(100)   # fixed 100px so all city name labels align left consistently
            nm.setFont(qfont(F.small_bold))
            nm.setStyleSheet(f"color: {P.text_primary};")
            bar_row.addWidget(nm)

            pb = GradientProgressBar(pct, color, h=9, w=180)   # 9px tall, 180px wide gradient bar filled to occupancy %
            bar_row.addWidget(pb)

            pct_lbl = QLabel(f"{int(pct*100)}%")
            pct_lbl.setFont(qfont(F.small))
            pct_lbl.setStyleSheet(f"color: {color};")   # percentage in the city's accent colour
            bar_row.addWidget(pct_lbl)
            bar_row.addStretch()   # fills any remaining horizontal space to the right
            inner.addLayout(bar_row)

        return card

    def _financial_snapshot_widget(self) -> Card:
        card = Card(title="Financial Snapshot", accent_color=P.success)   # green card for the financial summary
        inner = card.body_layout()

        fin = db.compareCollectedVsPending(self._loc)   # gets collected vs pending rent totals for the branch
        collected = fin.get("collected") or 0   # total £ collected (defaults to 0 if missing)
        pending = fin.get("pending") or 0   # total £ still overdue
        total = collected + pending or 1   # combined total (minimum 1 to avoid division-by-zero)
        pct_col = collected / total   # collection rate as a fraction 0.0-1.0

        big = QLabel(f"£{collected:,.0f}")
        big.setFont(QFont("Segoe UI", 28, QFont.Bold))   # very large 28pt bold for the headline collected amount
        big.setStyleSheet(f"color: {P.success};")   # green to indicate a positive financial figure
        inner.addWidget(big)
        sub = QLabel("Total Collected")
        sub.setFont(qfont(F.small))
        sub.setStyleSheet(f"color: {P.text_muted};")   # muted label below the big number
        inner.addWidget(sub)

        div = QFrame(); div.setFrameShape(QFrame.HLine)   # horizontal divider after the headline figure
        div.setStyleSheet(f"color: {P.divider};")
        inner.addWidget(div)

        lbl = QLabel("Collection Rate")
        lbl.setFont(qfont(F.label))
        lbl.setStyleSheet(f"color: {P.text_secondary};")   # secondary grey for the rate label
        inner.addWidget(lbl)
        pb = GradientProgressBar(pct_col, P.success, h=10, w=250)   # 10px tall green gradient bar showing the collection rate
        inner.addWidget(pb)
        pct_lbl = QLabel(f"{int(pct_col*100)}% collected")
        pct_lbl.setFont(qfont(F.small_bold))
        pct_lbl.setStyleSheet(f"color: {P.success};")   # green percentage label matching the bar colour
        inner.addWidget(pct_lbl)

        div2 = QFrame(); div2.setFrameShape(QFrame.HLine)   # second divider separating the rate from the detail rows
        div2.setStyleSheet(f"color: {P.divider};")
        inner.addWidget(div2)

        # Overdue
        r1 = QHBoxLayout()
        r1l = QLabel("Overdue Rent")
        r1l.setFont(qfont(F.label))
        r1l.setStyleSheet(f"color: {P.text_secondary};")
        r1.addWidget(r1l)
        r1.addStretch()   # pushes the overdue amount to the right edge
        r1v = QLabel(f"£{pending:,.0f}")
        r1v.setFont(qfont(F.body_bold))
        r1v.setStyleSheet(f"color: {P.danger};")   # red to highlight the overdue amount
        r1.addWidget(r1v)
        inner.addLayout(r1)

        # Maintenance costs
        mc = db.trackCostsByLocation(self._loc)   # fetches maintenance cost totals grouped by location
        total_mc = sum(r.get("total_cost") or 0 for r in mc)   # sums all maintenance costs across all locations
        r2 = QHBoxLayout()
        r2l = QLabel("Maintenance Spend")
        r2l.setFont(qfont(F.label))
        r2l.setStyleSheet(f"color: {P.text_secondary};")
        r2.addWidget(r2l)
        r2.addStretch()
        r2v = QLabel(f"£{total_mc:,.0f}")
        r2v.setFont(qfont(F.body_bold))
        r2v.setStyleSheet(f"color: {P.warning};")   # amber for maintenance spend (an outgoing cost)
        r2.addWidget(r2v)
        inner.addLayout(r2)

        return card

    def _quick_tenant_form(self) -> Card:
        card = Card(title="Quick Tenant Entry",
                    accent_color=ROLE_COLORS["Front-Desk Staff"])   # card in the front-desk rose-pink accent colour
        inner = card.body_layout()

        fields = [
            ("NI Number",    "e.g. AB123456C"),   # National Insurance number (required for tenant identity)
            ("Full Name",    "Full legal name"),
            ("Phone",        "07xxx xxxxxx"),
            ("Email",        "name@email.com"),
            ("Occupation",   "Job title"),
            ("Reference",    "Reference contact"),
            ("Apt Requirements", "e.g. 2-Bedroom"),   # free-text field for what type of apartment the tenant needs
            ("Deposit (£)",  "e.g. 1200.00"),
            ("Monthly Rent (£)", "e.g. 1200.00"),
        ]
        self._qf_entries: dict[str, QLineEdit] = {}   # stores each form field by its label key so values can be read on submit
        for label, ph in fields:
            lbl = QLabel(label)
            lbl.setFont(qfont(F.label))
            lbl.setStyleSheet(f"color: {P.text_secondary};")
            inner.addWidget(lbl)
            e = QLineEdit()
            e.setPlaceholderText(ph)   # shows example input format as grey hint text
            e.setFixedHeight(36)   # standardises all input fields to 36px tall
            inner.addWidget(e)
            self._qf_entries[label] = e   # saves the field widget keyed by its label string

        # Apartment picker
        lbl = QLabel("Apartment")
        lbl.setFont(qfont(F.label))
        lbl.setStyleSheet(f"color: {P.text_secondary};")
        inner.addWidget(lbl)
        apts = db.get_vacant_apartments()   # queries the DB for apartments with 'Vacant' status
        self._qf_apt_combo = QComboBox()
        apt_labels = [f"{aid} — {alabel}" for aid, alabel in apts]   # formats each vacant apartment as 'ID — unit label'
        if not apt_labels:
            apt_labels = ["No vacant apartments"]   # shows this placeholder if there are no vacant units available
        self._qf_apt_combo.addItems(apt_labels)   # populates the dropdown with all vacant apartment options
        inner.addWidget(self._qf_apt_combo)

        # Lease
        lbl2 = QLabel("Lease Period (months)")
        lbl2.setFont(qfont(F.label))
        lbl2.setStyleSheet(f"color: {P.text_secondary};")
        inner.addWidget(lbl2)
        self._qf_lease = QLineEdit()
        self._qf_lease.setPlaceholderText("12")   # defaults to 12 months as the hint
        self._qf_lease.setFixedHeight(36)
        inner.addWidget(self._qf_lease)

        self._qf_result = QLabel("")   # blank label that shows success/error messages after form submission
        self._qf_result.setFont(qfont(F.small))
        self._qf_result.setWordWrap(True)   # allows long error messages to wrap onto multiple lines
        inner.addWidget(self._qf_result)

        btn = styled_button("Register Tenant", "primary")   # primary styled button with the indigo gradient
        btn.setFixedHeight(D.btn_h)   # standard button height from design tokens
        btn.clicked.connect(self._submit_quick_tenant)   # wires the button click to the form submission handler
        inner.addWidget(btn)

        return card

    def _submit_quick_tenant(self):
        ni    = self._qf_entries["NI Number"].text().strip()   # reads and trims the NI number from the form field
        name  = self._qf_entries["Full Name"].text().strip()   # reads the full legal name
        phone = self._qf_entries["Phone"].text().strip()   # reads the phone number
        email = self._qf_entries["Email"].text().strip()   # reads the email address
        occ   = self._qf_entries["Occupation"].text().strip()   # reads the occupation/job title
        ref   = self._qf_entries["Reference"].text().strip()   # reads the referee contact details
        apt_req = self._qf_entries["Apt Requirements"].text().strip()   # reads the apartment type preference
        lease_str = self._qf_lease.text().strip()   # reads the lease duration in months

        if not all([ni, name, phone]):
            self._qf_result.setStyleSheet(f"color: {P.danger};")   # makes the result label text red
            self._qf_result.setText("ERROR: NI Number, Name and Phone are required.")
            return   # stops submission if required fields are missing

        try:
            deposit = float(self._qf_entries["Deposit (£)"].text() or "0")   # converts deposit to float or 0 if empty
            monthly_rent = float(self._qf_entries["Monthly Rent (£)"].text() or "0")   # converts monthly rent to float or 0
        except ValueError:
            self._qf_result.setStyleSheet(f"color: {P.danger};")
            self._qf_result.setText("ERROR: Deposit and Rent must be numbers.")
            return

        try:
            months = int(lease_str or "12")   # parses lease months as integer, defaulting to 12 if empty
        except ValueError:
            self._qf_result.setStyleSheet(f"color: {P.danger};")
            self._qf_result.setText("ERROR: Lease must be a number.")
            return

        today = datetime.date.today()   # gets today's date as the lease start date
        end = (today + datetime.timedelta(days=30 * months)).isoformat()   # calculates lease end date by adding 30×months days
        apt_str = self._qf_apt_combo.currentText()   # reads the selected apartment text from the dropdown
        apt_id = None
        if apt_str and "—" in apt_str:
            try:
                apt_id = int(apt_str.split("—")[0].strip())   # extracts the apartment ID from the 'ID — label' format
            except Exception:
                pass

        try:
            db.add_tenant(ni, name, phone, email, occ, ref,
                          apt_req, apt_id, today.isoformat(), end,
                          deposit, monthly_rent)   # inserts the new tenant record into the database
            self._qf_result.setStyleSheet(f"color: {P.success};")   # makes the result label green for success
            self._qf_result.setText(f"SUCCESS: Tenant '{name}' registered successfully.")
            for e in self._qf_entries.values():
                e.clear()   # clears all form fields after a successful registration
        except Exception as ex:
            self._qf_result.setStyleSheet(f"color: {P.danger};")
            self._qf_result.setText(f"ERROR: {ex}")   # shows the DB error message in red if the insert fails

    def _recent_payments_widget(self) -> Card:
        card = Card(title="Recent Payments", accent_color=P.warning)   # amber accent card for the payments table
        cols = [("Tenant", 150), ("Amount", 80), ("Due", 90), ("Status", 80)]   # payment table columns with hint widths
        table, model = make_table(card.body_layout(), cols)   # builds the styled read-only payments table
        payments = db.get_all_payments(self._loc)[:14]   # fetches the 14 most-recent payments for the branch
        for p in payments:
            color = STATUS_COLORS.get(p["status"], P.text_muted)   # colours each row by payment status (green=Paid, red=Overdue)
            table_insert(model, [
                p["full_name"],
                f"£{p['amount']:,.0f}",   # formats the amount with comma separator and £ prefix
                fmt_date(p["due_date"]),
                badge_text(p["status"]),   # converts the status to a badge symbol
            ], color)
        return card

    def _maintenance_card(self) -> Card:
        card = Card(title="Active Maintenance Requests",
                    accent_color=ROLE_COLORS["Maintenance Staff"])   # orange accent card for the maintenance table
        cols = [("Issue", 180), ("Tenant", 130), ("Priority", 80),
                ("Status", 100), ("Reported", 90)]   # maintenance table columns with hint widths
        table, model = make_table(card.body_layout(), cols)   # builds the styled read-only maintenance table
        items = db.get_all_maintenance(self._loc)[:20]   # fetches the 20 most-recent maintenance requests for the branch
        for m in items:
            pri = m["priority"]
            color = PRIORITY_COLORS.get(pri, P.text_muted)   # colours rows by priority: red=High, amber=Medium, green=Low
            table_insert(model, [
                m["title"],
                m.get("full_name") or "—",   # shows a dash if the maintenance request has no linked tenant
                m["priority"],
                badge_text(m["status"]),   # badge symbol for the current maintenance status
                fmt_date(m["reported_date"]),
            ], color)
        return card


# ──────────────────────────────────────────────────────────
# BANNER (QPainter)
# ──────────────────────────────────────────────────────────
class _BannerWidget(QWidget):
    def __init__(self, user, role, loc, color, parent=None):
        super().__init__(parent)
        self._user = user   # the full user dict used to extract the first name for the greeting
        self._role = role   # the role string displayed on the second line of the banner
        self._loc = loc   # the branch location displayed beside the role
        self._color = color   # the role accent colour used for the banner gradient and decorative elements

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)   # enables smooth anti-aliased shapes
        w, h = self.width(), self.height()
        color = self._color   # shorthand for the role accent colour

        # Gradient
        grad = QLinearGradient(0, 0, w, 0)   # horizontal left-to-right gradient across the full banner width
        grad.setColorAt(0.0, QColor(_blend(color, P.bg_card, 0.04)))   # left edge: 4% blended with card bg (nearly pure accent)
        grad.setColorAt(1.0, QColor(_blend(color, P.bg_card, 0.72)))   # right edge: 72% blended (much lighter, fades out)
        p.fillRect(0, 0, w, h, grad)   # fills the entire banner background with the horizontal gradient

        # Decorative background circles
        p.setPen(Qt.NoPen)   # no border on the decorative circles
        for cx_f, cy_f, cr, alpha in [
            (0.85, 0.3, 60, 20), (0.75, 0.7, 40, 15),   # large and medium circles at the upper and lower right area
            (0.92, 0.6, 30, 18), (0.70, 0.2, 25, 12),   # smaller circles further to the right and upper region
        ]:
            dc = QColor("#FFFFFF")
            dc.setAlpha(alpha)   # very low alpha (12-20) so the circles are barely visible watermark-like shapes
            p.setBrush(dc)
            p.drawEllipse(QRectF(cx_f * w - cr, cy_f * h - cr, cr * 2, cr * 2))   # draws each decorative circle at its proportional position

        # Decorative buildings (right side)
        bx = w - 200   # locks the building group to start 200px from the right edge regardless of window width
        for rect, dark in [
            ((bx+60, 20, 45, h-20), 0.55),   # tallest building: 45px wide, starts from y=20, darkened 55%
            ((bx+15, 42, 43, h-42), 0.65),   # leftmost building: 43px wide, starts from y=42, darkened 65%
            ((bx+107, 34, 38, h-34), 0.60),  # third building: 38px wide, starts from y=34, darkened 60%
            ((bx+148, 58, 24, h-58), 0.70),  # shortest building: 24px wide, starts from y=58, darkened 70%
        ]:
            p.setBrush(QColor(_blend(color, "#000000", dark)))   # blends the role colour toward black to create dark building silhouettes
            p.drawRect(*rect)   # draws each building as a filled rectangle

        # Windows
        rng = random.Random(77)   # fixed seed so window pattern is deterministic (same every repaint)
        win_col = QColor(_blend(color, P.bg_card, 0.25))   # window colour: 25% card bg blend for a warm glow effect
        p.setBrush(win_col)
        for row in range(3):   # 3 rows of windows on the tall building
            for col in range(2):   # 2 columns of windows per row
                p.drawRect(bx+68 + col*18, 26 + row*22, 10, 14)   # each window is 10×14px, spaced 18px horizontally and 22px vertically
        for row in range(2):   # 2 rows of windows on the second building
            for col in range(2):
                p.drawRect(bx+22 + col*16, 48 + row*20, 10, 12)   # slightly smaller windows on the second building

        # Text — larger and bolder
        name = self._user.get("full_name", "").split()[0]   # extracts just the first name for the personalised greeting
        p.setPen(QColor("#FFFFFF"))   # white text for maximum contrast against the gradient background
        p.setFont(QFont("Segoe UI", 22, QFont.Bold))   # large 22pt bold for the 'Welcome back, Name' headline
        p.drawText(QRectF(40, 14, w-220, 38), Qt.AlignVCenter | Qt.AlignLeft,
                   f"Welcome back, {name}")   # draws the personalised greeting headline 40px from the left edge
        p.setPen(QColor(_blend("#FFFFFF", color, 0.22)))   # slightly tinted white (22% accent blend) for the role/location line
        p.setFont(QFont("Segoe UI", 12))   # medium 12pt for the role and location subtitle
        p.drawText(QRectF(40, 52, w-220, 22), Qt.AlignVCenter | Qt.AlignLeft,
                   f"{self._role}  •  {self._loc}")   # draws 'Role  •  Location' as the second line of text
        p.setPen(QColor(_blend("#FFFFFF", color, 0.40)))   # more tinted white (40% accent) for the less prominent date line
        p.setFont(QFont("Segoe UI", 10))   # small 10pt for today's date
        p.drawText(QRectF(40, 76, w-220, 20), Qt.AlignVCenter | Qt.AlignLeft,
                   f"{datetime.date.today():%A, %d %B %Y}")   # draws today's full date in 'Monday, 01 January 2025' format

        # Bottom accent line
        for i in range(min(280, w)):   # draws up to 280 vertical 3px lines across the bottom of the banner
            t = i / 280   # t goes from 0.0 at the left to 1.0 at 280px creating a fade-out effect
            lc = QColor(_blend(P.bg_card, color, 0.4*(1-t)))   # blends from accent toward card bg as it goes right
            p.setPen(lc)
            p.drawLine(i, h-3, i, h)   # draws a 3px tall vertical line at this position to form the accent gradient strip

        p.end()
