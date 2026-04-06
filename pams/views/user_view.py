# ============================================================
# PAMS — views/user_view.py
# User / Account Management View  (Administrator only)  (PySide6)
# ============================================================
from __future__ import annotations   # enables forward-reference type hints without quote wrapping

import re   # used by _validate_password to check letter and digit requirements via regex

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QDialog, QMessageBox,
    QFrame, QScrollArea,
)   # all Qt widget and layout classes needed for the user management screen and dialog
from PySide6.QtCore import Qt   # Qt alignment and window flag constants
from PySide6.QtGui import QFont   # QFont used for bold headings in the dialog

from ..theme import PALETTE as P, FONTS as F, DIMS as D, ROLE_COLORS   # P = brand colours, F = font sizes, D = spacing, ROLE_COLORS = per-role accent colours
from ..widgets import (
    qfont, Card, section_header, make_table, table_clear,
    table_insert, table_selected_id, badge_text, styled_button, Toast,
    STATUS_COLORS,
)   # shared UI helpers: card panel, table factory, toast notification, badge formatter, role colour map
from .. import database as db   # all database operations for user accounts (get, add, update, delete)

ROLES = [
    "Administrator", "Manager",
    "Front-Desk Staff", "Finance Manager", "Maintenance Staff",
]   # complete list of valid PAMS roles shown in the role dropdown when creating or editing a user

ROLE_RANK = {
    "Manager": 4,
    "Administrator": 3,
    "Finance Manager": 2,
    "Front-Desk Staff": 1,
    "Maintenance Staff": 1,
}   # numeric rank per role; checked in _deactivate to prevent lower-ranked staff from deactivating higher-ranked accounts


def _get_locations():
    locs = db.get_all_locations()   # fetches all city names that currently exist in the database
    return locs if locs else ["Bristol", "London", "Manchester", "Cardiff"]   # falls back to 4 default cities if the DB returns nothing


def _validate_password(pw: str) -> str | None:
    if len(pw) < 6:
        return "Password must be at least 6 characters."   # rejects passwords shorter than 6 characters
    if not re.search(r'[a-zA-Z]', pw):
        return "Password must contain at least one letter."   # rejects passwords with no alphabetic character
    if not re.search(r'\d', pw):
        return "Password must contain at least one digit."   # rejects passwords with no numeric digit
    return None   # returns None to signal the password passes all three rules


class UserView(QWidget):   # administrator-only panel for viewing, adding, editing, and deactivating user accounts
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)   # registers this widget with Qt's parent-child ownership system
        self._user = user   # stores the logged-in user dict (used to block self-deactivation and rank checks)
        self._loc = user.get("location")   # stores the admin's branch city (used to scope some queries)
        self._selected_id: int | None = None   # tracks which user row is currently highlighted (None = none selected)
        self._build()   # constructs all child widgets and layouts
        self._reload()   # fetches user data from the DB and populates the table and role strip

    def _build(self):
        lay = QVBoxLayout(self)   # stacks the header, toolbar, role strip, and table vertically
        lay.setContentsMargins(0, 0, 0, 0)   # removes outer padding so the view fills its container edge-to-edge
        lay.setSpacing(8)   # 8 px gap between each stacked section

        section_header(lay, "User Management",
                       "Create and manage system user accounts")   # adds the styled page title and subtitle strip

        # ── Toolbar ──
        toolbar = QHBoxLayout()   # lays out the search box, role filter, and action buttons side by side
        toolbar.setContentsMargins(D.pad_lg, D.pad_sm, D.pad_lg, D.pad_sm)   # horizontal and vertical padding for the toolbar

        self._search = QLineEdit()   # text box for filtering the user table by name or username
        self._search.setPlaceholderText("Search users…")   # ghost text shown when the search field is empty
        self._search.setFixedWidth(220)   # fixes the search box width to 220 px
        self._search.setFixedHeight(36)   # fixes the search box height to 36 px
        self._search.textChanged.connect(lambda: self._reload())   # re-filters the table on every keystroke
        toolbar.addWidget(self._search)   # adds the search box to the toolbar

        self._role_filter = QComboBox()   # dropdown for filtering the table to a single role
        self._role_filter.addItems(["All"] + ROLES)   # first option is "All" (no filtering), followed by each role
        self._role_filter.setFixedWidth(180)   # fixes the role filter dropdown width to 180 px
        self._role_filter.currentIndexChanged.connect(lambda: self._reload())   # reloads the table when a different role is selected
        toolbar.addWidget(self._role_filter)   # adds the role filter dropdown to the toolbar

        btn_add = styled_button("+ New User", "primary")   # blue "New User" button for creating a new account
        btn_add.clicked.connect(self._open_add)   # opens the New User dialog when clicked
        toolbar.addWidget(btn_add)   # adds the new user button to the toolbar

        btn_edit = styled_button("Edit", "outline")   # outlined "Edit" button for modifying the selected user
        btn_edit.clicked.connect(self._open_edit)   # opens the Edit User dialog when clicked
        toolbar.addWidget(btn_edit)   # adds the edit button to the toolbar

        btn_deact = styled_button("Deactivate", "danger")   # red "Deactivate" button for disabling the selected account
        btn_deact.clicked.connect(self._deactivate)   # triggers the deactivation flow when clicked
        toolbar.addWidget(btn_deact)   # adds the deactivate button to the toolbar

        toolbar.addStretch()   # pushes all buttons to the left and count label to the right
        self._count_lbl = QLabel("")   # small muted label showing how many users match the current filter
        self._count_lbl.setFont(qfont(F.small))   # applies the small font size to the count label
        self._count_lbl.setStyleSheet(f"color: {P.text_muted};")   # colours the count label in the muted text colour
        toolbar.addWidget(self._count_lbl)   # adds the count label to the far right of the toolbar
        lay.addLayout(toolbar)   # adds the toolbar row to the main vertical layout

        # ── Role summary strip ──
        self._role_strip_container = QWidget()   # invisible container for the per-role count boxes
        self._role_strip_lay = QHBoxLayout(self._role_strip_container)   # lays the role count boxes side by side
        self._role_strip_lay.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_sm)   # horizontal and bottom padding for the role strip
        self._role_strip_lay.setSpacing(D.pad_xs)   # tiny gap between each role count box
        lay.addWidget(self._role_strip_container)   # adds the role strip container to the main layout

        # ── Table ──
        card = Card(title="", accent_color=P.accent2)   # secondary-accent coloured card holding the users table
        cols = [
            ("#", 40), ("Username", 120), ("Full Name", 170),
            ("Role", 140), ("Location", 90), ("Email", 170),
            ("Active", 55), ("Created", 90),
        ]   # column name and pixel-width pairs for the 8-column users table
        self._table, self._model = make_table(card.body_layout(), cols)   # creates the table widget and data model inside the card
        self._table.clicked.connect(self._on_select)   # fires _on_select whenever the user clicks a row
        lay.addWidget(card, 1)   # adds the users card to the layout, giving it all remaining vertical space

    def _reload(self):
        # Role summary strip
        while self._role_strip_lay.count():
            item = self._role_strip_lay.takeAt(0)   # removes the first item from the role strip repeatedly until empty
            w = item.widget()
            if w:
                w.deleteLater()   # schedules old role box widgets for deletion to free memory

        all_users = db.get_all_users()   # fetches every user record from the database
        role_counts: dict[str, int] = {}   # accumulator dict mapping role name → count of active users in that role
        for u in all_users:
            if u["active"]:
                role_counts[u["role"]] = role_counts.get(u["role"], 0) + 1   # increments the count for this user's role
        for role, count in sorted(role_counts.items()):
            color = ROLE_COLORS.get(role, P.accent)   # looks up the brand colour for this role
            box = QFrame()   # card-style container for one role's count and label
            box.setStyleSheet(
                f"background: {P.bg_card}; border-radius: 6px; padding: 4px 8px;")   # rounds the box with card background
            bl = QHBoxLayout(box)   # lays the count number and role label side by side inside the box
            bl.setContentsMargins(6, 2, 6, 2)   # tight inner padding for the role count box
            bl.setSpacing(4)   # 4 px gap between the count and label
            clbl = QLabel(str(count))   # large coloured number showing how many active users have this role
            clbl.setFont(qfont(F.h4))   # applies the h4 heading font to make the count stand out
            clbl.setStyleSheet(f"color: {color};")   # colours the count in the role's brand colour
            bl.addWidget(clbl)   # adds the count label to the box
            rlbl = QLabel(role)   # secondary label showing the role name next to the count
            rlbl.setFont(qfont(F.small))   # applies the small font to the role name label
            rlbl.setStyleSheet(f"color: {P.text_secondary};")   # colours the role name in secondary text colour
            bl.addWidget(rlbl)   # adds the role name label to the box
            self._role_strip_lay.addWidget(box)   # adds this role's count box to the strip
        self._role_strip_lay.addStretch()   # pushes all role boxes to the left

        # Table
        table_clear(self._model)   # clears all existing rows from the user table
        q = self._search.text().lower()   # reads and lowercases the search query for case-insensitive matching
        rf = self._role_filter.currentText()   # reads the currently selected role filter
        cnt = 0   # counter tracking how many users pass both filters
        for u in db.get_all_users():
            if not u["active"]:
                continue   # skips deactivated accounts (they are never shown in the active table)
            if q and q not in (u["full_name"] + u["username"]).lower():
                continue   # skips users whose name and username don't contain the search query
            if rf != "All" and u["role"] != rf:
                continue   # skips users whose role doesn't match the active role filter
            color = ROLE_COLORS.get(u["role"], P.accent)   # looks up the row colour based on the user's role
            table_insert(self._model, [
                str(u["id"]),
                u["username"],
                u["full_name"],
                u["role"],
                u["location"],
                u.get("email") or "—",   # shows email or a dash if not set
                "YES" if u["active"] else "NO",   # shows active status as "YES" or "NO"
                (u.get("created_at") or "")[:10],   # shows only the YYYY-MM-DD portion of the creation date
            ], color)   # inserts this user row with its role colour
            cnt += 1   # increments the visible row counter
        self._count_lbl.setText(f"{cnt} user(s)")   # updates the count label with how many users are visible
        self._selected_id = None   # clears the selection after a reload

    def _on_select(self, index):
        tid = table_selected_id(self._table, self._model, 0)   # reads the user ID from column 0 of the clicked row
        if tid is None:
            return   # exits early if no row ID could be read
        try:
            self._selected_id = int(tid)   # converts the ID string to an integer and stores it for action methods
        except ValueError:
            pass   # silently ignores if parsing fails (should not happen with valid table data)

    def _open_add(self):
        dlg = _UserDialog(self)   # opens the New User dialog (no user data = create mode)
        if dlg.exec() == QDialog.Accepted:
            self._reload()   # refreshes the table if a new user was successfully created

    def _open_edit(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a user first.")   # blocks edit if no row is selected
            return
        users = db.get_all_users()   # fetches all user records to find the selected one
        user = next((u for u in users if u["id"] == self._selected_id), None)   # finds the dict for this specific user ID
        if user:
            dlg = _UserDialog(self, user=user)   # opens the Edit User dialog pre-populated with this user's data
            if dlg.exec() == QDialog.Accepted:
                self._reload()   # refreshes the table if the user was successfully updated

    def _deactivate(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a user first.")   # blocks deactivation if no row is selected
            return
        if self._selected_id == self._user["id"]:
            QMessageBox.critical(self, "Error",
                                 "Cannot deactivate your own account.")   # prevents the logged-in admin from deactivating themselves
            return
        all_users = db.get_all_users()   # fetches all users to look up the target account's role rank
        target = next(
            (u for u in all_users if u["id"] == self._selected_id), None)   # finds the dict for the selected user
        if target:
            actor_rank = ROLE_RANK.get(self._user["role"], 0)   # looks up the numeric rank of the logged-in user's role
            target_rank = ROLE_RANK.get(target["role"], 0)   # looks up the numeric rank of the target account's role
            if target_rank >= actor_rank:
                QMessageBox.critical(
                    self, "Permission Denied",
                    f"You cannot deactivate a '{target['role']}' account.\n"
                    f"That role has equal or higher authority than yours.")   # blocks deactivation if the target's rank is equal or higher
                return
        ans = QMessageBox.question(self, "Confirm",
                                   "Deactivate this account?")   # shows a Yes/No confirmation dialog before deactivation
        if ans == QMessageBox.Yes:
            db.delete_user(self._selected_id)   # marks the selected user account as inactive in the database
            self._reload()   # refreshes the table to remove the deactivated account
            Toast(self.window(), "User deactivated.", kind="info")   # shows a brief info notification


# ──────────────────────────────────────────────────────
# USER ADD / EDIT DIALOG
# ──────────────────────────────────────────────────────
class _UserDialog(QDialog):   # popup dialog for creating a new user account or editing an existing one
    def __init__(self, parent, user=None):
        super().__init__(parent)   # attaches this dialog to the parent window so it stays on top
        self._user_data = user   # stores the existing user dict in edit mode, or None in create mode
        self.setWindowTitle("Edit User" if user else "New User")   # sets the title bar text based on mode
        self.setMinimumSize(480, 560)   # prevents the dialog from being shrunk below 480×560 px
        self.resize(480, 580)   # opens the dialog at 480 wide by 580 tall
        self._build()   # draws all the form fields and buttons
        if user:
            self._populate(user)   # pre-fills all fields with the existing user's data when in edit mode

    def _build(self):
        lay = QVBoxLayout(self)   # stacks the heading, scroll form, and button row vertically
        lay.setSpacing(6)   # 6 px gap between each stacked section

        title = QLabel("Edit User" if self._user_data else "Create New User")   # heading label showing which mode the dialog is in
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))   # 18pt bold heading font
        title.setStyleSheet(f"color: {P.text_primary};")   # colours the heading in the primary text colour
        title.setAlignment(Qt.AlignCenter)   # centres the heading horizontally
        lay.addWidget(title)   # adds the heading to the top of the dialog layout

        # Scrollable form
        scroll = QScrollArea()   # wraps the form so it can scroll if the dialog is resized smaller
        scroll.setWidgetResizable(True)   # allows the inner form widget to resize with the scroll area
        scroll.setStyleSheet("QScrollArea{border:none;}")   # removes the border around the scroll area
        form_w = QWidget()   # plain container widget that holds all form fields
        form = QVBoxLayout(form_w)   # stacks all form fields vertically inside the scroll container
        form.setSpacing(4)   # 4 px gap between each label-input pair
        scroll.setWidget(form_w)   # inserts the form container inside the scroll area
        lay.addWidget(scroll, 1)   # adds the scroll area to the dialog, giving it all remaining vertical space

        # Username
        form.addWidget(self._lbl("Username"))   # adds a grey "Username" section label
        self._username = QLineEdit()   # text input for the user's login username
        self._username.setPlaceholderText("e.g. jsmith")   # ghost text showing the expected format
        self._username.setFixedHeight(38)   # fixes the username input height to 38 px
        form.addWidget(self._username)   # adds the username input to the form

        # Full Name
        form.addWidget(self._lbl("Full Name"))   # adds a grey "Full Name" section label
        self._fullname = QLineEdit()   # text input for the user's display name
        self._fullname.setPlaceholderText("First Last")   # ghost text showing the expected format
        self._fullname.setFixedHeight(38)   # fixes the full name input height to 38 px
        form.addWidget(self._fullname)   # adds the full name input to the form

        # Email
        form.addWidget(self._lbl("Email"))   # adds a grey "Email" section label
        self._email = QLineEdit()   # text input for the user's email address
        self._email.setPlaceholderText("user@paragon.co.uk")   # ghost text showing the expected email format
        self._email.setFixedHeight(38)   # fixes the email input height to 38 px
        form.addWidget(self._email)   # adds the email input to the form

        # Role
        form.addWidget(self._lbl("Role"))   # adds a grey "Role" section label
        self._role_combo = QComboBox()   # dropdown for assigning one of the five PAMS roles to this user
        self._role_combo.addItems(ROLES)   # populates the dropdown with all valid role names
        form.addWidget(self._role_combo)   # adds the role dropdown to the form

        # Location
        form.addWidget(self._lbl("Location"))   # adds a grey "Location" section label
        self._loc_combo = QComboBox()   # dropdown for assigning this user to a branch city
        self._loc_combo.addItems(_get_locations())   # populates with all cities from the DB (or 4 defaults)
        form.addWidget(self._loc_combo)   # adds the location dropdown to the form

        # Password
        pw_label = ("Password (leave blank = no change)"
                    if self._user_data else "Password")   # label changes in edit mode to indicate blank keeps existing password
        form.addWidget(self._lbl(pw_label))   # adds the contextual password section label
        self._password = QLineEdit()   # masked text input for the user's password
        self._password.setPlaceholderText("••••••••")   # ghost text using bullet characters to hint at masking
        self._password.setEchoMode(QLineEdit.Password)   # hides typed characters so the password is not visible on screen
        self._password.setFixedHeight(38)   # fixes the password input height to 38 px
        form.addWidget(self._password)   # adds the password input to the form

        # Active checkbox (edit only)
        if self._user_data:
            self._active_cb = QCheckBox("Account active")   # checkbox shown only in edit mode to toggle account active state
            self._active_cb.setChecked(True)   # pre-checks the box so the account remains active unless explicitly unchecked
            form.addWidget(self._active_cb)   # adds the active checkbox to the form
        else:
            self._active_cb = None   # create mode: no active checkbox (new accounts are always active)

        form.addStretch()   # pushes all form fields to the top

        # Buttons
        btn_row = QHBoxLayout()   # horizontal row for the action buttons at the bottom
        btn_save = styled_button("Save User", "primary")   # blue "Save User" button that triggers _save
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

    def _populate(self, u: dict):
        self._username.setText(u.get("username", ""))   # pre-fills the username field with the existing value
        self._fullname.setText(u.get("full_name", ""))   # pre-fills the full name field with the existing value
        self._email.setText(u.get("email", ""))   # pre-fills the email field with the existing value
        idx = self._role_combo.findText(u.get("role", ""))   # finds the index of the existing role in the dropdown
        if idx >= 0:
            self._role_combo.setCurrentIndex(idx)   # selects the existing role in the dropdown
        lidx = self._loc_combo.findText(u.get("location", ""))   # finds the index of the existing city in the dropdown
        if lidx >= 0:
            self._loc_combo.setCurrentIndex(lidx)   # selects the existing city in the dropdown
        if self._active_cb:
            self._active_cb.setChecked(bool(u.get("active", 1)))   # checks or unchecks the active box based on the existing active flag

    def _save(self):
        username = self._username.text().strip()   # reads and trims the username from its input field
        fullname = self._fullname.text().strip()   # reads and trims the full name from its input field
        email = self._email.text().strip()   # reads and trims the email from its input field
        role = self._role_combo.currentText()   # reads the selected role from the dropdown
        location = self._loc_combo.currentText()   # reads the selected city from the dropdown
        password = self._password.text().strip()   # reads and trims the password from its input field (may be blank in edit mode)

        if not username or not fullname:
            QMessageBox.critical(self, "Validation",
                                 "Username and Full Name are required.")   # blocks save if either required field is empty
            return

        if self._user_data:
            active = self._active_cb.isChecked() if self._active_cb else True   # reads the active checkbox state (True if not shown)
            if password:
                pw_err = _validate_password(password)   # validates the new password against the 3-rule policy
                if pw_err:
                    QMessageBox.critical(self, "Validation", pw_err)   # shows the specific validation failure message
                    return
                db.updateUserPassword(self._user_data["id"], password)   # updates the password in the database for this user
            db.update_user(self._user_data["id"],
                           fullname, role, location, email,
                           1 if active else 0)   # writes the updated profile fields (name, role, city, email, active flag) to the database
            msg = "User updated."   # confirmation message for a successful edit
        else:
            if not password:
                QMessageBox.critical(self, "Validation",
                                     "Password is required.")   # blocks create if no password was entered
                return
            pw_err = _validate_password(password)   # validates the new password against the 3-rule policy
            if pw_err:
                QMessageBox.critical(self, "Validation", pw_err)   # shows the specific validation failure message
                return
            db.add_user(username, password, fullname, role, location, email)   # inserts the brand-new user record into the database
            msg = "User created."   # confirmation message for a successful creation

        Toast(self.window(), msg)   # shows a brief success notification with "User updated." or "User created."
        self.accept()   # closes the dialog with Accepted result, triggering a table reload in the parent
