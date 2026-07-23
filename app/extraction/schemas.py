"""Semantic content block schema, matching the project brief section 6:
{"content_id": "...", "type": "...", "context": "...", "source": "...", "translate": true}
"""
from __future__ import annotations

from pydantic import BaseModel


class ContentBlock(BaseModel):
    content_id: str
    type: str
    context: str
    source: str
    translate: bool
