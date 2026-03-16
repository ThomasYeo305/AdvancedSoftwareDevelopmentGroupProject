# ============================================================
# PAMS — views/user_view.py
# User / Account Management View  (Administrator only)  (PySide6)
# ============================================================
from __future__ import annotations

import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QDialog, QMessageBox,
    QFrame, QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..theme import PALETTE as P, FONTS as F, DIMS as D, ROLE_COLORS
from ..widgets import (
    qfont, Card, section_header, make_table, table_clear,
    table_insert, table_selected_id, badge_text, styled_button, Toast,
    STATUS_COLORS,
)
from .. import database as db

ROLES = [
    "Administrator", "Manager",
    "Front-Desk Staff", "Finance Manager", "Maintenance Staff",
]

ROLE_RANK = {
    "Manager": 4,
    "Administrator": 3,
    "Finance Manager": 2,
    "Front-Desk Staff": 1,
    "Maintenance Staff": 1,
}


def _get_locations():
    locs = db.get_all_locations()
    return locs if locs else ["Bristol", "London", "Manchester", "Cardiff"]


def _validate_password(pw: str) -> str | None:
    if len(pw) < 6:
        return "Password must be at least 6 characters."
    if not re.search(r'[a-zA-Z]', pw):
        return "Password must contain at least one letter."
    if not re.search(r'\d', pw):
        return "Password must contain at least one digit."
    return None


class UserView(QWidget):
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self._user = user
        self._loc = user.get("location")
        self._selected_id: int | None = None
        self._build()
        self._reload()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        section_header(lay, "User Management",
                       "Create and manage system user accounts")

        # ── Toolbar ──
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(D.pad_lg, D.pad_sm, D.pad_lg, D.pad_sm)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search users…")
        self._search.setFixedWidth(220)
        self._search.setFixedHeight(36)
        self._search.textChanged.connect(lambda: self._reload())
        toolbar.addWidget(self._search)

        self._role_filter = QComboBox()
        self._role_filter.addItems(["All"] + ROLES)
        self._role_filter.setFixedWidth(180)
        self._role_filter.currentIndexChanged.connect(lambda: self._reload())
        toolbar.addWidget(self._role_filter)

        btn_add = styled_button("+ New User", "primary")
        btn_add.clicked.connect(self._open_add)
        toolbar.addWidget(btn_add)

        btn_edit = styled_button("Edit", "outline")
        btn_edit.clicked.connect(self._open_edit)
        toolbar.addWidget(btn_edit)

        btn_deact = styled_button("Deactivate", "danger")
        btn_deact.clicked.connect(self._deactivate)
        toolbar.addWidget(btn_deact)

        toolbar.addStretch()
        self._count_lbl = QLabel("")
        self._count_lbl.setFont(qfont(F.small))
        self._count_lbl.setStyleSheet(f"color: {P.text_muted};")
        toolbar.addWidget(self._count_lbl)
        lay.addLayout(toolbar)

        # ── Role summary strip ──
        self._role_strip_container = QWidget()
        self._role_strip_lay = QHBoxLayout(self._role_strip_container)
        self._role_strip_lay.setContentsMargins(D.pad_lg, 0, D.pad_lg, D.pad_sm)
        self._role_strip_lay.setSpacing(D.pad_xs)
        lay.addWidget(self._role_strip_container)

        # ── Table ──
        card = Card(title="", accent_color=P.accent2)
        cols = [
            ("#", 40), ("Username", 120), ("Full Name", 170),
            ("Role", 140), ("Location", 90), ("Email", 170),
            ("Active", 55), ("Created", 90),
        ]
        self._table, self._model = make_table(card.body_layout(), cols)
        self._table.clicked.connect(self._on_select)
        lay.addWidget(card, 1)

    def _reload(self):
        # Role summary strip
        while self._role_strip_lay.count():
            item = self._role_strip_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        all_users = db.get_all_users()
        role_counts: dict[str, int] = {}
        for u in all_users:
            if u["active"]:
                role_counts[u["role"]] = role_counts.get(u["role"], 0) + 1
        for role, count in sorted(role_counts.items()):
            color = ROLE_COLORS.get(role, P.accent)
            box = QFrame()
            box.setStyleSheet(
                f"background: {P.bg_card}; border-radius: 6px; padding: 4px 8px;")
            bl = QHBoxLayout(box)
            bl.setContentsMargins(6, 2, 6, 2)
            bl.setSpacing(4)
            clbl = QLabel(str(count))
            clbl.setFont(qfont(F.h4))
            clbl.setStyleSheet(f"color: {color};")
            bl.addWidget(clbl)
            rlbl = QLabel(role)
            rlbl.setFont(qfont(F.small))
            rlbl.setStyleSheet(f"color: {P.text_secondary};")
            bl.addWidget(rlbl)
            self._role_strip_lay.addWidget(box)
        self._role_strip_lay.addStretch()

        # Table
        table_clear(self._model)
        q = self._search.text().lower()
        rf = self._role_filter.currentText()
        cnt = 0
        for u in db.get_all_users():
            if not u["active"]:
                continue
            if q and q not in (u["full_name"] + u["username"]).lower():
                continue
            if rf != "All" and u["role"] != rf:
                continue
            color = ROLE_COLORS.get(u["role"], P.accent)
            table_insert(self._model, [
                str(u["id"]),
                u["username"],
                u["full_name"],
                u["role"],
                u["location"],
                u.get("email") or "—",
                "✔" if u["active"] else "✗",
                (u.get("created_at") or "")[:10],
            ], color)
            cnt += 1
        self._count_lbl.setText(f"{cnt} user(s)")
        self._selected_id = None

    def _on_select(self, index):
        tid = table_selected_id(self._table, self._model, 0)
        if tid is None:
            return
        try:
            self._selected_id = int(tid)
        except ValueError:
            pass

    def _open_add(self):
        dlg = _UserDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._reload()

    def _open_edit(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a user first.")
            return
        users = db.get_all_users()
        user = next((u for u in users if u["id"] == self._selected_id), None)
        if user:
            dlg = _UserDialog(self, user=user)
            if dlg.exec() == QDialog.Accepted:
                self._reload()

    def _deactivate(self):
        if not self._selected_id:
            QMessageBox.warning(self, "Selection", "Select a user first.")
            return
        if self._selected_id == self._user["id"]:
            QMessageBox.critical(self, "Error",
                                 "Cannot deactivate your own account.")
            return
        all_users = db.get_all_users()
        target = next(
            (u for u in all_users if u["id"] == self._selected_id), None)
        if target:
            actor_rank = ROLE_RANK.get(self._user["role"], 0)
            target_rank = ROLE_RANK.get(target["role"], 0)
            if target_rank >= actor_rank:
                QMessageBox.critical(
                    self, "Permission Denied",
                    f"You cannot deactivate a '{target['role']}' account.\n"
                    f"That role has equal or higher authority than yours.")
                return
        ans = QMessageBox.question(self, "Confirm",
                                   "Deactivate this account?")
        if ans == QMessageBox.Yes:
            db.delete_user(self._selected_id)
            self._reload()
            Toast(self.window(), "User deactivated.", kind="info")


# ──────────────────────────────────────────────────────
# USER ADD / EDIT DIALOG
# ──────────────────────────────────────────────────────
class _UserDialog(QDialog):
    def __init__(self, parent, user=None):
        super().__init__(parent)
        self._user_data = user
        self.setWindowTitle("Edit User" if user else "New User")
        self.setMinimumSize(480, 560)
        self.resize(480, 580)
        self._build()
        if user:
            self._populate(user)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(6)

        title = QLabel("Edit User" if self._user_data else "Create New User")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet(f"color: {P.text_primary};")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        # Scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        form_w = QWidget()
        form = QVBoxLayout(form_w)
        form.setSpacing(4)
        scroll.setWidget(form_w)
        lay.addWidget(scroll, 1)

        # Username
        form.addWidget(self._lbl("Username"))
        self._username = QLineEdit()
        self._username.setPlaceholderText("e.g. jsmith")
        self._username.setFixedHeight(38)
        form.addWidget(self._username)

        # Full Name
        form.addWidget(self._lbl("Full Name"))
        self._fullname = QLineEdit()
        self._fullname.setPlaceholderText("First Last")
        self._fullname.setFixedHeight(38)
        form.addWidget(self._fullname)

        # Email
        form.addWidget(self._lbl("Email"))
        self._email = QLineEdit()
        self._email.setPlaceholderText("user@paragon.co.uk")
        self._email.setFixedHeight(38)
        form.addWidget(self._email)

        # Role
        form.addWidget(self._lbl("Role"))
        self._role_combo = QComboBox()
        self._role_combo.addItems(ROLES)
        form.addWidget(self._role_combo)

        # Location
        form.addWidget(self._lbl("Location"))
        self._loc_combo = QComboBox()
        self._loc_combo.addItems(_get_locations())
        form.addWidget(self._loc_combo)

        # Password
        pw_label = ("Password (leave blank = no change)"
                    if self._user_data else "Password")
        form.addWidget(self._lbl(pw_label))
        self._password = QLineEdit()
        self._password.setPlaceholderText("••••••••")
        self._password.setEchoMode(QLineEdit.Password)
        self._password.setFixedHeight(38)
        form.addWidget(self._password)

        # Active checkbox (edit only)
        if self._user_data:
            self._active_cb = QCheckBox("Account active")
            self._active_cb.setChecked(True)
            form.addWidget(self._active_cb)
        else:
            self._active_cb = None

        form.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_save = styled_button("Save User", "primary")
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

    def _populate(self, u: dict):
        self._username.setText(u.get("username", ""))
        self._fullname.setText(u.get("full_name", ""))
        self._email.setText(u.get("email", ""))
        idx = self._role_combo.findText(u.get("role", ""))
        if idx >= 0:
            self._role_combo.setCurrentIndex(idx)
        lidx = self._loc_combo.findText(u.get("location", ""))
        if lidx >= 0:
            self._loc_combo.setCurrentIndex(lidx)
        if self._active_cb:
            self._active_cb.setChecked(bool(u.get("active", 1)))

    def _save(self):
        username = self._username.text().strip()
        fullname = self._fullname.text().strip()
        email = self._email.text().strip()
        role = self._role_combo.currentText()
        location = self._loc_combo.currentText()
        password = self._password.text().strip()

        if not username or not fullname:
            QMessageBox.critical(self, "Validation",
                                 "Username and Full Name are required.")
            return

        if self._user_data:
            active = self._active_cb.isChecked() if self._active_cb else True
            if password:
                pw_err = _validate_password(password)
                if pw_err:
                    QMessageBox.critical(self, "Validation", pw_err)
                    return
                db.updateUserPassword(self._user_data["id"], password)
            db.update_user(self._user_data["id"],
                           fullname, role, location, email,
                           1 if active else 0)
            msg = "User updated."
        else:
            if not password:
                QMessageBox.critical(self, "Validation",
                                     "Password is required.")
                return
            pw_err = _validate_password(password)
            if pw_err:
                QMessageBox.critical(self, "Validation", pw_err)
                return
            db.add_user(username, password, fullname, role, location, email)
            msg = "User created."

        Toast(self.window(), msg)
        self.accept()
