"""
Knowledge Manager Widget

Provides a UI for viewing, creating, editing, and managing knowledge facts.
Displays all facts with search, filtering, and CRUD operations.
"""

import logging
from typing import Dict
from datetime import datetime

from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import (
    QTableWidgetItem,
    QMessageBox,
    QPushButton,
    QCheckBox,
)

from airunner.components.application.gui.widgets.base_widget import BaseWidget
from airunner.components.knowledge.gui.widgets.templates.knowledge_manager_ui import (
    Ui_knowledge_manager,
)
from airunner.components.knowledge.gui.widgets.knowledge_editor_widget import (
    KnowledgeEditorWidget,
)
from airunner.components.knowledge.data.models import KnowledgeFact
from airunner.enums import SignalCode
from airunner.components.data.session_manager import session_scope


logger = logging.getLogger(__name__)


class KnowledgeManagerWidget(BaseWidget):
    """
    Widget for managing knowledge facts.
    Shows a table of all facts with ability to create, edit, delete, filter, and search.
    """

    widget_class_ = Ui_knowledge_manager

    def __init__(self, *args, **kwargs):
        self.signal_handlers = {
            SignalCode.KNOWLEDGE_FACT_ADDED: self.on_fact_added,
            SignalCode.KNOWLEDGE_FACT_UPDATED: self.on_fact_updated,
            SignalCode.KNOWLEDGE_FACT_DELETED: self.on_fact_deleted,
            SignalCode.KNOWLEDGE_FACTS_RELOAD_REQUESTED: self.load_facts,
        }
        super().__init__(*args, **kwargs)

    def initialize_form(self):
        """Initialize the knowledge manager UI"""
        self.ui.create_fact_button.clicked.connect(self.on_create_fact_clicked)
        self.ui.reload_facts_button.clicked.connect(
            self.on_reload_facts_clicked
        )
        self.ui.search_box.textChanged.connect(self.on_search_changed)
        self.ui.category_filter.currentTextChanged.connect(
            self.on_category_filter_changed
        )
        self.ui.tag_filter.textChanged.connect(self.on_tag_filter_changed)

        # Setup table
        self.ui.facts_table.setColumnCount(8)
        self.ui.facts_table.setHorizontalHeaderLabels(
            [
                "Text",
                "Category",
                "Tags",
                "Confidence",
                "Verified",
                "Created",
                "Access Count",
                "Actions",
            ]
        )
        self.ui.facts_table.horizontalHeader().setStretchLastSection(False)
        self.ui.facts_table.horizontalHeader().setSectionResizeMode(
            0, self.ui.facts_table.horizontalHeader().ResizeMode.Stretch
        )

        # Populate category filter
        self._populate_category_filter()

        self.load_facts()

    def _populate_category_filter(self):
        """Populate category filter dropdown"""
        self.ui.category_filter.clear()
        self.ui.category_filter.addItem("All Categories")

        with session_scope() as session:
            categories = (
                session.query(KnowledgeFact.category)
                .distinct()
                .order_by(KnowledgeFact.category)
                .all()
            )
            for (category,) in categories:
                if category:
                    self.ui.category_filter.addItem(category)

    @Slot()
    def on_create_fact_clicked(self):
        """Open editor dialog to create a new fact"""
        editor = KnowledgeEditorWidget(parent=self)
        if editor.exec():
            self.load_facts()
            self._populate_category_filter()

    @Slot()
    def on_reload_facts_clicked(self):
        """Reload facts from database"""
        self.load_facts()
        self.emit_signal(SignalCode.KNOWLEDGE_FACTS_RELOAD_REQUESTED)

    @Slot(str)
    def on_search_changed(self, text: str):
        """Filter facts based on search text"""
        self._apply_filters()

    @Slot(str)
    def on_category_filter_changed(self, category: str):
        """Filter facts by category"""
        self._apply_filters()

    @Slot(str)
    def on_tag_filter_changed(self, text: str):
        """Filter facts by tags"""
        self._apply_filters()

    def _apply_filters(self):
        """Apply all active filters to the table"""
        search_text = self.ui.search_box.text().lower()
        category = self.ui.category_filter.currentText()
        tag_filter = self.ui.tag_filter.text().lower()

        for row in range(self.ui.facts_table.rowCount()):
            # Get row data
            text_item = self.ui.facts_table.item(row, 0)
            category_item = self.ui.facts_table.item(row, 1)
            tags_item = self.ui.facts_table.item(row, 2)

            # Apply search filter
            search_match = True
            if search_text:
                text_match = (
                    search_text in text_item.text().lower()
                    if text_item
                    else False
                )
                search_match = text_match

            # Apply category filter
            category_match = True
            if category and category != "All Categories":
                category_match = (
                    category_item.text() == category
                    if category_item
                    else False
                )

            # Apply tag filter
            tag_match = True
            if tag_filter:
                tag_match = (
                    tag_filter in tags_item.text().lower()
                    if tags_item
                    else False
                )

            # Show/hide row based on all filters
            self.ui.facts_table.setRowHidden(
                row, not (search_match and category_match and tag_match)
            )

    def load_facts(self):
        """Load and display all facts in the table"""
        self.ui.facts_table.setRowCount(0)
        with session_scope() as session:
            facts = (
                session.query(KnowledgeFact)
                .order_by(KnowledgeFact.created_at.desc())
                .all()
            )
            for fact in facts:
                self._add_fact_row(fact)

    def _add_fact_row(self, fact: KnowledgeFact):
        """Add a fact to the table"""
        row = self.ui.facts_table.rowCount()
        self.ui.facts_table.insertRow(row)

        # Text (truncate if long)
        text = fact.text[:100] + "..." if len(fact.text) > 100 else fact.text
        self.ui.facts_table.setItem(row, 0, QTableWidgetItem(text))

        # Category
        self.ui.facts_table.setItem(
            row, 1, QTableWidgetItem(fact.category or "")
        )

        # Tags
        tags_str = ", ".join(fact.tags) if fact.tags else ""
        self.ui.facts_table.setItem(row, 2, QTableWidgetItem(tags_str))

        # Confidence
        confidence_str = f"{fact.confidence:.2f}" if fact.confidence else "N/A"
        self.ui.facts_table.setItem(row, 3, QTableWidgetItem(confidence_str))

        # Verified checkbox (read-only display)
        verified_widget = QCheckBox()
        verified_widget.setChecked(fact.verified)
        verified_widget.setEnabled(False)
        self.ui.facts_table.setCellWidget(row, 4, verified_widget)

        # Created date
        created_str = fact.created_at.strftime("%Y-%m-%d %H:%M")
        self.ui.facts_table.setItem(row, 5, QTableWidgetItem(created_str))

        # Access count
        self.ui.facts_table.setItem(
            row, 6, QTableWidgetItem(str(fact.access_count))
        )

        # Actions
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(
            lambda checked, f=fact: self.on_edit_fact(f)
        )
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(
            lambda checked, f=fact: self.on_delete_fact(f)
        )
        actions_widget = self._create_actions_widget(
            edit_button, delete_button
        )
        self.ui.facts_table.setCellWidget(row, 7, actions_widget)

    def _create_actions_widget(self, *buttons):
        """Create a widget with action buttons"""
        from PySide6.QtWidgets import QWidget, QHBoxLayout

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        for button in buttons:
            layout.addWidget(button)
        return widget

    @Slot(object)
    def on_edit_fact(self, fact: KnowledgeFact):
        """Open editor dialog to edit a fact"""
        editor = KnowledgeEditorWidget(fact=fact, parent=self)
        if editor.exec():
            self.load_facts()
            self._populate_category_filter()

    @Slot(object)
    def on_delete_fact(self, fact: KnowledgeFact):
        """Delete a fact after confirmation"""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete this fact?\n\n{fact.text[:100]}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            with session_scope() as session:
                db_fact = (
                    session.query(KnowledgeFact).filter_by(id=fact.id).first()
                )
                if db_fact:
                    session.delete(db_fact)
                    logger.info(f"Deleted fact {fact.id}")
                    self.emit_signal(
                        SignalCode.KNOWLEDGE_FACT_DELETED, {"fact_id": fact.id}
                    )
                    self.load_facts()
                    self._populate_category_filter()

    def on_fact_added(self, data: Dict):
        """Handle fact added signal"""
        self.load_facts()
        self._populate_category_filter()

    def on_fact_updated(self, data: Dict):
        """Handle fact updated signal"""
        self.load_facts()

    def on_fact_deleted(self, data: Dict):
        """Handle fact deleted signal"""
        self.load_facts()

    def save_state(self):
        """Save widget state"""
        pass

    def restore_state(self):
        """Restore widget state"""
        pass
