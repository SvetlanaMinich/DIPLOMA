"""Database models — полная схема по ER / DiplomaDatabase.drawio."""
from app.models.audit import AuditAction, AuditLog
from app.models.document import Document, DocumentType, DocumentVersion, DocumentWorkflowStatus
from app.models.document_content import (
    AISuggestion,
    BibliographicReference,
    Citation,
    DocumentImage,
    DocumentTable,
    Section,
    TableCell,
    TextElement,
)
from app.models.role import Role
from app.models.session import Session
from app.models.template import Template, TemplateType
from app.models.user import User

__all__ = [
    "Role",
    "User",
    "Document",
    "DocumentType",
    "DocumentWorkflowStatus",
    "DocumentVersion",
    "Section",
    "TextElement",
    "DocumentTable",
    "TableCell",
    "DocumentImage",
    "AISuggestion",
    "BibliographicReference",
    "Citation",
    "Template",
    "TemplateType",
    "Session",
    "AuditLog",
    "AuditAction",
]
