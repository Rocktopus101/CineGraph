import csv
import hashlib
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from io import TextIOWrapper
from pathlib import Path


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def normalize_letterboxd_uri(uri: str) -> str:
    """Strip entry-specific slug, keep film URI base."""
    if not uri:
        return ""
    uri = uri.rstrip("/")
    # Entry URIs like boxd.it/7J83Yv have longer slugs; film URIs are shorter
    match = re.search(r"(boxd\.it/[a-zA-Z0-9]+)", uri)
    if match:
        slug = match.group(1)
        # Film URIs are typically 4-6 chars after boxd.it/
        parts = slug.split("/")
        if len(parts) == 2 and len(parts[1]) <= 6:
            return slug
        return parts[0] + "/" + parts[1][:6] if len(parts) == 2 else slug
    return uri


def row_fingerprint(name: str, year: str, watched_date: str, rating: str, review: str) -> str:
    content = f"{name}|{year}|{watched_date}|{rating}|{review}"
    return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class ParsedFilm:
    name: str
    year: int | None
    letterboxd_uri: str
    watched_date: str | None = None
    rating: float | None = None
    rewatch: bool = False
    tags: str | None = None
    review_text: str | None = None
    diary_uri: str | None = None
    source: str = "watched"
    fingerprint: str = ""


@dataclass
class ParsedExport:
    username: str | None = None
    films: dict[str, ParsedFilm] = field(default_factory=dict)
    watchlist: list[ParsedFilm] = field(default_factory=list)


def _parse_date(value: str) -> str | None:
    if not value:
        return None
    return value.strip()


def _parse_rating(value: str) -> float | None:
    if not value or not value.strip():
        return None
    try:
        return float(value.strip())
    except ValueError:
        return None


def _film_key(name: str, year: int | None, uri: str) -> str:
    return f"{normalize_title(name)}|{year or ''}|{normalize_letterboxd_uri(uri)}"


class LetterboxdParser:
    REQUIRED_FILES = {"watched.csv", "ratings.csv"}

    def extract_zip(self, zip_path: Path, dest: Path) -> None:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest)

    def validate_export(self, export_dir: Path) -> list[str]:
        missing = []
        for f in self.REQUIRED_FILES:
            if not (export_dir / f).exists():
                missing.append(f)
        return missing

    def parse_profile(self, export_dir: Path) -> str | None:
        profile_path = export_dir / "profile.csv"
        if not profile_path.exists():
            return None
        with open(profile_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                return row.get("Username")
        return None

    def _read_csv(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        with open(path, newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    def parse(self, export_dir: Path) -> ParsedExport:
        result = ParsedExport(username=self.parse_profile(export_dir))
        films: dict[str, ParsedFilm] = {}

        # Start with watched.csv
        for row in self._read_csv(export_dir / "watched.csv"):
            name = row.get("Name", "").strip()
            year = int(row["Year"]) if row.get("Year", "").strip().isdigit() else None
            uri = row.get("Letterboxd URI", "").strip()
            key = _film_key(name, year, uri)
            films[key] = ParsedFilm(
                name=name,
                year=year,
                letterboxd_uri=normalize_letterboxd_uri(uri),
                watched_date=_parse_date(row.get("Date", "")),
                source="watched",
                fingerprint=row_fingerprint(name, str(year or ""), row.get("Date", ""), "", ""),
            )

        # Merge ratings.csv
        for row in self._read_csv(export_dir / "ratings.csv"):
            name = row.get("Name", "").strip()
            year = int(row["Year"]) if row.get("Year", "").strip().isdigit() else None
            uri = row.get("Letterboxd URI", "").strip()
            key = _film_key(name, year, uri)
            rating = _parse_rating(row.get("Rating", ""))
            if key in films:
                films[key].rating = rating
                films[key].watched_date = films[key].watched_date or _parse_date(row.get("Date", ""))
            else:
                films[key] = ParsedFilm(
                    name=name,
                    year=year,
                    letterboxd_uri=normalize_letterboxd_uri(uri),
                    watched_date=_parse_date(row.get("Date", "")),
                    rating=rating,
                    source="ratings",
                    fingerprint=row_fingerprint(name, str(year or ""), row.get("Date", ""), row.get("Rating", ""), ""),
                )

        # Merge diary.csv (more detailed)
        for row in self._read_csv(export_dir / "diary.csv"):
            name = row.get("Name", "").strip()
            year = int(row["Year"]) if row.get("Year", "").strip().isdigit() else None
            uri = row.get("Letterboxd URI", "").strip()
            key = _film_key(name, year, uri)
            diary_uri = uri
            rating = _parse_rating(row.get("Rating", ""))
            watched = _parse_date(row.get("Watched Date", "") or row.get("Date", ""))
            rewatch = row.get("Rewatch", "").strip().lower() == "yes"
            tags = row.get("Tags", "").strip() or None
            fp = row_fingerprint(name, str(year or ""), watched or "", str(rating or ""), "")
            if key in films:
                f = films[key]
                f.watched_date = watched or f.watched_date
                f.rating = rating if rating is not None else f.rating
                f.rewatch = rewatch
                f.tags = tags
                f.diary_uri = diary_uri
                f.source = "diary"
                f.fingerprint = fp
            else:
                films[key] = ParsedFilm(
                    name=name,
                    year=year,
                    letterboxd_uri=normalize_letterboxd_uri(uri),
                    watched_date=watched,
                    rating=rating,
                    rewatch=rewatch,
                    tags=tags,
                    diary_uri=diary_uri,
                    source="diary",
                    fingerprint=fp,
                )

        # Merge reviews.csv (reviews win on text)
        for row in self._read_csv(export_dir / "reviews.csv"):
            name = row.get("Name", "").strip()
            year = int(row["Year"]) if row.get("Year", "").strip().isdigit() else None
            uri = row.get("Letterboxd URI", "").strip()
            key = _film_key(name, year, uri)
            review = row.get("Review", "").strip() or None
            rating = _parse_rating(row.get("Rating", ""))
            watched = _parse_date(row.get("Watched Date", "") or row.get("Date", ""))
            fp = row_fingerprint(name, str(year or ""), watched or "", str(rating or ""), review or "")
            if key in films:
                f = films[key]
                if review:
                    f.review_text = review
                f.rating = rating if rating is not None else f.rating
                f.watched_date = watched or f.watched_date
                f.diary_uri = uri or f.diary_uri
                f.source = "review"
                f.fingerprint = fp
            else:
                films[key] = ParsedFilm(
                    name=name,
                    year=year,
                    letterboxd_uri=normalize_letterboxd_uri(uri),
                    watched_date=watched,
                    rating=rating,
                    review_text=review,
                    diary_uri=uri,
                    source="review",
                    fingerprint=fp,
                )

        result.films = films

        # Parse watchlist
        for row in self._read_csv(export_dir / "watchlist.csv"):
            name = row.get("Name", "").strip()
            year = int(row["Year"]) if row.get("Year", "").strip().isdigit() else None
            uri = row.get("Letterboxd URI", "").strip()
            result.watchlist.append(
                ParsedFilm(
                    name=name,
                    year=year,
                    letterboxd_uri=normalize_letterboxd_uri(uri),
                    source="watchlist",
                )
            )

        return result
