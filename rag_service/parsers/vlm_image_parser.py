"""
Vision-Language Model (VLM) Image Parser using langchain-groq.

Processes image files (.png, .jpg, .jpeg, .webp, .bmp) using Groq's multimodal VLM
(default: qwen/qwen3.8-27b) via the langchain-groq library into structured LangChain Documents.
"""

import base64
import mimetypes
from pathlib import Path
from typing import List, Optional, Union

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from ..config import settings


VLM_IMAGE_EXTRACTION_PROMPT = """You are an advanced optical character recognition (OCR) and visual document analysis engine.
Carefully examine this image and perform the following tasks:
1. Transcribe all readable text, titles, paragraphs, bullet points, numbers, and labels verbatim in clean Markdown format.
2. If the image contains tables, transcribe them as formatted Markdown tables.
3. If the image contains diagrams, architecture flowcharts, infographics, or charts, describe the visual hierarchy, entities, and flow relationships in clear, precise detail.
4. Output the complete extracted text and visual synthesis cleanly without any preamble."""


class VLMImageParser:
    """Parses image files using Groq VLM (qwen/qwen3.8-27b) via langchain-groq."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ):
        self.api_key = api_key or settings.groq_api_key or settings.nvidia_api_key
        self.model = model or settings.groq_vlm_model or "qwen/qwen3.8-27b"
        self.max_tokens = max_tokens or settings.vlm_max_tokens or 1024

    def parse_image_file(self, file_path: Union[str, Path]) -> List[Document]:
        """Loads an image from disk and processes it with the VLM."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {path}")

        image_bytes = path.read_bytes()
        return self.parse_image_bytes(image_bytes, filename=path.name)

    def parse_image_bytes(self, image_bytes: bytes, filename: str = "image.png") -> List[Document]:
        """Processes raw image bytes through Groq VLM using langchain-groq."""
        ext = Path(filename).suffix.lower().lstrip(".")
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type or not mime_type.startswith("image/"):
            mime_type = f"image/{ext}" if ext in ["png", "jpeg", "jpg", "webp", "gif", "bmp"] else "image/png"

        # Encode to Base64 data URL
        b64_encoded = base64.b64encode(image_bytes).decode("utf-8")
        data_uri = f"data:{mime_type};base64,{b64_encoded}"

        # If no genuine API key is configured or in mock/test placeholder, return fallback
        if not self.api_key or self.api_key.startswith("your_"):
            fallback_text = (
                f"[Image: {filename}]\n"
                f"Image format: {mime_type}. Size: {len(image_bytes)} bytes.\n"
                f"Visual content extracted via VLM mock processor."
            )
            return [
                Document(
                    page_content=fallback_text,
                    metadata={
                        "source": filename,
                        "file_type": ext,
                        "mime_type": mime_type,
                        "parser": "vlm_mock",
                    },
                )
            ]

        extracted_text = self._call_vlm(data_uri, filename)

        return [
            Document(
                page_content=extracted_text,
                metadata={
                    "source": filename,
                    "file_type": ext,
                    "mime_type": mime_type,
                    "parser": "langchain_groq_vlm",
                    "vlm_model": self.model,
                },
            )
        ]

    def _call_vlm(self, data_uri: str, filename: str) -> str:
        """Invokes Groq VLM using langchain-groq ChatGroq."""
        try:
            llm = ChatGroq(
                model=self.model,
                api_key=self.api_key,
                temperature=0.1,
                max_tokens=self.max_tokens,
            )

            msg = HumanMessage(
                content=[
                    {"type": "text", "text": VLM_IMAGE_EXTRACTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ]
            )

            response = llm.invoke([msg])
            content = str(response.content).strip()
            return content or f"[Image {filename}: Visual content processed]"

        except Exception as e:
            # Fallback for offline testing or unexpected network error
            print(f"Warning: VLM error analyzing image '{filename}' via langchain-groq ({e}). Falling back to visual description.")
            return f"[Image: {filename}]\nVisual description could not be fetched ({e})."
