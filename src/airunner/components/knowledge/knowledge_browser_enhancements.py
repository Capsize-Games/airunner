"""
Enhanced knowledge browser widget integration.

Adds export, bulk operations, and verification features to the existing
knowledge manager widget.
"""

from typing import Set

from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QPushButton,
    QCheckBox,
    QHBoxLayout,
    QLabel,
)
from PySide6.QtCore import Qt

from airunner.components.knowledge.knowledge_browser_utils import (
    KnowledgeExporter,
    KnowledgeBulkOperations,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class KnowledgeBrowserEnhancements:
    """
    Mixin for enhancing knowledge browser widget.

    Provides export, bulk operations, and verification features.
    """

    def __init__(self):
        """Initialize enhancements."""
        self.exporter = KnowledgeExporter()
        self.bulk_ops = KnowledgeBulkOperations()
        self.selected_fact_ids: Set[int] = set()

    def add_export_buttons(self, layout):
        """
        Add export buttons to widget layout.

        Args:
            layout: Layout to add buttons to
        """
        export_layout = QHBoxLayout()

        export_json_btn = QPushButton("Export to JSON")
        export_json_btn.clicked.connect(self.on_export_json)
        export_layout.addWidget(export_json_btn)

        export_csv_btn = QPushButton("Export to CSV")
        export_csv_btn.clicked.connect(self.on_export_csv)
        export_layout.addWidget(export_csv_btn)

        backup_btn = QPushButton("Create Backup")
        backup_btn.clicked.connect(self.on_create_backup)
        export_layout.addWidget(backup_btn)

        layout.addLayout(export_layout)

    def add_bulk_operation_buttons(self, layout):
        """
        Add bulk operation buttons to widget layout.

        Args:
            layout: Layout to add buttons to
        """
        bulk_layout = QHBoxLayout()

        label = QLabel("Bulk Operations:")
        bulk_layout.addWidget(label)

        verify_btn = QPushButton("Verify Selected")
        verify_btn.clicked.connect(self.on_bulk_verify)
        bulk_layout.addWidget(verify_btn)

        unverify_btn = QPushButton("Unverify Selected")
        unverify_btn.clicked.connect(self.on_bulk_unverify)
        bulk_layout.addWidget(unverify_btn)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.on_bulk_delete)
        bulk_layout.addWidget(delete_btn)

        bulk_layout.addStretch()

        layout.addLayout(bulk_layout)

    def add_selection_checkbox(self, row: int, fact_id: int):
        """
        Add selection checkbox to table row.

        Args:
            row: Table row number
            fact_id: Fact ID for tracking
        """
        checkbox = QCheckBox()
        checkbox.setProperty("fact_id", fact_id)
        checkbox.stateChanged.connect(
            lambda state, fid=fact_id: self.on_selection_changed(
                fid, state == Qt.Checked
            )
        )

        # Assuming table widget is self.ui.table
        if hasattr(self, "ui") and hasattr(self.ui, "table"):
            self.ui.table.setCellWidget(row, 0, checkbox)

    def on_selection_changed(self, fact_id: int, selected: bool):
        """
        Handle selection checkbox state change.

        Args:
            fact_id: Fact ID
            selected: Whether checkbox is checked
        """
        if selected:
            self.selected_fact_ids.add(fact_id)
        else:
            self.selected_fact_ids.discard(fact_id)

        logger.debug(
            f"Selection changed: {len(self.selected_fact_ids)} facts selected"
        )

    def on_export_json(self):
        """Handle export to JSON button click."""
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Export Knowledge to JSON",
            "knowledge_export.json",
            "JSON Files (*.json)",
        )

        if file_path:
            try:
                count = self.exporter.export_to_json(file_path)
                QMessageBox.information(
                    None,
                    "Export Successful",
                    f"Exported {count} facts to {file_path}",
                )
                logger.info(f"Exported {count} facts to JSON: {file_path}")
            except Exception as e:
                QMessageBox.critical(
                    None, "Export Failed", f"Failed to export: {str(e)}"
                )
                logger.exception("JSON export failed")

    def on_export_csv(self):
        """Handle export to CSV button click."""
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Export Knowledge to CSV",
            "knowledge_export.csv",
            "CSV Files (*.csv)",
        )

        if file_path:
            try:
                count = self.exporter.export_to_csv(file_path)
                QMessageBox.information(
                    None,
                    "Export Successful",
                    f"Exported {count} facts to {file_path}",
                )
                logger.info(f"Exported {count} facts to CSV: {file_path}")
            except Exception as e:
                QMessageBox.critical(
                    None, "Export Failed", f"Failed to export: {str(e)}"
                )
                logger.exception("CSV export failed")

    def on_create_backup(self):
        """Handle create backup button click."""
        try:
            backup_path = self.exporter.create_backup()
            QMessageBox.information(
                None,
                "Backup Created",
                f"Backup created successfully:\n{backup_path}",
            )
            logger.info(f"Created backup at: {backup_path}")
        except Exception as e:
            QMessageBox.critical(
                None, "Backup Failed", f"Failed to create backup: {str(e)}"
            )
            logger.exception("Backup creation failed")

    def on_bulk_verify(self):
        """Handle bulk verify button click."""
        if not self.selected_fact_ids:
            QMessageBox.warning(
                None, "No Selection", "Please select facts to verify."
            )
            return

        try:
            count = self.bulk_ops.bulk_verify(
                list(self.selected_fact_ids), verified=True
            )
            QMessageBox.information(
                None, "Verification Complete", f"Verified {count} facts."
            )
            logger.info(f"Bulk verified {count} facts")

            # Refresh display if method exists
            if hasattr(self, "load_facts"):
                self.load_facts()

        except Exception as e:
            QMessageBox.critical(
                None,
                "Verification Failed",
                f"Failed to verify facts: {str(e)}",
            )
            logger.exception("Bulk verification failed")

    def on_bulk_unverify(self):
        """Handle bulk unverify button click."""
        if not self.selected_fact_ids:
            QMessageBox.warning(
                None, "No Selection", "Please select facts to unverify."
            )
            return

        try:
            count = self.bulk_ops.bulk_verify(
                list(self.selected_fact_ids), verified=False
            )
            QMessageBox.information(
                None, "Unverification Complete", f"Unverified {count} facts."
            )
            logger.info(f"Bulk unverified {count} facts")

            # Refresh display if method exists
            if hasattr(self, "load_facts"):
                self.load_facts()

        except Exception as e:
            QMessageBox.critical(
                None,
                "Unverification Failed",
                f"Failed to unverify facts: {str(e)}",
            )
            logger.exception("Bulk unverification failed")

    def on_bulk_delete(self):
        """Handle bulk delete button click."""
        if not self.selected_fact_ids:
            QMessageBox.warning(
                None, "No Selection", "Please select facts to delete."
            )
            return

        # Confirm deletion
        reply = QMessageBox.question(
            None,
            "Confirm Deletion",
            f"Are you sure you want to delete {len(self.selected_fact_ids)} facts?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                count = self.bulk_ops.bulk_delete(list(self.selected_fact_ids))
                QMessageBox.information(
                    None, "Deletion Complete", f"Deleted {count} facts."
                )
                logger.info(f"Bulk deleted {count} facts")

                # Clear selection
                self.selected_fact_ids.clear()

                # Refresh display if method exists
                if hasattr(self, "load_facts"):
                    self.load_facts()

            except Exception as e:
                QMessageBox.critical(
                    None,
                    "Deletion Failed",
                    f"Failed to delete facts: {str(e)}",
                )
                logger.exception("Bulk deletion failed")

    def add_quick_verify_buttons(self, row: int, fact_id: int):
        """
        Add quick verify/reject buttons to table row.

        Args:
            row: Table row number
            fact_id: Fact ID
        """
        widget_container = QHBoxLayout()

        verify_btn = QPushButton("✓")
        verify_btn.setToolTip("Verify this fact")
        verify_btn.setMaximumWidth(30)
        verify_btn.clicked.connect(
            lambda: self.on_quick_verify(fact_id, verified=True)
        )
        widget_container.addWidget(verify_btn)

        reject_btn = QPushButton("✗")
        reject_btn.setToolTip("Reject this fact")
        reject_btn.setMaximumWidth(30)
        reject_btn.clicked.connect(
            lambda: self.on_quick_verify(fact_id, verified=False)
        )
        widget_container.addWidget(reject_btn)

        # Create container widget for layout
        from PySide6.QtWidgets import QWidget

        container = QWidget()
        container.setLayout(widget_container)

        # Assuming table widget is self.ui.table
        if hasattr(self, "ui") and hasattr(self.ui, "table"):
            # Add to actions column (adjust column index as needed)
            self.ui.table.setCellWidget(row, 8, container)

    def on_quick_verify(self, fact_id: int, verified: bool):
        """
        Handle quick verify/reject button click.

        Args:
            fact_id: Fact ID
            verified: True to verify, False to reject
        """
        try:
            count = self.bulk_ops.bulk_verify([fact_id], verified=verified)

            if count > 0:
                status = "verified" if verified else "rejected"
                logger.info(f"Fact {fact_id} {status}")

                # Refresh display if method exists
                if hasattr(self, "load_facts"):
                    self.load_facts()

        except Exception as e:
            QMessageBox.critical(
                None,
                "Verification Failed",
                f"Failed to update fact: {str(e)}",
            )
            logger.exception(f"Quick verify failed for fact {fact_id}")
