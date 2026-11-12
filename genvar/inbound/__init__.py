"""OGIAS Inbound/Validation — API publique non destructive.

Exemple :
    from genvar.inbound import InputKind, preview_import, stage_import
    report = preview_import("inventaire.xlsx", InputKind.INVENTORY, session)
    if not report.errors:
        staged = stage_import(report, session, confirmed=True)
        # staged.session est une COPIE non enregistrée ; l'original reste intact.
"""
from .schemas import (Diagnostic, ImportPreview, InboundError, InputKind,
                      PreviewRow, RowAction, Severity, StagedImport)
from .validation import preview_import, session_digest
from .commit import stage_import

__all__ = ["Diagnostic", "ImportPreview", "InboundError", "InputKind",
           "PreviewRow", "RowAction", "Severity", "StagedImport",
           "preview_import", "session_digest", "stage_import"]
