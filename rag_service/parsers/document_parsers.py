"""
LangChain Document Parsers and Loaders.

Handles multi-format document loading:
- PDF (.pdf) via PyPDFLoader
- Microsoft Word (.docx, .doc) via DocxParser
- Images (.png, .jpg, .jpeg, .webp, .bmp) via Vision-Language Model (VLM)
- Text and Markdown (.txt, .md, .markdown, .rst) via TextLoader
- JSON (.json) and structured records
Followed by chunking using RecursiveCharacterTextSplitter and metadata enrichment.
"""

import json
from pathlib import Path
from typing import List, Optional, Set

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
)

from ..config import settings
from .docx_parser import DocxParser
from .vlm_image_parser import VLMImageParser

IMAGE_EXTENSIONS: Set[str] = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".gif"}
DOC_EXTENSIONS: Set[str] = {".docx", ".doc"}
TEXT_EXTENSIONS: Set[str] = {".txt", ".md", ".markdown", ".rst"}


class DocumentIngestionPipeline:
    """Ingests multi-format files, parses them with appropriate specialized loaders

    (PDF, Word docs, VLM for images, Markdown, JSON), and splits them into chunked
    LangChain Documents with enriched metadata.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        vlm_parser: Optional[VLMImageParser] = None,
        docx_parser: Optional[DocxParser] = None,
    ):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
            length_function=len,
        )
        self.vlm_parser = vlm_parser or VLMImageParser()
        self.docx_parser = docx_parser or DocxParser()

    def load_file(self, file_path: str | Path) -> List[Document]:
        """Loads a file using the appropriate parser/loader based on its file extension."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()

        # 1. PDF Documents
        if suffix == ".pdf":
            loader = PyPDFLoader(str(path))
            docs = loader.load()

        # 2. Microsoft Word Documents (.docx, .doc)
        elif suffix in DOC_EXTENSIONS:
            docs = self.docx_parser.parse_file(path)

        # 3. Image Files (Processed with Vision-Language Model)
        elif suffix in IMAGE_EXTENSIONS:
            docs = self.vlm_parser.parse_image_file(path)

        # 4. Text and Markdown Documents
        elif suffix in TEXT_EXTENSIONS:
            loader = TextLoader(str(path), encoding="utf-8")
            docs = loader.load()

        # 5. Structured JSON Files
        elif suffix == ".json":
            docs = self._load_json(path)

        # 6. Fallback Text Loader
        else:
            try:
                loader = TextLoader(str(path), encoding="utf-8")
                docs = loader.load()
            except Exception as e:
                raise ValueError(f"Unsupported or unparseable file type: {suffix}. Error: {e}")

        # Enrich raw loaded docs with normalized metadata
        for i, doc in enumerate(docs):
            doc.metadata["source"] = path.name
            doc.metadata["file_name"] = path.name
            doc.metadata["file_path"] = str(path.resolve())
            doc.metadata.setdefault("file_type", suffix.lstrip("."))
            if "page" not in doc.metadata:
                doc.metadata["page"] = i + 1

        return docs

    def _load_json(self, path: Path) -> List[Document]:
        """Custom JSON parser converting records or key-value structures into LangChain Documents."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        docs = []
        if isinstance(data, list):
            for idx, item in enumerate(data):
                if isinstance(item, dict):
                    content = item.get("text") or item.get("content") or json.dumps(item, indent=2)
                    metadata = {
                        k: v for k, v in item.items()
                        if k not in ["text", "content"] and isinstance(v, (str, int, float, bool))
                    }
                    metadata["record_index"] = idx
                else:
                    content = str(item)
                    metadata = {"record_index": idx}
                docs.append(Document(page_content=content, metadata=metadata))
        elif isinstance(data, dict):
            for key, val in data.items():
                content = f"[{key}]\n{json.dumps(val, indent=2) if isinstance(val, (dict, list)) else str(val)}"
                docs.append(Document(page_content=content, metadata={"key": key}))
        else:
            docs.append(Document(page_content=str(data), metadata={}))

        return docs

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Splits loaded LangChain Documents into smaller chunks

        and enriches each chunk with chunk_id and character length.
        """
        chunks = self.splitter.split_documents(documents)
        for idx, chunk in enumerate(chunks):
            source = chunk.metadata.get("source", "unknown")
            chunk.metadata["chunk_id"] = f"{source}_chunk_{idx}"
            chunk.metadata["chunk_index"] = idx
            chunk.metadata["char_count"] = len(chunk.page_content)
        return chunks

    def process_file(self, file_path: str | Path) -> List[Document]:
        """Convenience method: loads and chunks a single file."""
        raw_docs = self.load_file(file_path)
        return self.split_documents(raw_docs)

    def process_directory(self, dir_path: str | Path, recursive: bool = True) -> List[Document]:
        """Scans a directory, parses all supported files, and splits them into chunks."""
        path = Path(dir_path)
        if not path.is_dir():
            raise NotADirectoryError(f"Directory not found: {path}")

        pattern = "**/*" if recursive else "*"
        all_chunks = []
        supported_exts = {".pdf", ".docx", ".doc", ".txt", ".md", ".markdown", ".json"} | IMAGE_EXTENSIONS

        for p in path.glob(pattern):
            if p.is_file() and p.suffix.lower() in supported_exts:
                try:
                    chunks = self.process_file(p)
                    all_chunks.extend(chunks)
                except Exception as e:
                    print(f"Warning: Failed to parse {p}: {e}")

        return all_chunks


def parse_document(file_path: str | Path) -> List[Document]:
    """Helper function to load and chunk a file with default pipeline settings."""
    pipeline = DocumentIngestionPipeline()
    return pipeline.process_file(file_path)
