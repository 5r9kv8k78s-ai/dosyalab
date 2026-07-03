import logging
from pathlib import Path

import fitz
from openpyxl import Workbook

from app.modules.converter.base import ConversionModule
from app.modules.converter.registry import register_converter

logger = logging.getLogger(__name__)


class PdfToXlsxConverter(ConversionModule):
    """Converts PDF documents to XLSX by extracting tables via PyMuPDF's
    built-in table finder (`Page.find_tables()`, available since PyMuPDF
    1.23) — no new heavy dependency, since PyMuPDF is already used for PDF
    validation elsewhere in the app.

    One worksheet per source page that contains at least one table; a page
    with multiple tables gets all of them on that page's sheet, separated by
    a blank row, preserving each table's row/column structure. Pages with no
    tables are skipped entirely. If the PDF has no tables anywhere,
    conversion fails with a clear error (an empty workbook cannot be saved).
    """

    slug = "pdf-to-xlsx"
    input_formats = ("pdf",)
    output_format = "xlsx"

    def convert(self, source_path: Path, destination_dir: Path) -> Path:
        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / f"{source_path.stem}.xlsx"

        logger.info("pdf_to_xlsx.convert.start", extra={"source": str(source_path)})

        doc = fitz.open(source_path)
        try:
            workbook = Workbook()
            workbook.remove(workbook.active)

            tables_written = 0
            for page_index, page in enumerate(doc):
                tables = page.find_tables().tables
                if not tables:
                    continue

                sheet = workbook.create_sheet(title=f"Page {page_index + 1}")
                row_cursor = 1
                for table in tables:
                    for row in table.extract():
                        for col_index, value in enumerate(row, start=1):
                            sheet.cell(row=row_cursor, column=col_index, value=value)
                        row_cursor += 1
                    row_cursor += 1  # blank separator row between tables on the same page
                    tables_written += 1

            if tables_written == 0:
                raise ValueError("No tables were found in this PDF.")

            workbook.save(output_path)
        finally:
            doc.close()

        logger.info(
            "pdf_to_xlsx.convert.done",
            extra={"output": str(output_path), "tables_written": tables_written},
        )
        return output_path


register_converter(PdfToXlsxConverter())
