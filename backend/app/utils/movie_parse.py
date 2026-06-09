import re


def _strip_markdown(text: str) -> str:
    return re.sub(r"\*+", "", text).strip()


def parse_title_year_from_text(text: str) -> tuple[str, int | None]:
    """Extract a clean title and year from list-item or bloated title text."""
    body = _strip_markdown(text).strip()
    if not body:
        return text, None

    # Title (Year): reason — Gemini numbered-list format (colon may end the line)
    match = re.match(r"^(.+?)\s*\((\d{4})\)\s*:", body)
    if match:
        return match.group(1).strip(), int(match.group(2))

    match = re.match(r"^(.+?)\s*\((\d{4})\)\s*$", body)
    if match:
        return match.group(1).strip(), int(match.group(2))

    # Title (Year) - reason
    match = re.match(r"^(.+?)\s*\((\d{4})\)\s*[-–—]\s*", body)
    if match:
        return match.group(1).strip(), int(match.group(2))

    match = re.match(r"^([^:]{2,80})\s*:", body)
    if match:
        return match.group(1).strip(), None

    if len(body) <= 80:
        return body.rstrip(":").strip(), None
    return text, None


def chip_display_title(raw_title: str, parsed_title: str | None = None) -> str:
    """Short label for citation chips — never show AI recommendation prose."""
    if parsed_title and parsed_title.strip():
        candidate = parsed_title.strip()
    else:
        candidate, _ = parse_title_year_from_text(raw_title)

    if looks_like_bloated_title(candidate):
        short, _ = parse_title_year_from_text(candidate)
        if short and not looks_like_bloated_title(short):
            return short

    if looks_like_bloated_title(raw_title):
        short, _ = parse_title_year_from_text(raw_title)
        if short and not looks_like_bloated_title(short):
            return short

    return candidate if candidate and len(candidate) <= 80 else (parsed_title or raw_title)[:80].rstrip()


def looks_like_bloated_title(title: str) -> bool:
    return len(title) > 80 or bool(re.search(r"\(\d{4}\)\s*:", title))
