"""NameChainDialog — name and description input for the "Add Style Chain" flow.

Shown after the user selects a source in :class:`AddChainDialog`.
Pre-fills name and description with the same auto-suggested string; both
fields are fully editable.  [Save Chain] is disabled while Name is empty.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

_MAX_NAME_LEN = 18


class NameChainDialog(QDialog):
    """Step 2 of the Add Chain flow — collect name and description.

    Args:
        suggested_name: Pre-filled value for both Name and Description fields.
        parent:         Optional parent widget.
    """

    def __init__(
        self,
        suggested_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Name Your Chain")
        self.setMinimumWidth(380)

        layout = QFormLayout(self)

        self._name_edit = QLineEdit(suggested_name[:_MAX_NAME_LEN])
        self._name_edit.setMaxLength(_MAX_NAME_LEN)
        self._name_counter = QLabel(f"{len(self._name_edit.text())}/{_MAX_NAME_LEN}")
        layout.addRow("Name *:", self._name_edit)
        layout.addRow("", self._name_counter)

        self._desc_edit = QLineEdit(suggested_name)
        layout.addRow("Description:", self._desc_edit)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.Cancel | QDialogButtonBox.Save,  # type: ignore[attr-defined]
        )
        self._buttons.button(QDialogButtonBox.Save).setText("Save Chain")  # type: ignore[attr-defined]
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addRow(self._buttons)

        # Disable Save while name is empty
        self._update_save_button()
        self._name_edit.textChanged.connect(self._update_save_button)
        self._name_edit.textChanged.connect(
            lambda t: self._name_counter.setText(f"{len(t)}/{_MAX_NAME_LEN}")
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _update_save_button(self) -> None:
        enabled = bool(self._name_edit.text().strip())
        self._buttons.button(QDialogButtonBox.Save).setEnabled(enabled)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    def chain_name(self) -> str:
        """Return the entered name (stripped)."""
        return self._name_edit.text().strip()

    def chain_description(self) -> str:
        """Return the entered description (stripped)."""
        return self._desc_edit.text().strip()
