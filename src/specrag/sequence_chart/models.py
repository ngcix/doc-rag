"""Sequence chart domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SequenceChartElement:
    element_type: str
    source: str | None = None
    target: str | None = None
    message: str | None = None
    description: str | None = None


@dataclass
class SequenceChart:
    chart_id: str
    title: str | None = None
    participants: list[str] = field(default_factory=list)
    elements: list[SequenceChartElement] = field(default_factory=list)
    raw_content: str = ""
    description: str = ""
    image_path: str | None = None
    source_file: str | None = None

    def to_dict(self) -> dict:
        return {
            "chart_id": self.chart_id,
            "title": self.title,
            "participants": self.participants,
            "description": self.description,
            "image_path": self.image_path,
            "source_file": self.source_file,
            "element_count": len(self.elements),
        }

    def generate_description(self) -> str:
        parts = []
        if self.title:
            parts.append(f"Sequence Diagram: {self.title}")
        if self.participants:
            parts.append(f"Participants: {', '.join(self.participants)}")
        flow = []
        for element in self.elements:
            if element.element_type == "message" and element.source and element.target:
                flow.append(f"{element.source} sends '{element.message or 'communicates'}' to {element.target}")
            elif element.element_type == "note" and element.description:
                flow.append(f"Note: {element.description}")
        if flow:
            parts.append("Flow:\n" + "\n".join(f"  - {line}" for line in flow))
        self.description = "\n\n".join(parts)
        return self.description
