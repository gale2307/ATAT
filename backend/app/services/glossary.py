"""Domain glossary loading."""
import json
from pathlib import Path

DOMAINS_DIR = Path(__file__).parent.parent / "glossary" / "domains"


def load_glossary(domain: str) -> dict[str, str]:
    """Load the glossary for a given domain ID. Returns empty dict if not found."""
    path = DOMAINS_DIR / f"{domain}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}
