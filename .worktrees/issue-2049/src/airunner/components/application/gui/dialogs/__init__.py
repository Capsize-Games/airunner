"""Application dialogs module."""

from airunner.components.application.gui.dialogs.donation_dialog import DonationDialog
from airunner.components.application.gui.dialogs.download_models_dialog import (
    DownloadModelsDialog,
    show_download_models_dialog,
)
from airunner.components.application.gui.dialogs.first_run_agreement_dialog import (
    FirstRunAgreementDialog,
)
from airunner.components.application.gui.dialogs.legal_document_dialog import (
    LegalDocumentDialog,
)

__all__ = [
    "DonationDialog",
    "DownloadModelsDialog",
    "show_download_models_dialog",
    "FirstRunAgreementDialog",
    "LegalDocumentDialog",
]
