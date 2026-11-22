"""
Word Document (.docx / .doc) Parser.

Extracts text, paragraphs, and tables from Microsoft Word (.docx) files
into structured LangChain Documents without requiring external heavy binaries.
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Union
import io
from langchain_core.documents import Document


class DocxParser:
    """Parses Microsoft Word (.docx) documents into LangChain Documents."""

    def parse_file(self, file_path: Union[str, Path]) -> List[Document]:
        """Reads and extracts text from a .docx file on disk."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        file_bytes = path.read_bytes()
        return self.parse_bytes(file_bytes, filename=path.name)

    def parse_bytes(self, file_bytes: bytes, filename: str = "document.docx") -> List[Document]:
        """Parses raw .docx bytes extracting paragraphs and tables."""
        text = self._extract_text_from_docx_bytes(file_bytes)
        return [
            Document(
                page_content=text,
                metadata={
                    "source": filename,
                    "file_name": filename,
                    "file_type": "docx",
                    "total_chars": len(text),
                },
            )
        ]

    def _extract_text_from_docx_bytes(self, file_bytes: bytes) -> str:
        """Extracts text content by reading word/document.xml inside the .docx zip container."""
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx_zip:
                if "word/document.xml" not in docx_zip.namelist():
                    # Fallback for plain text or older format
                    return file_bytes.decode("utf-8", errors="ignore").strip()

                xml_data = docx_zip.read("word/document.xml")

            tree = ET.fromstring(xml_data)
            # OpenXML Namespace for WordprocessingML
            w_namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

            paragraphs: List[str] = []

            # Extract paragraphs and tables
            for p in tree.iter(f"{w_namespace}p"):
                # Collect text runs inside this paragraph
                run_texts = [
                    t.text for t in p.iter(f"{w_namespace}t") if t.text
                ]
                if run_texts:
                    line = "".join(run_texts).strip()
                    if line:
                        paragraphs.append(line)

            # Also check for table cells if any
            for table in tree.iter(f"{w_namespace}tbl"):
                table_rows = []
                for row in table.iter(f"{w_namespace}tr"):
                    row_cells = []
                    for cell in row.iter(f"{w_namespace}tc"):
                        cell_texts = [
                            t.text for t in cell.iter(f"{w_namespace}t") if t.text
                        ]
                        row_cells.append("".join(cell_texts).strip())
                    if any(row_cells):
                        table_rows.append(" | ".join(row_cells))
                if table_rows:
                    paragraphs.append("\n[Table Data]\n" + "\n".join(table_rows))

            return "\n\n".join(paragraphs).strip()

        except Exception as e:
            # Fallback for legacy binary doc or simple text
            decoded = file_bytes.decode("utf-8", errors="ignore")
            # Filter non-printable ASCII
            printable = "".join(ch for ch in decoded if ch.isprintable() or ch in "\n\r\t")
            return printable.strip()
