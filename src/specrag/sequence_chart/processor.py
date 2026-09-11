"""
Sequence Chart Processing Module

This module provides functionality to parse, render, and vectorize
sequence diagrams (e.g., Mermaid sequence charts).
"""

import hashlib
import re
from pathlib import Path
from typing import Optional

from specrag.config import DOCUMENTS_DIR, SequenceChartConfig, ensure_directories, settings
from specrag.sequence_chart.models import SequenceChart, SequenceChartElement


class SequenceChartProcessor:
    """
    Handles sequence chart parsing, rendering, and vectorization.

    Supports Mermaid sequence diagram syntax.
    """

    def __init__(self, config: SequenceChartConfig | None = None):
        """
        Initialize the SequenceChartProcessor.

        Args:
            config: Sequence chart configuration.
        """
        self.config = config or settings.sequence_chart
        ensure_directories()

    def parse_mermaid(self, content: str, source_file: str | None = None) -> SequenceChart:
        """
        Parse a Mermaid sequence diagram.

        Args:
            content: Mermaid sequence diagram content.
            source_file: Optional source file path.

        Returns:
            Parsed SequenceChart object.
        """
        # Generate chart ID
        chart_id = hashlib.md5(content.encode()).hexdigest()[:8]

        chart = SequenceChart(chart_id=chart_id, raw_content=content, source_file=source_file)

        lines = content.strip().split("\n")

        for line in lines:
            line = line.strip()

            # Skip empty lines and diagram declaration
            if not line or line.startswith("sequenceDiagram"):
                continue

            # Parse title
            if line.startswith("title"):
                chart.title = line.replace("title", "").strip()
                continue

            # Parse participant
            participant_match = re.match(r"participant\s+(\w+)(?:\s+as\s+(.+))?", line)
            if participant_match:
                participant_name = participant_match.group(2) or participant_match.group(1)
                chart.participants.append(participant_name)
                continue

            # Parse message arrows (various arrow types)
            message_patterns = [
                r"(\w+)\s*->>>\s*(\w+)\s*:\s*(.+)",  # ->>>
                r"(\w+)\s*-->>\s*(\w+)\s*:\s*(.+)",  # -->>
                r"(\w+)\s*->>?\s*(\w+)\s*:\s*(.+)",  # ->> or ->
                r"(\w+)\s*-->\s*(\w+)\s*:\s*(.+)",  # -->
            ]

            for pattern in message_patterns:
                message_match = re.match(pattern, line)
                if message_match:
                    elem = SequenceChartElement(element_type="message", source=message_match.group(1), target=message_match.group(2), message=message_match.group(3))
                    chart.elements.append(elem)

                    # Auto-add participants if not already added
                    for p in [elem.source, elem.target]:
                        if p and p not in chart.participants:
                            chart.participants.append(p)
                    break

            # Parse notes
            note_match = re.match(r"Note\s+(left|right|over)\s+(?:of\s+)?(\w+)\s*:\s*(.+)", line, re.IGNORECASE)
            if note_match:
                elem = SequenceChartElement(element_type="note", target=note_match.group(2), description=note_match.group(3))
                chart.elements.append(elem)

        # Generate description
        chart.generate_description()

        return chart

    def extract_from_markdown(self, markdown_content: str, source_file: str | None = None) -> list[SequenceChart]:
        """
        Extract sequence charts from markdown content.

        Args:
            markdown_content: Markdown content with mermaid code blocks.
            source_file: Optional source file path.

        Returns:
            List of parsed SequenceChart objects.
        """
        charts = []

        # Find mermaid code blocks
        pattern = r"```mermaid\s*\n(.*?)\n```"
        matches = re.findall(pattern, markdown_content, re.DOTALL)

        for match in matches:
            if "sequenceDiagram" in match:
                chart = self.parse_mermaid(match, source_file)
                charts.append(chart)

        return charts

    def export_image(self, chart: SequenceChart, output_dir: Path | None = None, format: str | None = None) -> str | None:
        """Export a chart with Mermaid or a lightweight placeholder."""
        from specrag.sequence_chart.renderer import render_chart

        output_dir = output_dir or DOCUMENTS_DIR / "charts"
        output_dir = Path(output_dir)
        format = format or self.config.export_format
        output_file = output_dir / f"chart_{chart.chart_id}.{format}"
        if render_chart(chart, output_file):
            chart.image_path = str(output_file)
            return chart.image_path
        return None

    def process_file(self, file_path: Path, export_images: bool = True) -> list[SequenceChart]:
        """
        Process a file to extract and optionally export sequence charts.

        Args:
            file_path: Path to the file to process.
            export_images: Whether to export images.

        Returns:
            List of processed SequenceChart objects.
        """
        file_path = Path(file_path)
        content = file_path.read_text(encoding="utf-8")

        charts = self.extract_from_markdown(content, str(file_path))

        if export_images:
            for chart in charts:
                self.export_image(chart)

        print(f"Processed {file_path.name}: found {len(charts)} sequence charts")
        return charts

    def get_vectorization_data(self, charts: list[SequenceChart]) -> list[dict]:
        """
        Prepare chart data for vectorization.

        The description and metadata will be used for vector embedding.

        Args:
            charts: List of SequenceChart objects.

        Returns:
            List of dicts ready for vectorization.
        """
        data = []
        for chart in charts:
            data.append(
                {
                    "chunk_id": f"chart_{chart.chart_id}",
                    "content": chart.description,
                    "metadata": {
                        "type": "sequence_chart",
                        "title": chart.title or "",
                        "participants": ", ".join(chart.participants),
                        "image_path": chart.image_path or "",
                        "source_file": chart.source_file or "",
                    },
                    "source_file": chart.source_file,
                }
            )
        return data


# Global processor instance
_processor: SequenceChartProcessor | None = None


def get_chart_processor() -> SequenceChartProcessor:
    """Get or create the global chart processor instance."""
    global _processor
    if _processor is None:
        _processor = SequenceChartProcessor()
    return _processor
