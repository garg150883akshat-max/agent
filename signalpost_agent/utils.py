from __future__ import annotations
import hashlib, re, unicodedata
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

STOPWORDS = {"as", "asa", "nuf", "da", "sa", "stiftelsen", "the", "and", "og", "i", "of", "a"}

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def norm_text(s: str | None) -> str:
    s = s or ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def norm_company(s: str | None) -> str:
    parts = [p for p in norm_text(s).split() if p not in STOPWORDS]
    return " ".join(parts)

def token_overlap(a: str, b: str) -> float:
    aa, bb = set(norm_company(a).split()), set(norm_company(b).split())
    if not aa or not bb: return 0.0
    return len(aa & bb) / len(aa | bb)

def normalize_orgnr(v: str | int) -> str:
    digits = re.sub(r"\D", "", str(v))
    if len(digits) != 9: raise ValueError(f"invalid organisation number: {v}")
    return digits

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def same_host(base: str, url: str) -> bool:
    a, b = urlparse(base), urlparse(url)
    ha=(a.hostname or "").lower(); hb=(b.hostname or "").lower();
    if ha.startswith("www."): ha=ha[4:]
    if hb.startswith("www."): hb=hb[4:]
    return ha == hb

def clean_url(base: str, href: str) -> str | None:
    if not href: return None
    u = urljoin(base, href)
    p = urlparse(u)
    if p.scheme not in {"http", "https"}: return None
    return u.split("#", 1)[0]

def first_nonempty(*xs):
    for x in xs:
        if x not in (None, "", [], {}): return x
    return None
