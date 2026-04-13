# ============================================================
# PAMS — views/report_view.py
# Reporting & Analytics View (PySide6)
#
# Contributors (UI):
#   Chouaib Hakim       — Student ID: 24018717
#   Sinoli Rodrigo      — Student ID: 24055025
# ============================================================
from __future__ import annotations   # enables forward-reference type hints without quote wrapping

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QFrame, QGridLayout, QScrollArea,
)   # all Qt widget and layout classes needed for the reporting screen
from PySide6.QtCore import Qt   # Qt alignment constants used throughout
from PySide6.QtGui import QFont   # QFont used for bold headings and stat labels

from ..theme import PALETTE as P, FONTS as F, DIMS as D   # P = brand colours, F = font sizes, D = spacing constants
from ..widgets import (
    qfont, Card, StatCard, section_header, make_table, table_clear,
    table_insert, badge_text, StatusRing, GradientProgressBar, styled_button,
    STATUS_COLORS, fmt_date,
)   # shared UI helpers: stat card, ring chart, progress bar, table factory, badge formatter
from .. import database as db   # all database queries for occupancy, finance, maintenance, and lease data

CITY_COLORS = {
    "Bristol":    P.accent,     # Bristol rows and rings use the primary accent (blue/indigo)
    "London":     P.accent2,    # London rows and rings use the secondary accent colour
    "Manchester": P.success,    # Manchester rows and rings use the green success colour
    "Cardiff":    P.warning,    # Cardiff rows and rings use the amber warning colour
}   # maps each city name to a distinctive brand colour used in charts and progress bars


class ReportView(QWidget):   # main reports panel showing occupancy, financial, maintenance, and lease analytics
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)   # registers this widget with Qt's parent-child ownership system
        self._user = user   # stores the logged-in user dict (role, location, etc.)
        self._loc = user.get("location")   # stores the user's branch city to scope all report data
        self._current_tab = "occupancy"   # tracks which report tab is currently displayed
        self._build()   # constructs the tab bar and content area shell
        self._switch_tab("occupancy")   # loads the occupancy report as the default landing tab

    def _build(self):
        lay = QVBoxLayout(self)   # stacks the page header, tab bar, and content area vertically
        lay.setContentsMargins(0, 0, 0, 0)   # removes outer padding so the view fills its container edge-to-edge
        lay.setSpacing(8)   # 8 px gap between the header, tab bar, and content area

        section_header(lay, "Reports & Analytics",
                       "Occupancy, financial and maintenance summaries")   # adds the styled page title and subtitle strip

        # ── Tab bar ──
        tab_bar = QHBoxLayout()   # lays out the four report tab buttons side by side
        tab_bar.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_md)   # horizontal padding and bottom margin for the tab bar
        self._tab_btns: dict[str, QPushButton] = {}   # dict mapping tab key → QPushButton for easy style updates

        for key, label in [
            ("occupancy",   "Occupancy"),
            ("financial",   "Financial Summary"),
            ("maintenance", "Maintenance Costs"),
            ("leases",      "Lease Tracking"),
        ]:   # iterates over the four report tabs to create their buttons
            btn = QPushButton(label)   # creates a flat tab button with the report label
            btn.setCursor(Qt.PointingHandCursor)   # changes the mouse cursor to a hand when hovering the tab button
            btn.setFont(qfont(F.body_bold))   # applies the bold body font to the tab label
            btn.setFlat(True)   # removes the raised button appearance so it looks like a text tab
            btn.clicked.connect(lambda _=False, k=key: self._switch_tab(k))   # switches to this tab when its button is clicked
            tab_bar.addWidget(btn)   # adds the tab button to the tab bar layout
            self._tab_btns[key] = btn   # stores the button reference so _switch_tab can restyle it

        tab_bar.addStretch()   # pushes all tab buttons to the left
        lay.addLayout(tab_bar)   # adds the tab bar to the main vertical layout

        # ── Content area ──
        self._content = QWidget()   # invisible container that holds whichever report is currently displayed
        self._content_lay = QVBoxLayout(self._content)   # stacks the active report's sections vertically
        self._content_lay.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)   # adds padding around the report content
        self._content_lay.setSpacing(D.pad_sm)   # small gap between each section within a report
        lay.addWidget(self._content, 1)   # adds the content area to the layout, giving it all remaining vertical space

    def _switch_tab(self, key: str):
        self._current_tab = key   # records which tab is now active
        # Style active tab
        for k, btn in self._tab_btns.items():
            if k == key:
                btn.setStyleSheet(
                    f"color: {P.accent}; border-bottom: 2px solid {P.accent}; "
                    f"padding: 4px 12px; background: transparent;")   # highlights the active tab with an accent underline
            else:
                btn.setStyleSheet(
                    f"color: {P.text_muted}; padding: 4px 12px; "
                    f"background: transparent;")   # styles inactive tabs in muted text with no underline

        # Clear content
        while self._content_lay.count():
            item = self._content_lay.takeAt(0)   # removes the first item in the content layout repeatedly until empty
            w = item.widget()
            if w:
                w.deleteLater()   # schedules old widgets for deletion to free memory
            elif item.layout():
                self._clear_layout(item.layout())   # recursively clears any nested layouts

        builders = {
            "occupancy":   self._build_occupancy,
            "financial":   self._build_financial,
            "maintenance": self._build_maintenance,
            "leases":      self._build_leases,
        }   # maps each tab key to its builder method
        builders[key]()   # calls the builder for the selected tab to populate the content area

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)   # removes the first layout item repeatedly until the layout is empty
            w = item.widget()
            if w:
                w.deleteLater()   # schedules the widget for deletion
            elif item.layout():
                ReportView._clear_layout(item.layout())   # recursively clears any nested sub-layouts

    # ──────────────────────────────────────────────────────
    # OCCUPANCY REPORT
    # ──────────────────────────────────────────────────────
    def _build_occupancy(self):
        lay = self._content_lay   # shorthand reference to the content area layout

        body = QHBoxLayout()   # places the left ring-chart card and right apartment table side by side
        body.setSpacing(D.pad_sm)   # small gap between the two cards

        # LEFT — ring cards + bar breakdown
        left_card = Card(title="City Occupancy Rings", accent_color=P.accent)   # blue-accented card for the ring charts and bar breakdown
        left_body = left_card.body_layout()   # gets the inner layout to add ring columns and bars into

        occ_data = db.getOccupancyByCity()   # fetches occupancy totals (total units, occupied count) grouped by city

        # Rings row
        ring_row = QHBoxLayout()   # lays out one ring chart column per city side by side
        ring_row.setSpacing(D.pad_md)   # medium gap between each city's ring column
        for row in occ_data:
            loc = row["location"]   # city name for this occupancy row
            tot = max(row["total"], 1)   # total apartment count (clamped to 1 to prevent division by zero)
            occ = row["occupied"]   # number of occupied apartments in this city
            pct = occ / tot   # occupancy rate as a 0.0–1.0 fraction
            color = CITY_COLORS.get(loc, P.info)   # looks up this city's brand colour (falls back to info blue)

            col = QVBoxLayout()   # stacks the ring, city name label, and count label vertically
            col.setAlignment(Qt.AlignCenter)   # centres the column content horizontally
            ring = StatusRing(size=110, thickness=10, color=color, value=pct)   # draws a 110px donut ring showing this city's occupancy percentage
            col.addWidget(ring, alignment=Qt.AlignCenter)   # adds the ring to the column, centred

            nlbl = QLabel(loc)   # city name label shown below the ring
            nlbl.setFont(qfont(F.small_bold))   # applies the small bold font to the city name
            nlbl.setStyleSheet(f"color: {color};")   # colours the city name in its designated brand colour
            nlbl.setAlignment(Qt.AlignCenter)   # centres the city name below the ring
            col.addWidget(nlbl)   # adds the city name label to the column

            clbl = QLabel(f"{occ}/{tot} occupied")   # shows "occupied/total" count below the city name
            clbl.setFont(qfont(F.small))   # applies the small font to the count label
            clbl.setStyleSheet(f"color: {P.text_secondary};")   # colours the count label in secondary text colour
            clbl.setAlignment(Qt.AlignCenter)   # centres the count label below the city name
            col.addWidget(clbl)   # adds the count label to the column
            ring_row.addLayout(col)   # adds this city's column to the ring row

        left_body.addLayout(ring_row)   # adds the full row of city rings to the left card

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)   # horizontal divider between the ring row and bar breakdown
        div.setStyleSheet(f"color: {P.divider};")
        left_body.addWidget(div)   # adds the divider to the left card

        bar_title = QLabel("Occupancy Breakdown by City")   # bold sub-heading above the bar chart section
        bar_title.setFont(qfont(F.h4))   # applies the h4 heading font size
        bar_title.setStyleSheet(f"color: {P.text_primary};")   # colours the heading in the primary text colour
        left_body.addWidget(bar_title)   # adds the bar section heading to the left card

        for row in occ_data:
            loc = row["location"]   # city name for this bar row
            tot = max(row["total"], 1)   # total apartment count (clamped to 1)
            occ = row["occupied"]   # occupied apartment count
            vac = tot - occ   # vacant apartment count derived from total minus occupied
            pct = occ / tot   # occupancy fraction (0.0–1.0) for the gradient bar
            color = CITY_COLORS.get(loc, P.info)   # looks up this city's brand colour

            br = QHBoxLayout()   # one horizontal row per city: name label + bar + stats text
            nlbl = QLabel(loc)   # city name label at the start of the bar row
            nlbl.setFixedWidth(100)   # fixes the name column to 100 px so bars all start at the same x position
            nlbl.setFont(qfont(F.small_bold))   # applies the small bold font to the city name
            nlbl.setStyleSheet(f"color: {P.text_primary};")   # colours the city name in primary text colour
            br.addWidget(nlbl)   # adds the city name to the bar row

            pb = GradientProgressBar(value=pct, color=color,
                                      width=260, height=12)   # draws a 260×12 px gradient bar showing the occupancy percentage
            br.addWidget(pb)   # adds the gradient bar to the row

            info = QLabel(f"  {int(pct*100)}%  Occ:{occ}  Vac:{vac}")   # shows percentage, occupied count, and vacant count after the bar
            info.setFont(qfont(F.small))   # applies the small font to the stats text
            info.setStyleSheet(f"color: {P.text_secondary};")   # colours the stats text in secondary text colour
            br.addWidget(info)   # adds the stats text to the bar row
            br.addStretch()   # pushes the row content to the left
            left_body.addLayout(br)   # adds this city's bar row to the left card

        left_body.addStretch()   # pushes all ring/bar content to the top of the left card
        body.addWidget(left_card, 3)   # left card takes 3 parts of the horizontal space

        # RIGHT — apartment table
        right_card = Card(title="All Apartments", accent_color=P.info)   # info-blue card listing every apartment with its status
        cols = [
            ("Apt #", 70), ("City", 80), ("Type", 90),
            ("Status", 70), ("Rent £", 70),
        ]   # column names and pixel widths for the 5-column apartment table
        tbl, mdl = make_table(right_card.body_layout(), cols)   # creates the table widget and data model inside the right card
        for a in db.get_all_apartments(self._loc):
            color = STATUS_COLORS.get(a["status"], P.text_muted)   # looks up the row colour based on apartment status
            table_insert(mdl, [
                a["apt_number"], a["location"], a["type"],
                badge_text(a["status"]),   # wraps the status in a badge-style label
                f"£{a['monthly_rent']:,.0f}",   # formats the monthly rent as "£1,200"
            ], color)   # inserts this apartment row into the table with its status colour
        body.addWidget(right_card, 2)   # right card takes 2 parts of the horizontal space

        lay.addLayout(body, 1)   # adds the two-card body to the content area, giving it all remaining vertical space

    # ──────────────────────────────────────────────────────
    # FINANCIAL REPORT
    # ──────────────────────────────────────────────────────
    def _build_financial(self):
        lay = self._content_lay   # shorthand reference to the content area layout

        occ_data = db.getOccupancyByCity()   # fetches unit counts per city (used for the per-city table)
        fin_all = db.compareCollectedVsPending()   # fetches total collected vs pending payment amounts across all cities

        col_all = fin_all.get("collected") or 0   # total collected amount (£) across all branches
        pen_all = fin_all.get("pending") or 0   # total pending/overdue amount (£) across all branches
        total = col_all + pen_all or 1   # combined total used as the denominator for collection rate (clamped to 1)

        # Summary strip
        strip = QHBoxLayout()   # horizontal row of three KPI stat cards at the top
        strip.setSpacing(D.pad_sm)   # small gap between each stat card
        for icon, title, val, color in [
            ("RC", "All-City Collected", f"£{col_all:,.0f}", P.success),  # green card showing total collected amount
            ("OD", "All-City Overdue",   f"£{pen_all:,.0f}", P.danger),   # red card showing total overdue amount
            ("CR", "Collection Rate",    f"{int(col_all/total*100)}%", P.accent),  # blue card showing overall collection rate %
        ]:
            sc = StatCard(icon=icon, value=val, label=title, color=color)   # creates a branded KPI card with icon, value, and label
            strip.addWidget(sc)   # adds this stat card to the summary strip
        lay.addLayout(strip)   # adds the three KPI stat cards to the top of the financial report

        # Per-city table
        loc_card = Card(title="Per-City Financial Summary", accent_color=P.success)   # green-accented card listing units/occupancy per city
        cols = [
            ("City", 100), ("Total Units", 90), ("Occupied", 80),
            ("Occ. Rate", 80),
        ]   # column names and pixel widths for the 4-column per-city summary table
        tbl, mdl = make_table(loc_card.body_layout(), cols)   # creates the per-city table inside the card
        for row in occ_data:
            tot = max(row["total"], 1)   # total unit count (clamped to 1 to prevent division by zero)
            occ = row["occupied"]   # occupied unit count for this city
            city_color = CITY_COLORS.get(row["location"], P.text_secondary)   # colours each city row in its brand colour to match the ring charts above
            table_insert(mdl, [
                row["location"], str(tot), str(occ),
                f"{int(occ/tot*100)}%",   # calculates and formats occupancy rate as a percentage string
            ], city_color)   # inserts this city's row coloured with its brand colour
        lay.addWidget(loc_card)   # adds the per-city summary table to the financial report

        # Payment table
        pay_card = Card(title="Recent Payments", accent_color=P.warning)   # amber-accented card showing the 30 most recent payments
        cols2 = [
            ("Tenant", 150), ("Amount", 80), ("Due", 90),
            ("Type", 70), ("Status", 70),
        ]   # column names and pixel widths for the 5-column payments table
        tbl2, mdl2 = make_table(pay_card.body_layout(), cols2)   # creates the payments table inside the card
        for p in db.get_all_payments(self._loc)[:30]:   # fetches and slices to the 30 most recent payments for this branch
            color = STATUS_COLORS.get(p["status"], P.text_muted)   # looks up row colour based on payment status
            table_insert(mdl2, [
                p.get("full_name") or "—",   # tenant name or dash if not linked
                f"£{p['amount']:,.0f}",   # formats the payment amount as "£1,200"
                fmt_date(p["due_date"]),   # due date in UK DD/MM/YYYY format
                p.get("type") or "Rent",   # payment type or default to "Rent"
                badge_text(p["status"]),   # wraps the status in a badge-style label
            ], color)   # inserts this payment row with its status colour
        lay.addWidget(pay_card, 1)   # adds the recent payments table, giving it all remaining vertical space

    # ──────────────────────────────────────────────────────
    # MAINTENANCE COST REPORT
    # ──────────────────────────────────────────────────────
    def _build_maintenance(self):
        lay = self._content_lay   # shorthand reference to the content area layout

        summary = db.trackCostsByLocation(self._loc)   # fetches total maintenance cost and count grouped by status for this branch
        total_cost = sum(r.get("total_cost") or 0 for r in summary)   # sums all status groups to get the overall maintenance spend

        color_map = {
            "Open": P.warning,          # amber for open (unstarted) requests
            "In Progress": P.info,       # blue for in-progress requests
            "Resolved": P.success,       # green for fully resolved requests
        }   # maps each maintenance status to a distinctive brand colour

        strip = QHBoxLayout()   # horizontal row of KPI stat cards, one per status group
        strip.setSpacing(D.pad_sm)   # small gap between each stat card
        status_icons = {"Open": "OP", "In Progress": "IP", "Resolved": "RS"}   # short icon codes shown on each stat card
        for row in summary:
            status = row.get("status", "—")   # maintenance status name for this group
            cost = row.get("total_cost") or 0   # total cost for this status group
            count = row.get("count") or 0   # number of requests in this status group
            color = color_map.get(status, P.accent)   # looks up the brand colour for this status (falls back to accent)
            sc = StatCard(icon=status_icons.get(status, "MT"),
                          value=f"£{cost:,.0f}",
                          label=f"{status} — {count} request(s)",
                          color=color)   # creates a branded KPI card showing cost and request count for this status
            strip.addWidget(sc)   # adds this status stat card to the strip
        lay.addLayout(strip)   # adds the row of stat cards to the top of the maintenance report

        # Total
        div = QFrame()
        div.setFrameShape(QFrame.HLine)   # horizontal divider separating the stat cards from the total label
        div.setStyleSheet(f"color: {P.divider};")
        lay.addWidget(div)   # adds the divider to the layout

        total_lbl = QLabel(f"Total Maintenance Spend:  £{total_cost:,.2f}")   # large amber label showing the overall maintenance cost to 2 decimal places
        total_lbl.setFont(qfont(F.h3))   # applies the h3 heading font size to make it stand out
        total_lbl.setStyleSheet(f"color: {P.warning};")   # colours the total spend in amber to draw attention
        lay.addWidget(total_lbl)   # adds the total spend label to the layout

        # Detailed table
        mc = Card(title="Maintenance Request Costs", accent_color=P.danger)   # red-accented card listing every maintenance request with its cost
        cols = [
            ("Issue", 160), ("Priority", 70), ("Status", 80),
            ("Cost £", 70), ("Hours", 60), ("Resolved", 90),
        ]   # column names and pixel widths for the 6-column maintenance detail table
        tbl, mdl = make_table(mc.body_layout(), cols)   # creates the maintenance detail table inside the card
        for m in db.get_all_maintenance(self._loc):
            row_color = STATUS_COLORS.get(m["status"], P.text_muted)   # colours row by status: amber=Open, blue=In Progress, green=Resolved
            table_insert(mdl, [
                m["title"],   # short issue title
                m["priority"],   # priority level (High, Medium, or Low)
                badge_text(m["status"]),   # wraps the status in a badge-style label
                f"£{m.get('cost') or 0:,.0f}",   # formats the cost as "£500" (0 if not yet resolved)
                str(m.get("time_spent") or 0),   # time spent in hours (0 if not yet resolved)
                fmt_date(m.get("resolved_date")),   # resolved date in DD/MM/YYYY or dash if still open
            ], row_color)   # inserts this maintenance row coloured by its status
        lay.addWidget(mc, 1)   # adds the detailed maintenance table, giving it all remaining vertical space

    # ──────────────────────────────────────────────────────
    # LEASE TRACKING REPORT
    # ──────────────────────────────────────────────────────
    def _build_leases(self):
        lay = self._content_lay   # shorthand reference to the content area layout

        # Day filter
        filter_row = QHBoxLayout()   # horizontal row of "Within N days" radio buttons
        self._lease_days = 30   # default window: show leases expiring within 30 days
        self._lease_group = QButtonGroup(self)   # exclusive group so only one day-range radio can be checked at a time
        for d in [30, 60, 90]:
            rb = QRadioButton(f"Within {d} days")   # creates a radio button for this expiry window
            rb.setStyleSheet(f"color: {P.text_secondary};")   # colours the radio label in secondary text colour
            if d == 30:
                rb.setChecked(True)   # pre-selects the 30-day window as the default view
            rb.toggled.connect(
                lambda checked, dd=d: self._set_lease_days(dd, checked))   # calls _set_lease_days when this radio is toggled on
            self._lease_group.addButton(rb)   # adds this radio to the exclusive group
            filter_row.addWidget(rb)   # adds this radio button to the filter row
        filter_row.addStretch()   # pushes all radio buttons to the left
        lay.addLayout(filter_row)   # adds the day-filter radio row to the layout

        self._lease_summary_lbl = QLabel("")   # amber label updated by _reload_leases to show the expiring count
        self._lease_summary_lbl.setFont(qfont(F.h4))   # applies the h4 heading size to this summary label
        self._lease_summary_lbl.setStyleSheet(f"color: {P.warning};")   # colours the summary label in amber to draw attention
        lay.addWidget(self._lease_summary_lbl)   # adds the summary count label to the layout

        card = Card(title="Expiring Leases", accent_color=P.warning)   # amber-accented card listing tenants with soon-expiring leases
        cols = [
            ("Tenant", 150), ("NI Number", 100), ("Apartment", 80),
            ("City", 80), ("Lease End", 90), ("Status", 70),
        ]   # column names and pixel widths for the 6-column expiring leases table
        self._lease_tbl, self._lease_mdl = make_table(
            card.body_layout(), cols)   # creates the expiring leases table and stores references for reloading
        lay.addWidget(card, 1)   # adds the leases card to the layout, giving it all remaining vertical space

        self._reload_leases()   # populates the table immediately with the 30-day default

    def _set_lease_days(self, days, checked):
        if checked:
            self._lease_days = days   # updates the active expiry window to the newly selected day count
            self._reload_leases()   # reloads the table so only leases in the new window are shown

    def _reload_leases(self):
        days = self._lease_days   # reads the currently selected expiry window (30, 60, or 90 days)
        leases = db.get_expiring_leases(days, self._loc)   # fetches all tenants whose leases expire within the selected window
        table_clear(self._lease_mdl)   # clears all existing rows from the expiring leases table
        for t in leases:
            table_insert(self._lease_mdl, [
                t["full_name"],   # tenant's full name
                t["ni_number"],   # tenant's national insurance number
                t.get("apt_number") or "—",   # apartment number or dash if not linked
                t.get("location") or "—",   # city or dash if not linked
                fmt_date(t.get("lease_end")),   # lease end in UK DD/MM/YYYY format
                badge_text(t["status"]),   # wraps the tenant status in a badge-style label
            ], P.warning)   # inserts the row in amber to highlight the urgency of an expiring lease
        self._lease_summary_lbl.setText(
            f"{len(leases)} lease(s) expiring within {days} days")   # updates the summary label with the count and selected window
