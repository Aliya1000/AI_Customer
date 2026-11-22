"""
Tests for PDF, Word (.docx), and Vision-Language Model (VLM) image parsers.
"""

import io
import zipfile
from pathlib import Path
from langchain_core.documents import Document

from rag_service.config import settings
from rag_service.parsers.docx_parser import DocxParser
from rag_service.parsers.vlm_image_parser import VLMImageParser
from rag_service.parsers.document_parsers import DocumentIngestionPipeline


def test_pdf_parsing_sample_doc():
    pdf_path = settings.sample_docs_dir / "Customer_Support_Knowledge_Base_50_QA.pdf"
    if not pdf_path.exists():
        pdf_path = Path("sample_docs/Customer_Support_Knowledge_Base_50_QA.pdf")
    if not pdf_path.exists():
        return

    pipeline = DocumentIngestionPipeline()
    chunks = pipeline.process_file(pdf_path)

    assert len(chunks) > 0
    first_chunk = chunks[0]
    assert first_chunk.metadata["file_type"] == "pdf"
    assert "Customer Support Knowledge Base" in first_chunk.page_content or first_chunk.metadata["source"] == "Customer_Support_Knowledge_Base_50_QA.pdf"


def test_docx_parser(tmp_path: Path):
    # Construct a minimal valid .docx file in-memory using standard zipfile
    xml_content = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:body>
            <w:p><w:r><w:t>ShopEase Return Policy and Guidelines</w:t></w:r></w:p>
            <w:p><w:r><w:t>Customers can return items within 30 calendar days for a full refund.</w:t></w:r></w:p>
        </w:body>
    </w:document>"""

    docx_path = tmp_path / "policy.docx"
    with zipfile.ZipFile(docx_path, "w") as z:
        z.writestr("word/document.xml", xml_content)

    parser = DocxParser()
    docs = parser.parse_file(docx_path)

    assert len(docs) == 1
    assert docs[0].metadata["file_type"] == "docx"
    assert "ShopEase Return Policy and Guidelines" in docs[0].page_content
    assert "30 calendar days" in docs[0].page_content


def test_vlm_image_parser_mock():
    # 1x1 valid transparent PNG
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\x9f\x01\x00\x01\x00\x01\xa2\xde\xbe\x14\x00\x00\x00\x00IEND\xaeB`\x82"

    parser = VLMImageParser(api_key="your_api_key_placeholder", model="qwen/qwen3.8-27b")
    assert parser.model == "qwen/qwen3.8-27b"
    docs = parser.parse_image_bytes(png_bytes, filename="architecture_diagram.png")

    assert len(docs) == 1
    doc = docs[0]
    assert doc.metadata["source"] == "architecture_diagram.png"
    assert doc.metadata["file_type"] == "png"
    assert "architecture_diagram.png" in doc.page_content


def test_document_ingestion_routing(tmp_path: Path):
    pipeline = DocumentIngestionPipeline()

    # 1. Text file
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("Plain text test file content.")

    # 2. Mock image file
    img_file = tmp_path / "chart.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\x9f\x01\x00\x01\x00\x01\xa2\xde\xbe\x14\x00\x00\x00\x00IEND\xaeB`\x82")

    chunks_txt = pipeline.process_file(txt_file)
    chunks_img = pipeline.process_file(img_file)

    assert len(chunks_txt) >= 1
    assert chunks_txt[0].metadata["file_type"] == "txt"

    assert len(chunks_img) >= 1
    assert chunks_img[0].metadata["file_type"] == "png"
