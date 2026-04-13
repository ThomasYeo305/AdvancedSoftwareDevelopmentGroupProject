# ============================================================
# PAMS — views/maintenance_view.py
# Maintenance Request Management View (PySide6)
#
# Contributors (UI):
#   Chouaib Hakim       — Student ID: 24018717
#   Sinoli Rodrigo      — Student ID: 24055025
# ============================================================
from __future__ import annotations   # allows forward type hints
import datetime   # imported for potential date calculations (unused directly but kept for future use)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QRadioButton, QButtonGroup,
    QDialog, QMessageBox, QScrollArea, QFrame, QSplitter,   # QSplitter available for side-by-side panels
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..theme import PALETTE as P, FONTS as F, DIMS as D
from ..widgets import (
    qfont, Card, section_header, make_table, table_clear,
    table_insert, table_selected_id, badge_text, styled_button, Toast,
    PRIORITY_COLORS, STATUS_COLORS, fmt_date,   # PRIORITY_COLORS maps High/Medium/Low to red/amber/green; STATUS_COLORS maps Resolved to green etc.
)
from .. import database as db   # all maintenance, tenant and staff SQL queries


class MaintenanceView(QWidget):
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self._user = user   # full user dict for role and location checks
        self._loc = user.get("location")   # branch filter applied to all maintenance queries
        self._role = user["role"]   # stored separately to check if action buttons should be shown
        self._selected_id = None   # tracks the currently selected maintenance request row
        self._build()   # constructs toolbar, table and detail panel
        self._reload()   # loads all maintenance requests on first open

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        section_header(lay, "Maintenance Management",
                       "Log, prioritise, assign and resolve maintenance issues")   # page title bar

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(D.pad_lg, D.pad_sm, D.pad_lg, D.pad_sm)

        # Status filter
        self._filter_val = "All"   # default shows all statuses
        self._filter_group = QButtonGroup(self)   # groups status radios so only one is active
        for s in ["All", "Open", "Assigned", "Scheduled", "In Progress", "Resolved"]:
            rb = QRadioButton(s)
            rb.setStyleSheet(f"color: {P.text_secondary};")
            if s == "All":
                rb.setChecked(True)   # 'All' pre-selected on first open
            rb.toggled.connect(
                lambda checked, st=s: self._set_filter("status", st, checked))   # updates status filter on toggle
            self._filter_group.addButton(rb)
            toolbar.addWidget(rb)

        # Priority filter
        sep = QLabel("  Priority:")
        sep.setFont(qfont(F.small))
        sep.setStyleSheet(f"color: {P.text_muted};")   # muted separator label between the two filter groups
        toolbar.addWidget(sep)

        self._pri_val = "All"   # default shows all priority levels
        self._pri_group = QButtonGroup(self)   # groups priority radios separately from the status radios
        for p in ["All", "Critical", "High", "Medium", "Low"]:
            rb = QRadioButton(p)
            rb.setStyleSheet(f"color: {P.text_secondary};")
            if p == "All":
                rb.setChecked(True)
            rb.toggled.connect(
                lambda checked, pr=p: self._set_filter("priority", pr, checked))   # updates priority filter on toggle
            self._pri_group.addButton(rb)
            toolbar.addWidget(rb)

        toolbar.addStretch()   # pushes action buttons to the right

        btn_add = styled_button("+ Log Request", "danger")   # red button to open the new maintenance request dialog
        btn_add.clicked.connect(self._open_add)
        toolbar.addWidget(btn_add)

        if self._role in ("Maintenance Staff", "Administrator"):   # resolve/status/schedule only for maintenance staff and admins
            btn_resolve = styled_button("Resolve", "success")   # green button to mark the request as resolved with cost and notes
            btn_resolve.clicked.connect(self._open_resolve)
            toolbar.addWidget(btn_resolve)

            btn_status = styled_button("Update Status", "primary")   # indigo button to change the request's status stage
            btn_status.clicked.connect(self._update_status)
            toolbar.addWidget(btn_status)

            btn_sched = styled_button("Schedule & Notify", "warning")   # amber button to set a scheduled date and notify the tenant
            btn_sched.clicked.connect(self._schedule_notify)
            toolbar.addWidget(btn_sched)

        lay.addLayout(toolbar)

        # ── Body: table + detail panel ──
        body = QHBoxLayout()
        body.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_lg)
        body.setSpacing(D.pad_sm)

        # Table card
        card = Card(title="", accent_color=P.danger)   # red-accented card for the maintenance requests table
        cols = [
            ("#", 55), ("Issue", 160), ("Tenant", 120), ("Apt", 70),
            ("City", 80), ("Priority", 80), ("Status", 100),
            ("Assigned To", 130), ("Reported", 90), ("Scheduled", 90),
            ("Resolved", 90), ("Cost £", 70),   # 12 columns covering all key maintenance fields
        ]
        self._table, self._model = make_table(card.body_layout(), cols)   # styled read-only table
        self._table.clicked.connect(self._on_select)   # populates the detail panel when a row is clicked
        body.addWidget(card, 3)   # table takes 3 stretch units (wider)

        # Detail panel
        self._detail_card = Card(title="Request Detail", accent_color=P.danger)   # right-side detail panel with title
        self._detail_layout = self._detail_card.body_layout()   # vertical layout inside the detail panel rebuilt on each row click
        body.addWidget(self._detail_card, 1)   # detail panel takes 1 stretch unit (narrower)

        lay.addLayout(body, 1)   # body layout fills remaining vertical space

    def _set_filter(self, kind, val, checked):
        if not checked:
            return   # ignores the radio that was just unchecked
        if kind == "status":
            self._filter_val = val   # updates the status filter value
        else:
            self._pri_val = val   # updates the priority filter value
        self._reload()   # refreshes the table with the new combined filter

    def _reload(self):
        table_clear(self._model)   # removes all existing rows before repopulating
        items = db.get_all_maintenance(self._loc)   # fetches all maintenance requests for the branch
        filt = self._filter_val   # current status filter ('All', 'Open', 'In Progress', 'Resolved')
        pfilt = self._pri_val   # current priority filter ('All', 'High', 'Medium', 'Low')
        cnt = 0
        for m in items:
            if filt != "All" and m["status"] != filt:
                continue   # skips requests not matching the current status filter
            if pfilt != "All" and m["priority"] != pfilt:
                continue   # skips requests not matching the current priority filter
            cnt += 1
            pri = m["priority"]
            # Resolved items are always green; active items are coloured by priority for urgency
            if m["status"] == "Resolved":
                color = STATUS_COLORS.get("Resolved", P.success)
            else:
                color = PRIORITY_COLORS.get(pri, P.text_muted)   # row text colour based on priority (dark-red=Critical, red=High, amber=Medium, green=Low)
            table_insert(self._model, [
                str(cnt),
                m["title"],
                m.get("full_name") or "—",   # tenant name, dash if unlinked
                m.get("apt_number") or "—",   # apartment unit, dash if not set
                m.get("location") or "—",
                m["priority"],
                badge_text(m["status"]),   # badge symbol for Open/In Progress/Resolved
                m.get("staff_name") or "Unassigned",   # assigned staff name or 'Unassigned'
                fmt_date(m["reported_date"]),
                fmt_date(m.get("scheduled_date")),   # dash if no scheduled date set
                fmt_date(m.get("resolved_date")),   # dash if not yet resolved
                f"£{m.get('cost') or 0:,.0f}",   # maintenance cost formatted with £
            ], color, row_id=m["id"])   # stores DB id for selection
        self._selected_id = None   # clears selection after reload

    def _on_select(self, index):
        tid = table_selected_id(self._table, self._model, 0)   # reads the request ID from column 0
        if tid is None:
            return
        try:
            self._selected_id = int(tid)   # stores as integer for action button usage
        except ValueError:
            return

        # Populate detail panel
        while self._detail_layout.count():
            item = self._detail_layout.takeAt(0)   # removes all existing detail rows
            w = item.widget()
            if w:
                w.deleteLater()   # schedules old widgets for memory cleanup

        items = db.get_all_maintenance()   # fetches all maintenance records (no filter) to find the selected one
        m = next((x for x in items if x["id"] == self._selected_id), None)   # finds the dict for the selected ID
        if not m:
            return

        pri_color = PRIORITY_COLORS.get(m["priority"], P.accent)   # colour for the priority row in the detail panel
        details = [
            ("Issue",       m["title"],                     P.text_primary),
            ("Priority",    m["priority"],                   pri_color),   # priority shown in its own colour (red/amber/green)
            ("Status",      badge_text(m["status"]),         P.text_primary),
            ("Tenant",      m.get("full_name") or "—",      P.text_secondary),
            ("Reported",    fmt_date(m["reported_date"]),              P.text_secondary),
            ("Scheduled",   fmt_date(m.get("scheduled_date")), P.info),   # cyan for the scheduled date
            ("Notified",    "Yes" if m.get("communication_sent") else "No", P.info),   # shows whether tenant was notified
            ("Resolved",    fmt_date(m.get("resolved_date")),  P.text_secondary),
            ("Cost (£)",    f"£{m.get('cost') or 0:,.2f}",  P.warning),   # amber colour for cost
            ("Time (hrs)",  str(m.get("time_spent") or 0),  P.text_secondary),
            ("Assigned To", m.get("staff_name") or "—",     P.text_secondary),
        ]
        for label, value, color in details:
            row = QHBoxLayout()
            lbl = QLabel(f"{label}:")
            lbl.setFixedWidth(90)   # fixed 90px so all label text aligns consistently
            lbl.setFont(qfont(F.small_bold))
            lbl.setStyleSheet(f"color: {P.text_muted};")
            row.addWidget(lbl)
            vlbl = QLabel(str(value))
            vlbl.setFont(qfont(F.small))
            vlbl.setStyleSheet(f"color: {color};")   # each value displayed in its own designated colour
            vlbl.setWordWrap(True)   # allows long values to wrap within the detail panel width
            row.addWidget(vlbl, 1)   # value label stretches to fill remaining row width
            self._detail_layout.addLayout(row)

        if m.get("description"):
            div = QFrame()
            div.setFrameShape(QFrame.HLine)   # horizontal divider before the full description
            div.setStyleSheet(f"color: {P.divider};")
            self._detail_layout.addWidget(div)
            desc = QLabel(m["description"])
            desc.setFont(qfont(F.small))
            desc.setStyleSheet(f"color: {P.text_secondary};")
            desc.setWordWrap(True)   # wraps the full description text within the panel
            self._detail_layout.addWidget(desc)

        self._detail_layout.addStretch()   # pushes all detail rows to the top of the panel

    def _open_add(self):
        dlg = _MaintDialog(self)   # opens the 'Log Maintenance Request' dialog
        if dlg.exec() == QDialog.Accepted:
            self._reload()

    def _open_resolve(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a request first.")
            return
        dlg = _ResolveDialog(self, mid=self._selected_id)   # opens resize dialog for the selected request
        if dlg.exec() == QDialog.Accepted:
            self._reload()

    def _update_status(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a request first.")
            return
        dlg = _StatusDialog(self, mid=self._selected_id)   # opens the quick status change dropdown dialog
        if dlg.exec() == QDialog.Accepted:
            self._reload()

    def _schedule_notify(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a request first.")
            return
        dlg = _ScheduleDialog(self, mid=self._selected_id)   # opens the schedule date + notification dialog
        if dlg.exec() == QDialog.Accepted:
            self._reload()


# ──────────────────────────────────────────────────────────
# LOG MAINTENANCE DIALOG
# ──────────────────────────────────────────────────────────
class _MaintDialog(QDialog):   # popup dialog for logging a brand-new maintenance request
    def __init__(self, parent):
        super().__init__(parent)   # attaches this dialog to the parent window so it stays on top
        self.setWindowTitle("Log Maintenance Request")   # sets the dialog title in the OS title bar
        self.setMinimumSize(480, 540)   # prevents the dialog from being shrunk below 480×540 px
        self.resize(480, 540)   # opens the dialog at exactly 480 wide by 540 tall
        self._build()   # draws all the widgets inside the dialog

    def _build(self):
        lay = QVBoxLayout(self)   # stacks all dialog sections vertically
        lay.setSpacing(6)   # 6 px gap between each stacked section

        title = QLabel("Log Maintenance Request")   # big heading shown at the top of the dialog
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))   # 18pt bold heading font
        title.setStyleSheet(f"color: {P.text_primary};")   # colours the heading in the primary text colour
        title.setAlignment(Qt.AlignCenter)   # centres the heading horizontally
        lay.addWidget(title)   # adds the heading to the top of the dialog layout

        scroll = QScrollArea()   # wraps the form so it can scroll if content overflows
        scroll.setWidgetResizable(True)   # allows the inner form widget to resize with the scroll area
        scroll.setFrameShape(QFrame.NoFrame)   # removes the border around the scroll area
        form = QWidget()   # plain container widget that holds all form fields
        fl = QVBoxLayout(form)   # form fields stacked vertically inside the scroll container
        fl.setSpacing(4)   # 4 px gap between each field label-input pair

        # Tenant
        fl.addWidget(self._lbl("Tenant"))   # adds a grey "Tenant" section label above the dropdown
        tenants = db.get_all_tenants()   # fetches every tenant record from the database
        self._tenant_combo = QComboBox()   # dropdown for selecting which tenant raised the request
        self._tenant_combo.addItems(
            [f"{t['id']} — {t['full_name']}" for t in tenants])   # populates dropdown with "ID — Full Name" entries
        fl.addWidget(self._tenant_combo)   # adds the tenant dropdown to the form

        # Apartment
        fl.addWidget(self._lbl("Apartment"))   # adds a grey "Apartment" section label
        apts = db.get_all_apartments()   # fetches every apartment record from the database
        self._apt_combo = QComboBox()   # dropdown for selecting which apartment has the issue
        self._apt_combo.addItems(
            [f"{a['id']} — {a['apt_number']} ({a['location']})" for a in apts])   # formats each entry as "ID — AptNum (City)"
        fl.addWidget(self._apt_combo)   # adds the apartment dropdown to the form

        # Title
        fl.addWidget(self._lbl("Issue Title"))   # adds a grey "Issue Title" section label
        self._title_e = QLineEdit()   # single-line text input for the short issue title (required)
        self._title_e.setPlaceholderText("Brief description")   # ghost text shown when the field is empty
        self._title_e.setFixedHeight(38)   # fixes input height to 38 px to match other fields
        fl.addWidget(self._title_e)   # adds the title input to the form

        # Description
        fl.addWidget(self._lbl("Full Description"))   # adds a grey "Full Description" section label
        self._desc_e = QLineEdit()   # single-line input for a longer explanation of the issue
        self._desc_e.setPlaceholderText("Detailed description")   # ghost text shown when the field is empty
        self._desc_e.setFixedHeight(38)   # fixes input height to 38 px
        fl.addWidget(self._desc_e)   # adds the description input to the form

        # Priority
        fl.addWidget(self._lbl("Priority"))   # adds a grey "Priority" section label
        self._pri_combo = QComboBox()   # dropdown for selecting urgency level (Critical, High, Medium, Low)
        self._pri_combo.addItems(["Critical", "High", "Medium", "Low"])   # adds the four priority options
        self._pri_combo.setCurrentIndex(2)   # pre-selects "Medium" as the sensible default priority
        fl.addWidget(self._pri_combo)   # adds the priority dropdown to the form

        # Assign To
        fl.addWidget(self._lbl("Assign To"))   # adds a grey "Assign To" section label
        staff = db.get_maintenance_staff()   # fetches all maintenance staff records from the database
        self._staff_combo = QComboBox()   # dropdown for assigning the request to a specific staff member
        self._staff_combo.addItems(
            [f"{s[0]} — {s[1]}" for s in staff])   # formats each staff entry as "ID — Name"
        fl.addWidget(self._staff_combo)   # adds the staff assignment dropdown to the form

        # Scheduled Date
        fl.addWidget(self._lbl("Scheduled Date"))   # adds a grey "Scheduled Date" section label
        self._sched_e = QLineEdit()   # text input for entering an optional date to schedule the work
        self._sched_e.setPlaceholderText("YYYY-MM-DD (optional)")   # ghost text showing expected date format
        self._sched_e.setFixedHeight(38)   # fixes input height to 38 px
        fl.addWidget(self._sched_e)   # adds the scheduled date input to the form

        scroll.setWidget(form)   # inserts the form container inside the scroll area
        lay.addWidget(scroll, 1)   # adds the scroll area to the dialog, giving it all remaining vertical space

        btn_row = QHBoxLayout()   # horizontal row for the action buttons at the bottom
        btn_save = styled_button("Log Request", "danger")   # red "Log Request" button that triggers _save
        btn_save.setFixedHeight(42)   # fixes button height to 42 px
        btn_save.setFixedWidth(180)   # fixes button width to 180 px
        btn_save.clicked.connect(self._save)   # connects the button click to the _save method
        btn_row.addWidget(btn_save)   # adds the save button to the button row
        btn_cancel = styled_button("Cancel", "outline")   # outlined "Cancel" button that dismisses the dialog
        btn_cancel.setFixedHeight(42)   # fixes cancel button height to 42 px
        btn_cancel.setFixedWidth(120)   # fixes cancel button width to 120 px
        btn_cancel.clicked.connect(self.reject)   # clicking Cancel closes the dialog with Rejected result
        btn_row.addWidget(btn_cancel)   # adds the cancel button to the button row
        btn_row.addStretch()   # pushes both buttons to the left
        lay.addLayout(btn_row)   # adds the button row to the bottom of the dialog layout

    def _lbl(self, text):
        l = QLabel(text)   # creates a plain text label for a form section heading
        l.setFont(qfont(F.label))   # applies the standard label font size
        l.setStyleSheet(f"color: {P.text_secondary};")   # colours the label in the muted secondary text colour
        return l   # returns the ready-to-use label widget

    def _save(self):
        t_str = self._tenant_combo.currentText()   # reads the selected "ID — Name" string from the tenant dropdown
        a_str = self._apt_combo.currentText()   # reads the selected "ID — AptNum (City)" string from the apt dropdown
        title = self._title_e.text().strip()   # reads and trims the issue title from its input field
        desc = self._desc_e.text().strip()   # reads and trims the full description from its input field
        pri = self._pri_combo.currentText()   # reads the chosen priority text ("High", "Medium", or "Low")

        if not title:
            QMessageBox.critical(self, "Validation", "Issue title is required.")   # blocks save if no title was entered
            return
        try:
            tid = int(t_str.split("—")[0].strip()) if t_str else None   # parses the numeric tenant ID from before the "—"
            aid = int(a_str.split("—")[0].strip()) if a_str else None   # parses the numeric apartment ID from before the "—"
        except ValueError:
            tid = aid = None   # falls back to None if parsing fails (should not happen with valid combo data)

        s_str = self._staff_combo.currentText()   # reads the selected "ID — Name" string from the staff dropdown
        try:
            assigned = int(s_str.split("—")[0].strip()) if s_str else None   # parses the numeric staff ID from before the "—"
        except ValueError:
            assigned = None   # falls back to None if no staff is selected or parsing fails
        sched = self._sched_e.text().strip() or None   # reads the scheduled date, converting empty string to None
        db.add_maintenance(tid, aid, title, desc, pri, assigned, sched)   # inserts the new maintenance request into the database
        Toast(self.window(), "Maintenance request logged.")   # shows a brief success notification
        self.accept()   # closes the dialog with Accepted result, triggering a table reload in the parent


# ──────────────────────────────────────────────────────────
# RESOLVE DIALOG
# ──────────────────────────────────────────────────────────
class _ResolveDialog(QDialog):   # popup dialog for marking a maintenance request as resolved with cost, time, and notes
    def __init__(self, parent, mid: int):
        super().__init__(parent)   # attaches this dialog to the parent window
        self._mid = mid   # stores the maintenance request ID that is being resolved
        self.setWindowTitle("Resolve Request")   # sets the dialog title in the OS title bar
        self.setMinimumSize(400, 320)   # prevents the dialog from being shrunk below 400×320 px
        self.resize(400, 340)   # opens the dialog at 400 wide by 340 tall
        self._build()   # draws all the widgets inside the dialog

    def _build(self):
        lay = QVBoxLayout(self)   # stacks all dialog sections vertically
        lay.setSpacing(6)   # 6 px gap between each stacked section

        title = QLabel("Resolve Maintenance Request")   # bold heading shown at the top of the dialog
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))   # 16pt bold heading font
        title.setStyleSheet(f"color: {P.text_primary};")   # colours the heading in the primary text colour
        title.setAlignment(Qt.AlignCenter)   # centres the heading horizontally
        lay.addWidget(title)   # adds the heading to the top of the dialog layout

        for label, attr, ph in [
            ("Cost Incurred (£)", "_cost", "0.00"),
            ("Time Spent (hours)", "_time", "0.0"),
            ("Resolution Notes", "_notes", "What was done to fix the issue"),
        ]:   # loops over the 3 resolution fields: cost, time spent, and resolution notes
            lbl = QLabel(label)   # creates a grey label above each input field
            lbl.setFont(qfont(F.label))   # applies the standard label font size
            lbl.setStyleSheet(f"color: {P.text_secondary};")   # colours the label in the muted secondary text colour
            lay.addWidget(lbl)   # adds the section label to the layout
            e = QLineEdit()   # creates the text input for this field
            e.setPlaceholderText(ph)   # sets the ghost text hint shown when the field is empty
            e.setFixedHeight(38)   # fixes the input height to 38 px
            lay.addWidget(e)   # adds the input field to the layout
            setattr(self, attr, e)   # stores a reference to each input on self (_cost, _time, _notes)

        btn_row = QHBoxLayout()   # horizontal row for the action buttons at the bottom
        btn_save = styled_button("Mark Resolved", "success")   # green "Mark Resolved" button that triggers _save
        btn_save.setFixedHeight(42)   # fixes button height to 42 px
        btn_save.setFixedWidth(180)   # fixes button width to 180 px
        btn_save.clicked.connect(self._save)   # connects the button click to the _save method
        btn_row.addWidget(btn_save)   # adds the save button to the button row
        btn_cancel = styled_button("Cancel", "outline")   # outlined "Cancel" button that dismisses the dialog
        btn_cancel.setFixedHeight(42)   # fixes cancel button height to 42 px
        btn_cancel.setFixedWidth(120)   # fixes cancel button width to 120 px
        btn_cancel.clicked.connect(self.reject)   # clicking Cancel closes the dialog with Rejected result
        btn_row.addWidget(btn_cancel)   # adds the cancel button to the button row
        btn_row.addStretch()   # pushes both buttons to the left
        lay.addLayout(btn_row)   # adds the button row to the bottom of the dialog layout

    def _save(self):
        try:
            cost = float(self._cost.text() or 0)   # converts the cost field text to a float (0 if blank)
            time = float(self._time.text() or 0)   # converts the time field text to a float (0 if blank)
        except ValueError:
            QMessageBox.critical(self, "Validation",
                                 "Cost and Time must be numbers.")   # blocks save if non-numeric values were entered
            return
        notes = self._notes.text().strip()   # reads and trims the resolution notes text
        db.resolveIssue(self._mid, cost, time, notes)   # marks the request as resolved in the database with cost/time/notes
        Toast(self.window(), "Request resolved successfully!", kind="success")   # shows a green success notification
        self.accept()   # closes the dialog with Accepted result, triggering a table reload in the parent


# ──────────────────────────────────────────────────────────
# UPDATE STATUS DIALOG
# ──────────────────────────────────────────────────────────
class _StatusDialog(QDialog):   # small popup dialog for quickly changing the status of a maintenance request
    def __init__(self, parent, mid: int):
        super().__init__(parent)   # attaches this dialog to the parent window
        self._mid = mid   # stores the maintenance request ID whose status will be updated
        self.setWindowTitle("Update Status")   # sets the dialog title in the OS title bar
        self.setFixedSize(360, 200)   # locks the dialog to exactly 360×200 px (cannot be resized)
        self._build()   # draws all the widgets inside the dialog

    def _build(self):
        lay = QVBoxLayout(self)   # stacks the heading, dropdown, and button vertically
        lbl = QLabel("New Status")   # bold heading telling the user what the dropdown is for
        lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))   # 14pt bold heading font
        lbl.setStyleSheet(f"color: {P.text_primary};")   # colours the heading in the primary text colour
        lbl.setAlignment(Qt.AlignCenter)   # centres the heading horizontally
        lay.addWidget(lbl)   # adds the heading to the top of the dialog layout

        self._combo = QComboBox()   # dropdown listing all possible maintenance statuses
        self._combo.addItems(["Open", "Assigned", "Scheduled", "In Progress", "Resolved"])   # adds all five status options matching the DB CHECK constraint
        self._combo.setCurrentIndex(3)   # pre-selects "In Progress" as the most common next step
        lay.addWidget(self._combo)   # adds the status dropdown to the layout

        btn = styled_button("Apply", "primary")   # blue "Apply" button that triggers _apply
        btn.setFixedHeight(38)   # fixes the apply button height to 38 px
        btn.clicked.connect(self._apply)   # connects the button click to the _apply method
        lay.addWidget(btn)   # adds the apply button to the bottom of the layout

    def _apply(self):
        db.update_maintenance_status(self._mid, self._combo.currentText())   # saves the newly selected status to the database for this request
        Toast(self.window(),
              f"Status updated to '{self._combo.currentText()}'")   # shows a brief notification confirming the status change
        self.accept()   # closes the dialog with Accepted result, triggering a table reload in the parent


# ──────────────────────────────────────────────────────────
# SCHEDULE & NOTIFY DIALOG
# ──────────────────────────────────────────────────────────
class _ScheduleDialog(QDialog):   # popup dialog for setting a scheduled maintenance date and notifying the tenant
    def __init__(self, parent, mid: int):
        super().__init__(parent)   # attaches this dialog to the parent window
        self._mid = mid   # stores the maintenance request ID that is being scheduled
        self.setWindowTitle("Schedule & Notify Tenant")   # sets the dialog title in the OS title bar
        self.setMinimumSize(420, 300)   # prevents the dialog from being shrunk below 420×300 px
        self.resize(420, 320)   # opens the dialog at 420 wide by 320 tall
        self._build()   # draws all the widgets inside the dialog

    def _build(self):
        lay = QVBoxLayout(self)   # stacks all dialog sections vertically
        lay.setSpacing(6)   # 6 px gap between each stacked section

        title = QLabel("Schedule Maintenance")   # bold heading shown at the top of the dialog
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))   # 16pt bold heading font
        title.setStyleSheet(f"color: {P.text_primary};")   # colours the heading in the primary text colour
        title.setAlignment(Qt.AlignCenter)   # centres the heading horizontally
        lay.addWidget(title)   # adds the heading to the top of the dialog layout

        lbl1 = QLabel("Scheduled Date (YYYY-MM-DD)")   # grey label above the date input field
        lbl1.setFont(qfont(F.label))   # applies the standard label font size
        lbl1.setStyleSheet(f"color: {P.text_secondary};")   # colours the label in the muted secondary text colour
        lay.addWidget(lbl1)   # adds the date section label to the layout
        self._sched = QLineEdit()   # text input for the date the maintenance work is scheduled to happen
        self._sched.setPlaceholderText("YYYY-MM-DD")   # ghost text showing the expected date format
        self._sched.setFixedHeight(38)   # fixes the date input height to 38 px
        lay.addWidget(self._sched)   # adds the date input to the layout

        lbl2 = QLabel("Notes / Communication")   # grey label above the notes input field
        lbl2.setFont(qfont(F.label))   # applies the standard label font size
        lbl2.setStyleSheet(f"color: {P.text_secondary};")   # colours the label in the muted secondary text colour
        lay.addWidget(lbl2)   # adds the notes section label to the layout
        self._notes = QLineEdit()   # text input for any message or notes to communicate to the tenant
        self._notes.setPlaceholderText("Details to communicate to tenant")   # ghost text prompting what to write
        self._notes.setFixedHeight(38)   # fixes the notes input height to 38 px
        lay.addWidget(self._notes)   # adds the notes input to the layout

        btn_row = QHBoxLayout()   # horizontal row for the action buttons at the bottom
        btn_apply = styled_button("Schedule & Notify", "primary")   # blue "Schedule & Notify" button that triggers _apply
        btn_apply.setFixedHeight(42)   # fixes button height to 42 px
        btn_apply.setFixedWidth(200)   # fixes button width to 200 px
        btn_apply.clicked.connect(self._apply)   # connects the button click to the _apply method
        btn_row.addWidget(btn_apply)   # adds the primary button to the button row
        btn_cancel = styled_button("Cancel", "outline")   # outlined "Cancel" button that dismisses the dialog
        btn_cancel.setFixedHeight(42)   # fixes cancel button height to 42 px
        btn_cancel.setFixedWidth(120)   # fixes cancel button width to 120 px
        btn_cancel.clicked.connect(self.reject)   # clicking Cancel closes the dialog with Rejected result
        btn_row.addWidget(btn_cancel)   # adds the cancel button to the button row
        btn_row.addStretch()   # pushes both buttons to the left
        lay.addLayout(btn_row)   # adds the button row to the bottom of the dialog layout

    def _apply(self):
        sd = self._sched.text().strip()   # reads and trims the scheduled date from its input field
        if not sd:
            QMessageBox.critical(self, "Validation",
                                 "Scheduled date is required.")   # blocks save if no date was entered
            return
        notes = self._notes.text().strip()   # reads and trims the communication notes
        db.update_maintenance_schedule(self._mid, sd, notes)   # saves the scheduled date and notes to the database for this request
        Toast(self.window(), "Scheduled and tenant notified", kind="success")   # shows a green success notification
        self.accept()   # closes the dialog with Accepted result, triggering a table reload in the parent
