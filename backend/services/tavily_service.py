import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from tavily import TavilyClient
from backend.config import settings

logger = logging.getLogger(__name__)

# Tracking query parameters to strip for canonical URL calculation
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "fbclid", "gclid", "msclkid", "mc_cid", "mc_eid", "igshid",
    "spm", "_hsenc", "_hsmi", "source", "feature"
}

# Time-sensitive keywords that trigger time-aware research prioritization
TIME_SENSITIVE_KEYWORDS = [
    "latest", "current", "recent", "this year", "this month",
    "this week", "today", "new", "emerging", "2026", "2025"
]

# Domain classification rules
GOV_DOMAINS = {".gov", ".mil", ".gov.uk", ".gov.in"}
RESEARCH_DOMAINS = {
    "arxiv.org", "nature.com", "science.org", "biorxiv.org",
    "medrxiv.org", "mit.edu", "stanford.edu", "harvard.edu",
    "berkeley.edu", "cell.com", "ieee.org", "acm.org"
}
INDUSTRY_PUBLICATIONS = {
    "techcrunch.com", "venturebeat.com", "reuters.com", "bloomberg.com",
    "wsj.com", "ft.com", "forbes.com", "wired.com", "theverge.com",
    "theinformation.com", "sifted.eu", "pitchbook.com", "crunchbase.com"
}


class TavilyServiceError(Exception):
    """Custom exception for Tavily search failures."""
    pass


def canonicalize_url(url: str) -> str:
    """
    Produce a normalized canonical URL by:
    - Lowercasing scheme and host
    - Removing standard port numbers
    - Stripping trailing slash
    - Removing tracking query parameters (utm_*, ref, fbclid, etc.)
    - Removing fragment (#...)
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]

        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        # Filter out tracking query params
        query_dict = parse_qs(parsed.query, keep_blank_values=False)
        clean_query = {
            k: v for k, v in query_dict.items()
            if k.lower() not in TRACKING_PARAMS
        }
        encoded_query = urlencode(clean_query, doseq=True)

        return urlunparse((scheme, netloc, path, "", encoded_query, ""))
    except Exception:
        return url.strip().rstrip("/")


def classify_source_type(url: str, title: str) -> str:
    """Classify the source based on domain authority and structure."""
    try:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.lower()
        if hostname.startswith("www."):
            hostname = hostname[4:]

        for gov in GOV_DOMAINS:
            if hostname.endswith(gov):
                return "government"

        if hostname in RESEARCH_DOMAINS or any(hostname.endswith(edu) for edu in [".edu", ".ac.uk"]):
            return "research_institution"

        if hostname in INDUSTRY_PUBLICATIONS:
            return "industry_publication"

        # Check for official company signals in domain or URL path
        if "blog." in hostname or "/blog" in url or "/news" in url or "/press" in url:
            return "official_company"

        return "web"
    except Exception:
        return "web"


def parse_publication_date(date_str: Optional[str]) -> Tuple[Optional[str], Optional[datetime]]:
    """
    Parse date string safely into (ISO_string, datetime_object).
    Returns (None, None) if missing or unparseable. Never invents a date.
    """
    if not date_str or not isinstance(date_str, str) or not date_str.strip():
        return None, None

    cleaned = date_str.strip()
    # Try common formats
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y/%m/%d",
    ):
        try:
            dt = datetime.strptime(cleaned, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.date().isoformat(), dt
        except ValueError:
            continue

    # Regex fallback for YYYY-MM-DD
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", cleaned)
    if match:
        try:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            dt = datetime(year, month, day, tzinfo=timezone.utc)
            return dt.date().isoformat(), dt
        except ValueError:
            pass

    # Regex fallback for just a 4-digit year
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", cleaned)
    if year_match:
        year = int(year_match.group(1))
        dt = datetime(year, 1, 1, tzinfo=timezone.utc)
        return str(year), dt

    return None, None


def compute_freshness_label(pub_dt: Optional[datetime], now_dt: Optional[datetime] = None) -> Tuple[Optional[str], bool]:
    """
    Determine human-readable freshness label and whether source is historical.
    Sources older than ~2.5 years are tagged as historical context.
    """
    if not pub_dt:
        return None, False

    now = now_dt or datetime.now(timezone.utc)
    diff = now - pub_dt
    days = diff.days

    # Future date safeguard
    if days < 0:
        return "Recent", False

    # Historical stale threshold: > 900 days (approx 2.5 years)
    if days > 900:
        return f"Historical context ({pub_dt.year})", True

    if days == 0:
        return "Today", False
    if days == 1:
        return "Yesterday", False
    if days < 7:
        return f"{days} days ago", False
    if days < 30:
        weeks = max(1, days // 7)
        return f"{weeks} week{'s' if weeks > 1 else ''} ago", False
    if days < 365:
        months = max(1, days // 30)
        return f"{months} month{'s' if months > 1 else ''} ago", False

    years = max(1, days // 365)
    return f"{years} year{'s' if years > 1 else ''} ago", False


class TavilyService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = settings.TAVILY_API_KEY if api_key is None else api_key
        self._client: Optional[TavilyClient] = None
        if self.api_key and self.api_key.strip():
            try:
                self._client = TavilyClient(api_key=self.api_key.strip())
            except Exception as e:
                logger.error(f"Failed to initialize TavilyClient: {e}")

    def is_configured(self) -> bool:
        return self._client is not None

    def search(
        self,
        query: str,
        max_results: int = 6,
        search_depth: str = "basic"
    ) -> List[Dict[str, Any]]:
        """
        Execute web search via Tavily and return deduplicated, normalized, freshness-tagged sources.
        """
        if not self.is_configured():
            raise TavilyServiceError(
                "Tavily API key is not configured. Please set TAVILY_API_KEY in your .env file."
            )

        if not query or not query.strip():
            return []

        clean_query = query.strip()
        is_time_sensitive = any(kw in clean_query.lower() for kw in TIME_SENSITIVE_KEYWORDS)

        # Enhance query with temporal intent if user explicitly requested current info
        search_query = clean_query
        topic_mode = "general"
        if is_time_sensitive:
            topic_mode = "news"
            # Ensure query has explicit keywords for current signals
            if not any(k in clean_query.lower() for k in ["2026", "2025", "latest", "recent"]):
                search_query = f"{clean_query} latest 2026 news updates"

        try:
            logger.info(f"Tavily searching: '{search_query}' (topic_mode={topic_mode})")
            response = self._client.search(
                query=search_query,
                max_results=max_results + 3,  # Fetch slightly more to account for dedup
                search_depth=search_depth,
                topic=topic_mode if topic_mode == "news" else "general",
            )
            raw_results = response.get("results", [])

            now_utc = datetime.now(timezone.utc)
            retrieved_at_str = now_utc.isoformat()

            seen_canonical_urls: Set[str] = set()
            seen_domain_titles: Set[str] = set()
            normalized_results: List[Dict[str, Any]] = []

            for item in raw_results:
                raw_url = item.get("url", "").strip()
                if not raw_url:
                    continue

                canonical_url = canonicalize_url(raw_url)
                if canonical_url in seen_canonical_urls:
                    continue
                seen_canonical_urls.add(canonical_url)

                title = item.get("title", "").strip() or canonical_url
                content = item.get("content", "").strip()

                # Domain + title normalization deduplication
                domain = urlparse(canonical_url).hostname or ""
                normalized_title_slug = re.sub(r"[^a-z0-9]", "", title.lower())[:15]
                domain_title_key = f"{domain}:{normalized_title_slug}"
                if domain_title_key in seen_domain_titles:
                    continue
                seen_domain_titles.add(domain_title_key)

                # Date parsing & freshness tagging
                raw_date = item.get("published_date")
                parsed_date_str, pub_dt = parse_publication_date(raw_date)
                freshness_label, is_historical = compute_freshness_label(pub_dt, now_utc)

                source_type = classify_source_type(canonical_url, title)

                normalized_results.append({
                    "title": title,
                    "url": raw_url,
                    "snippet": content,
                    "published_at": parsed_date_str,
                    "source_type": source_type,
                    "retrieved_at": retrieved_at_str,
                    "freshness_label": freshness_label,
                    "is_historical": is_historical,
                })

            # Sort sources: prioritize current non-historical sources and high-authority publications
            def sort_key(s: Dict[str, Any]):
                # Prioritize: non-historical (0), has published date (0), source authority
                hist_score = 1 if s.get("is_historical") else 0
                has_date_score = 0 if s.get("published_at") else 1
                authority_score = 0 if s.get("source_type") in ("official_company", "government", "research_institution", "industry_publication") else 1
                return (hist_score, authority_score, has_date_score)

            normalized_results.sort(key=sort_key)
            return normalized_results[:max_results]

        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            raise TavilyServiceError(f"Current web research could not be completed: {str(e)}")


tavily_service = TavilyService()
