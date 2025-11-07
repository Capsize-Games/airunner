"""
Knowledge Editor Widget

Dialog for creating and editing knowledge facts.
Provides form fields for fact properties with validation.
"""

from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QDialog, QMessageBox

from airunner.components.knowledge.gui.widgets.templates.knowledge_editor_ui import (
    Ui_knowledge_editor,
)
from airunner.components.knowledge.data.models import KnowledgeFact
from airunner.enums import SignalCode
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger
from airunner.utils.application.mediator_mixin import MediatorMixin
from airunner.utils.settings.get_qsettings import get_qsettings
from airunner.components.data.session_manager import session_scope


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


class KnowledgeEditorWidget(QDialog, MediatorMixin):
    """
    Dialog for creating/editing knowledge facts.
    Provides form with validation.
    """

    def __init__(self, fact: Optional[KnowledgeFact] = None, parent=None):
        super().__init__(parent)
        self.settings = get_qsettings()
        self.fact = fact
        self.ui = Ui_knowledge_editor()
        self.ui.setupUi(self)

        self._setup_ui()
        self._connect_signals()

        if fact:
            self._load_fact_data()

    def _setup_ui(self):
        """Setup UI elements"""
        # Populate category dropdown with common categories
        common_categories = [
            "preference",
            "personal_info",
            "professional",
            "hobby",
            "health",
            "family",
            "location",
            "education",
            "technology",
            "other",
        ]
        self.ui.category_input.addItems(common_categories)

        # Update title based on mode
        if self.fact:
            self.ui.title_label.setText("Edit Knowledge Fact")
        else:
            self.ui.title_label.setText("Create New Knowledge Fact")

    def _connect_signals(self):
        """Connect signals"""
        self.ui.confidence_slider.valueChanged.connect(
            self.on_confidence_changed
        )
        self.ui.button_box.accepted.connect(self.on_save_clicked)
        self.ui.button_box.rejected.connect(self.reject)

    def _load_fact_data(self):
        """Load fact data into form"""
        if not self.fact:
            return

        self.ui.text_input.setPlainText(self.fact.text)
        if self.fact.category:
            index = self.ui.category_input.findText(self.fact.category)
            if index >= 0:
                self.ui.category_input.setCurrentIndex(index)
            else:
                self.ui.category_input.setEditText(self.fact.category)

        if self.fact.tags:
            self.ui.tags_input.setText(", ".join(self.fact.tags))

        if self.fact.confidence is not None:
            slider_value = int(self.fact.confidence * 100)
            self.ui.confidence_slider.setValue(slider_value)

        if self.fact.source:
            self.ui.source_input.setText(self.fact.source)

        self.ui.verified_checkbox.setChecked(self.fact.verified)
        self.ui.enabled_checkbox.setChecked(self.fact.enabled)

    @Slot(int)
    def on_confidence_changed(self, value: int):
        """Update confidence label when slider changes"""
        confidence = value / 100.0
        self.ui.confidence_value_label.setText(f"{confidence:.2f}")

    @Slot()
    def on_save_clicked(self):
        """Save fact to database"""
        # Validate required fields
        text = self.ui.text_input.toPlainText().strip()

        if not text:
            QMessageBox.warning(
                self, "Validation Error", "Fact text is required."
            )
            return

        # Collect form data
        category = self.ui.category_input.currentText().strip()
        tags_str = self.ui.tags_input.text().strip()
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
        confidence = self.ui.confidence_slider.value() / 100.0
        source = self.ui.source_input.text().strip()
        verified = self.ui.verified_checkbox.isChecked()
        enabled = self.ui.enabled_checkbox.isChecked()

        # Save to database
        try:
            with session_scope() as session:
                if self.fact:
                    # Update existing fact
                    db_fact = (
                        session.query(KnowledgeFact)
                        .filter_by(id=self.fact.id)
                        .first()
                    )
                    if db_fact:
                        db_fact.text = text
                        db_fact.category = category if category else None
                        db_fact.tags = tags
                        db_fact.confidence = confidence
                        db_fact.source = source if source else None
                        db_fact.verified = verified
                        db_fact.enabled = enabled

                        logger.info(f"Updated fact {db_fact.id}")
                        self.emit_signal(
                            SignalCode.KNOWLEDGE_FACT_UPDATED,
                            {"fact": db_fact},
                        )
                else:
                    # Create new fact
                    new_fact = KnowledgeFact(
                        text=text,
                        category=category if category else None,
                        tags=tags,
                        confidence=confidence,
                        source=source if source else None,
                        verified=verified,
                        enabled=enabled,
                    )
                    session.add(new_fact)
                    session.flush()

                    logger.info(f"Created new fact {new_fact.id}")
                    self.emit_signal(
                        SignalCode.KNOWLEDGE_FACT_ADDED, {"fact": new_fact}
                    )

            self.accept()

        except Exception as e:
            logger.error(f"Error saving fact: {e}")
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save fact:\n{str(e)}",
            )
