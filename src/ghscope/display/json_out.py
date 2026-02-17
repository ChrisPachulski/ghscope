"""JSON serialization for --json flag."""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime
from typing import Any

from rich.console import Console

console = Console()


class _Encoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def print_json(data: Any) -> None:
    """Print data as formatted JSON to stdout."""
    console.print_json(json.dumps(data, cls=_Encoder, indent=2))
