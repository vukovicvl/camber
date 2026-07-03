"""Preview dialog for 'Import from sensor file...'.

Shows what camber-convert detected (layout, profile, delimiter/decimal), any
locale warnings, and the first few rows exactly as they will be stored -- so a
wrong decimal separator or day/month order is caught by eye before ~millions of
rows are written. Also lets the user send the readings into a new asset or an
existing one.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..integrations.sensor_import import ImportPreview

_NEW_ASSET = -1  # sentinel userData for the "create new asset" combo entry


class ImportPreviewDialog(QDialog):
    def __init__(self, preview: ImportPreview, assets: list[dict], parent=None):
        super().__init__(parent)
        self.preview = preview
        self.setWindowTitle("Import sensor file")
        self.setMinimumWidth(680)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        # --- what was detected -------------------------------------------------
        summary = QLabel(
            f"Detected a <b>{preview.kind}</b> file"
            + (f" (profile <b>{preview.profile_name}</b>)" if preview.profile_name else "")
            + f" — delimiter <b>{_show(preview.delimiter)}</b>, "
            f"decimal <b>{_show(preview.decimal)}</b>, "
            f"<b>{preview.sensor_count}</b> channel(s)."
        )
        summary.setTextFormat(Qt.RichText)
        summary.setWordWrap(True)
        root.addWidget(summary)

        # --- warnings ----------------------------------------------------------
        for w in preview.warnings:
            warn = QLabel("⚠  " + w)
            warn.setWordWrap(True)
            warn.setStyleSheet("color: #f0b429;")  # amber; theme-neutral
            root.addWidget(warn)

        # --- preview table -----------------------------------------------------
        root.addWidget(QLabel("First rows, as they will be stored:"))
        table = QTableWidget()
        cols = ["timestamp", "sensor_id", "metric_type", "value", "unit"]
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setRowCount(len(preview.preview_rows))
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        for r, row in enumerate(preview.preview_rows):
            for c, key in enumerate(cols):
                table.setItem(r, c, QTableWidgetItem(str(row.get(key, ""))))
        table.resizeColumnsToContents()
        table.setMaximumHeight(200)
        root.addWidget(table)

        if not preview.preview_rows:
            empty = QLabel("No readings were parsed from the first rows "
                           "(all blank or sentinel values?).")
            empty.setObjectName("labelMuted")
            empty.setWordWrap(True)
            root.addWidget(empty)

        # --- destination -------------------------------------------------------
        form = QFormLayout()
        self.asset_combo = QComboBox()
        self.asset_combo.addItem(f"➕ Create new asset", _NEW_ASSET)
        for a in assets:
            self.asset_combo.addItem(f"{a['id']} — {a['name']}", a["id"])
        self.asset_combo.currentIndexChanged.connect(self._sync_name_field)
        form.addRow("Import into:", self.asset_combo)

        self.name_edit = QLineEdit(preview.asset_name)
        form.addRow("New asset name:", self.name_edit)
        root.addLayout(form)
        self._sync_name_field()

        # --- buttons -----------------------------------------------------------
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Import")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _sync_name_field(self):
        self.name_edit.setEnabled(self.asset_combo.currentData() == _NEW_ASSET)

    def selected_target(self) -> tuple[int | None, str | None]:
        """Return (target_asset_id, new_asset_name); exactly one is non-None."""
        data = self.asset_combo.currentData()
        if data == _NEW_ASSET:
            return None, (self.name_edit.text().strip() or self.preview.asset_name)
        return int(data), None


def _show(ch: str) -> str:
    return {",": "comma", ";": "semicolon", "\t": "tab", ".": "dot"}.get(ch, repr(ch))
