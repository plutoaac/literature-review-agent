import json
import re
from typing import Any, Dict


class JsonExtractionError(ValueError):
    """Raised when an LLM response does not contain a JSON object."""


def extract_json_object(text: str) -> Dict[str, Any]:
    """Extract the first JSON object from a possibly wrapped LLM response."""
    if not text or not text.strip():
        raise JsonExtractionError("empty response")

    candidates = [text.strip(), *_extract_fenced_blocks(text)]
    decoder = json.JSONDecoder()

    for candidate in candidates:
        candidate = candidate.strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        for index, char in enumerate(candidate):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(candidate[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

    raise JsonExtractionError("no JSON object found")


def _extract_fenced_blocks(text: str) -> list[str]:
    pattern = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
    return [match.group(1).strip() for match in pattern.finditer(text)]
