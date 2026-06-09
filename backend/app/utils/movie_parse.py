import re


def parse_title_year_from_text(text: str) -> tuple[str, int | None]:
    """Extract a clean title and year from list-item or bloated title text."""
    body = re.sub(r"\*+", "", text).strip()
    if not body:
        return text, None

    match = re.match(r"^(.+?)\s*\((\d{4})\)\s*:\s", body)
    if match:
        return match.group(1).strip(), int(match.group(2))

    match = re.match(r"^(.+?)\s*\((\d{4})\)\s*$", body)
    if match:
        return match.group(1).strip(), int(match.group(2))

    match = re.match(r"^([^:]{2,80})\s*:\s", body)
    if match:
        return match.group(1).strip(), None

    if len(body) <= 80:
        return body.rstrip(":").strip(), None
    return text, None


def looks_like_bloated_title(title: str) -> bool:
    return len(title) > 80 or bool(re.search(r"\(\d{4}\)\s*:", title))
