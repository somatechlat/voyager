"""OCR processing with Tesseract and table extraction.

Extracts text from images and PDFs with preprocessing, confidence
scoring, and table detection.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import time
from io import BytesIO
from typing import Any

from django.conf import settings
from django.utils import timezone

from ..models import OCRJob

logger = logging.getLogger(__name__)

# Max concurrent OCR jobs
MAX_CONCURRENT_OCR: int = getattr(settings, "WS_MAX_CONCURRENT_OCR", 4)


def _check_tesseract() -> bool:
    """Check if Tesseract OCR is available.

    Returns:
        True if Tesseract is installed.
    """
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


class OCRProcessor:
    """Processes images and PDFs for text extraction.

    Uses Tesseract for OCR with preprocessing pipeline, and
    Camelot for structured table extraction from PDFs.
    """

    def __init__(self) -> None:
        """Initialize the OCR processor."""
        self.tesseract_available = _check_tesseract()

    def process_image(
        self,
        image_data: bytes,
        languages: list[str] | None = None,
        apply_preprocessing: bool = True,
    ) -> dict[str, Any]:
        """Process an image for text extraction.

        Args:
            image_data: Raw image bytes.
            languages: OCR language codes (e.g., ["eng", "fra"]).
            apply_preprocessing: Whether to apply image preprocessing.

        Returns:
            Dict with extracted text, confidence, words, lines, blocks.
        """
        if not self.tesseract_available:
            return {"error": "Tesseract OCR is not installed", "text": ""}

        try:
            from PIL import Image

            image = Image.open(BytesIO(image_data))
        except ImportError:
            return {"error": "Pillow is not installed", "text": ""}
        except Exception as exc:
            logger.error("Failed to open image: %s", exc)
            return {"error": f"Failed to open image: {exc}", "text": ""}

        preprocessing_steps: list[str] = []

        if apply_preprocessing:
            image, steps = self._preprocess_image(image)
            preprocessing_steps = steps

        lang_str = "+".join(languages or ["eng"])

        try:
            import pytesseract

            # Extract text with detailed data
            data = pytesseract.image_to_data(
                image, lang=lang_str, output_type=pytesseract.Output.DICT
            )

            words: list[dict[str, Any]] = []
            lines_dict: dict[int, list[dict[str, Any]]] = {}
            blocks_dict: dict[int, list[dict[str, Any]]] = {}
            full_text_parts: list[str] = []
            confidences: list[int] = []

            n_boxes = len(data["text"])
            for i in range(n_boxes):
                text = data["text"][i].strip()
                conf = int(data["conf"][i])

                if not text or conf < 0:
                    continue

                word_info: dict[str, Any] = {
                    "text": text,
                    "confidence": conf,
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "width": data["width"][i],
                    "height": data["height"][i],
                    "line_num": data["line_num"][i],
                    "block_num": data["block_num"][i],
                }
                words.append(word_info)
                confidences.append(conf)

                line_id = data["line_num"][i]
                if line_id not in lines_dict:
                    lines_dict[line_id] = []
                lines_dict[line_id].append(word_info)

                block_id = data["block_num"][i]
                if block_id not in blocks_dict:
                    blocks_dict[block_id] = []
                blocks_dict[block_id].append(word_info)

                if text:
                    full_text_parts.append(text)

            # Build lines
            lines: list[dict[str, Any]] = []
            for line_id, line_words in sorted(lines_dict.items()):
                line_text = " ".join(w["text"] for w in line_words)
                if line_text.strip():
                    avg_conf = sum(w["confidence"] for w in line_words) / len(line_words)
                    lines.append(
                        {
                            "text": line_text,
                            "confidence": round(avg_conf, 2),
                            "words": line_words,
                        }
                    )

            # Build blocks
            blocks: list[dict[str, Any]] = []
            for block_id, block_words in sorted(blocks_dict.items()):
                block_text = " ".join(w["text"] for w in block_words)
                if block_text.strip():
                    avg_conf = sum(w["confidence"] for w in block_words) / len(block_words)
                    blocks.append(
                        {
                            "text": block_text,
                            "confidence": round(avg_conf, 2),
                            "words": block_words,
                        }
                    )

            full_text = " ".join(full_text_parts)
            avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0

            # Correct common OCR errors
            corrected_text = self._correct_ocr_errors(full_text)

            return {
                "text": corrected_text,
                "confidence": avg_confidence,
                "word_count": len(words),
                "words": words,
                "lines": lines,
                "blocks": blocks,
                "preprocessing": preprocessing_steps,
            }

        except Exception as exc:
            logger.error("OCR processing failed: %s", exc)
            return {"error": f"OCR processing failed: {exc}", "text": ""}

    def process_pdf(
        self,
        pdf_path: str,
        languages: list[str] | None = None,
    ) -> dict[str, Any]:
        """Process a PDF for text and table extraction.

        Args:
            pdf_path: Path to the PDF file.
            languages: OCR language codes.

        Returns:
            Dict with text, tables, and metadata.
        """
        if not os.path.exists(pdf_path):
            return {"error": f"PDF not found: {pdf_path}", "text": "", "tables": []}

        all_text_parts: list[str] = []
        all_tables: list[dict[str, Any]] = []
        total_confidence = 0.0
        page_count = 0

        # Try Camelot first for table extraction
        try:
            import camelot

            tables = camelot.read_pdf(pdf_path, flavor="lattice")
            if tables.n == 0:
                tables = camelot.read_pdf(pdf_path, flavor="stream")

            for table in tables:
                all_tables.append(
                    {
                        "data": table.df.to_dict(orient="records"),
                        "accuracy": round(table.accuracy, 2) if hasattr(table, "accuracy") else 0.9,
                        "method": "lattice" if table.flavor == "lattice" else "stream",
                        "page": table.page,
                    }
                )
        except ImportError:
            logger.info("Camelot not installed; skipping table extraction")
        except Exception as exc:
            logger.warning("Camelot table extraction failed: %s", exc)

        # Convert PDF pages to images and OCR
        try:
            from pdf2image import convert_from_path

            images = convert_from_path(pdf_path, dpi=300)
            for page_num, image in enumerate(images, 1):
                img_bytes = BytesIO()
                image.save(img_bytes, format="PNG")
                result = self.process_image(img_bytes.getvalue(), languages)

                if "error" not in result:
                    all_text_parts.append(f"--- Page {page_num} ---\n{result['text']}")
                    total_confidence += result.get("confidence", 0)
                    page_count += 1

                    # If no tables from Camelot, try detecting tables in OCR text
                    if not all_tables:
                        detected_tables = self._detect_tables_in_text(result["text"])
                        all_tables.extend(detected_tables)

        except ImportError:
            logger.info("pdf2image not installed; trying direct text extraction")
            # Fallback to direct text extraction
            try:
                from PyPDF2 import PdfReader

                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        all_text_parts.append(text)
                        page_count += 1
            except ImportError:
                logger.warning("PyPDF2 not installed; no PDF text extraction available")
        except Exception as exc:
            logger.error("PDF processing failed: %s", exc)

        full_text = "\n\n".join(all_text_parts)
        avg_confidence = round(total_confidence / page_count, 2) if page_count > 0 else 0

        return {
            "text": full_text,
            "confidence": avg_confidence,
            "tables": all_tables,
            "page_count": page_count,
        }

    def process_job(self, job: OCRJob) -> None:
        """Execute an OCRJob and update its status.

        Args:
            job: The OCRJob to process.
        """
        job.status = OCRJob.Status.RUNNING
        job.started_at = timezone.now()
        job.save(update_fields=["status", "started_at"])

        start_time = time.time()
        languages = job.languages.split(",") if job.languages else ["eng"]

        try:
            if job.file_type == OCRJob.FileType.PDF:
                result = self.process_pdf(job.file_url, languages)
            else:
                # Read image file
                if job.file_url.startswith("http"):
                    import requests

                    response = requests.get(job.file_url, timeout=30)
                    image_data = response.content
                else:
                    with open(job.file_url, "rb") as f:
                        image_data = f.read()

                result = self.process_image(image_data, languages)

            processing_time = int((time.time() - start_time) * 1000)

            if "error" in result:
                job.status = OCRJob.Status.FAILED
                job.error_message = result["error"]
            else:
                job.status = OCRJob.Status.COMPLETED
                job.extracted_text = result.get("text", "")
                job.avg_confidence = Decimal(str(result.get("confidence", 0)))
                job.word_count = result.get("word_count", 0)
                job.words = result.get("words", [])
                job.lines = result.get("lines", [])
                job.blocks = result.get("blocks", [])
                job.tables = result.get("tables", [])
                job.preprocessing_applied = result.get("preprocessing", [])
                job.processing_time_ms = processing_time

            job.completed_at = timezone.now()
            job.save()

        except Exception as exc:
            job.status = OCRJob.Status.FAILED
            job.error_message = str(exc)
            job.completed_at = timezone.now()
            job.save(update_fields=["status", "error_message", "completed_at"])
            logger.error("OCR job %s failed: %s", job.id, exc)

    def _preprocess_image(self, image: Any) -> tuple[Any, list[str]]:
        """Apply preprocessing pipeline to enhance OCR quality.

        Args:
            image: PIL Image object.

        Returns:
            Tuple of (processed_image, list_of_steps_applied).
        """
        from PIL import ImageFilter

        steps: list[str] = []

        # Step 1: Convert to RGB if necessary
        if image.mode not in ("L", "RGB"):
            image = image.convert("RGB")
            steps.append("color_conversion")

        # Step 2: Convert to grayscale
        if image.mode == "RGB":
            image = image.convert("L")
            steps.append("grayscale")

        # Step 3: Resize if too small (target minimum 300 DPI equivalent)
        min_dimension = 1000
        width, height = image.size
        if width < min_dimension or height < min_dimension:
            scale = max(min_dimension / width, min_dimension / height)
            new_size = (int(width * scale), int(height * scale))
            image = image.resize(new_size, Image.LANCZOS)
            steps.append("upscale")

        # Step 4: Denoise
        image = image.filter(ImageFilter.MedianFilter(size=3))
        steps.append("denoise")

        # Step 5: Enhance contrast
        from PIL import ImageEnhance

        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        steps.append("contrast_enhance")

        return image, steps

    def _correct_ocr_errors(self, text: str) -> str:
        """Correct common OCR misreadings.

        Args:
            text: OCR-extracted text.

        Returns:
            Corrected text.
        """
        corrections: dict[str, str] = {
            "l": "1",
            "O": "0",
            "|": "I",
        }
        # Apply conservative corrections in numeric contexts
        import re

        # l -> 1 when surrounded by digits
        text = re.sub(r"(?<=\d)l(?=\d)", "1", text)
        text = re.sub(r"(?<=\d)L(?=\d)", "1", text)

        return text

    def _detect_tables_in_text(self, text: str) -> list[dict[str, Any]]:
        """Detect table-like structures in OCR text.

        Args:
            text: OCR-extracted text.

        Returns:
            List of detected table dicts.
        """
        tables: list[dict[str, Any]] = []
        lines = text.split("\n")

        # Look for rows with consistent delimiters (tabs, pipes, multiple spaces)
        table_lines: list[str] = []
        for line in lines:
            if "|" in line or "\t" in line or len(re.split(r"\s{2,}", line.strip())) > 2:
                table_lines.append(line)
            elif table_lines:
                if len(table_lines) >= 2:
                    tables.append(
                        {
                            "data": [{"row": l} for l in table_lines],
                            "accuracy": 0.7,
                            "method": "text_heuristic",
                            "page": 0,
                        }
                    )
                table_lines = []

        if len(table_lines) >= 2:
            tables.append(
                {
                    "data": [{"row": l} for l in table_lines],
                    "accuracy": 0.7,
                    "method": "text_heuristic",
                    "page": 0,
                }
            )

        return tables



