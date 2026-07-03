"""Shared infrastructure for PDF-manipulation features.

Distinct from `app.modules.converter`, which holds the existing
format-to-format conversion pipeline (PDF -> DOCX, DOCX -> PDF, PDF -> XLSX,
Images -> PDF). This package is for PDF-to-PDF and PDF-inspection operations
built on top of `pdf_engine.PdfEngine`.
"""
