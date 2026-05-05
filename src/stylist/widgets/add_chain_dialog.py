"""AddChainDialog — source-selection step of the "Add Style Chain" flow.

The user picks one of two sources:
  • Import YAML file
  • Save the current style log as a chain (disabled when the log is empty)

The dialog only collects the source choice; the controller handles file
dialogs and name dialogs separately.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


class AddChainDialog(QDialog):
    """Step 1 of the Add Chain flow — choose import vs. save-from-log.

    Args:
        style_log_summary: Human-readable summary of the current style log,
            e.g. ``"Ukiyo-e 150 % → Cubism 80 %"``.  Shown next to the
            "Save current style log" radio button.
        log_empty: When *True* the "Save current style log" option is
            disabled.
        parent: Optional parent widget.
    """

    SOURCE_IMPORT_YAML = "import"
    SOURCE_SAVE_LOG = "save_log"

    def __init__(
        self,
        style_log_summary: str = "",
        log_empty: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Style Chain")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        self._radio_import = QRadioButton("Import YAML file\u2026")
        self._radio_import.setChecked(True)
        layout.addWidget(self._radio_import)

        self._radio_save = QRadioButton("Save current style log as chain")
        self._radio_save.setEnabled(not log_empty)
        layout.addWidget(self._radio_save)

        if style_log_summary:
            summary_label = QLabel(f"    {style_log_summary}")
            summary_label.setEnabled(not log_empty)
            summary_label.setStyleSheet("color: #aaaaaa;")
            layout.addWidget(summary_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Cancel | QDialogButtonBox.Ok,  # type: ignore[attr-defined]
        )
        buttons.button(QDialogButtonBox.Ok).setText("Next \u203a")  # type: ignore[attr-defined]
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------

    def selected_source(self) -> str:
        """Return ``SOURCE_IMPORT_YAML`` or ``SOURCE_SAVE_LOG``."""
        if self._radio_save.isChecked():
            return self.SOURCE_SAVE_LOG
        return self.SOURCE_IMPORT_YAML
