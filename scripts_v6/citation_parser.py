"""
citation_parser.py — Taiwan legal citation parser and normalizer.

Handles statutory citations (民法第767條第1項前段), court decision citations
(最高法院112年度台上字第1234號判決), and mixed text extraction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Citation:
    """Structured representation of a Taiwan legal citation."""

    raw: str                        # original text as found
    citation_type: str              # "statutory" | "case"
    law_body: Optional[str] = None  # 民法, 刑法, 刑事訴訟法, …
    article: Optional[str] = None   # 767
    paragraph: Optional[str] = None # 1 (第1項)
    subparagraph: Optional[str] = None  # 1 (第1款)
    segment: Optional[str] = None   # 前段 | 後段 | 中段
    court: Optional[str] = None     # 最高法院 | 台灣高等法院 | …
    year: Optional[str] = None      # 112
    case_type: Optional[str] = None # 台上字 | 上字 | …
    case_no: Optional[str] = None   # 1234
    case_kind: Optional[str] = None # 判決 | 裁定 | 決議
    canonical: str = field(default="", init=False)

    def __post_init__(self):
        self.canonical = _build_canonical(self)

    def __str__(self) -> str:
        return self.canonical or self.raw


def _build_canonical(c: Citation) -> str:
    """Reconstruct the normalised canonical string from parsed fields."""
    if c.citation_type == "statutory":
        parts = []
        if c.law_body:
            parts.append(c.law_body)
        if c.article:
            parts.append(f"第{c.article}條")
        if c.paragraph:
            parts.append(f"第{c.paragraph}項")
        if c.subparagraph:
            parts.append(f"第{c.subparagraph}款")
        if c.segment:
            parts.append(c.segment)
        return "".join(parts)

    elif c.citation_type == "case":
        parts = []
        if c.court:
            parts.append(c.court)
        if c.year:
            parts.append(f"{c.year}年度")
        if c.case_type:
            parts.append(f"{c.case_type}第")
        if c.case_no:
            parts.append(f"{c.case_no}號")
        if c.case_kind:
            parts.append(c.case_kind)
        return "".join(parts)

    return c.raw


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Known law bodies (order matters — longer names first to avoid partial match)
_LAW_BODIES = [
    "中華民國憲法",
    "憲法訴訟法",
    "行政訴訟法",
    "行政程序法",
    "行政執行法",
    "公司法",
    "票據法",
    "海商法",
    "保險法",
    "著作權法",
    "商標法",
    "專利法",
    "土地法",
    "消費者保護法",
    "勞動基準法",
    "勞工保險條例",
    "家事事件法",
    "非訟事件法",
    "破產法",
    "強制執行法",
    "刑事訴訟法",
    "民事訴訟法",
    "民法",
    "刑法",
]

_LAW_BODY_PATTERN = "|".join(re.escape(lb) for lb in _LAW_BODIES)

# Statutory citation:  LAW第NNN條[第NN項][第NN款][前段|後段|中段]
_STATUTORY_RE = re.compile(
    r"(?P<law>" + _LAW_BODY_PATTERN + r")"
    r"第(?P<article>\d+(?:-\d+)?)條"
    r"(?:第(?P<paragraph>\d+)項)?"
    r"(?:第(?P<subparagraph>\d+)款)?"
    r"(?P<segment>前段|後段|中段)?",
    re.UNICODE,
)

# Court citation:  COURT YY年度CASETYPE字第NNNN號判決/裁定
_COURT_RE = re.compile(
    r"(?P<court>最高法院|台灣高等法院|臺灣高等法院|台灣高等法院[高雄台中台南花蓮]*分院"
    r"|臺灣高等法院[高雄台中台南花蓮]*分院"
    r"|台灣[\u4e00-\u9fff]{2,4}地方法院|臺灣[\u4e00-\u9fff]{2,4}地方法院)"
    r"(?P<year>\d{2,3})年度"
    r"(?P<case_type>台上字|臺上字|台抗字|臺抗字|台再字|臺再字"
    r"|上字|上易字|上訴字|重上字|訴字|易字|簡字|簡上字|家上字|家訴字|勞上字|勞訴字)"
    r"第(?P<case_no>\d+)號"
    r"(?P<case_kind>判決|裁定|決議)?",
    re.UNICODE,
)

# Simplified alternative court citation without year (rare, for robustness)
_COURT_SHORT_RE = re.compile(
    r"(?P<court>最高法院|台灣高等法院|臺灣高等法院)"
    r"(?P<case_type>台上|臺上|台抗|臺抗)"
    r"(?P<case_no>\d+)"
    r"號(?P<case_kind>判決|裁定)?",
    re.UNICODE,
)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class TaiwanLegalCitationParser:
    """
    Parse, normalize, and compare Taiwan legal citations.

    Supports
    --------
    Statutory citations
        民法第767條
        民法第767條第1項
        民法第767條第1項前段
        刑法第339條
        刑事訴訟法第156條第1項
        民事訴訟法第400條第1項
        中華民國憲法第15條

    Court decisions
        最高法院112年度台上字第1234號判決
        台灣高等法院111年度上字第5678號判決
    """

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def parse(self, citation_text: str) -> list[Citation]:
        """
        Extract all citations from *citation_text*.

        Works on both short canonical citations and long prose passages.
        Returns a list of :class:`Citation` objects (may be empty).
        """
        results: list[Citation] = []
        seen_spans: list[tuple[int, int]] = []

        # -- court decisions (try first — longer patterns) -------------------
        for m in _COURT_RE.finditer(citation_text):
            span = m.span()
            if _overlaps(span, seen_spans):
                continue
            seen_spans.append(span)
            results.append(Citation(
                raw          = m.group(0),
                citation_type= "case",
                court        = m.group("court"),
                year         = m.group("year"),
                case_type    = m.group("case_type"),
                case_no      = m.group("case_no"),
                case_kind    = m.group("case_kind"),
            ))

        # -- statutory -------------------------------------------------------
        for m in _STATUTORY_RE.finditer(citation_text):
            span = m.span()
            if _overlaps(span, seen_spans):
                continue
            seen_spans.append(span)
            results.append(Citation(
                raw          = m.group(0),
                citation_type= "statutory",
                law_body     = m.group("law"),
                article      = m.group("article"),
                paragraph    = m.group("paragraph"),
                subparagraph = m.group("subparagraph"),
                segment      = m.group("segment"),
            ))

        # Sort by position in text
        results.sort(key=lambda c: citation_text.find(c.raw))
        return results

    def normalize(self, citation: str) -> str:
        """
        Normalize a single citation string to its canonical form.

        If the string contains more than one citation, only the first is
        normalised.  Pass individual citations for best results.
        """
        citations = self.parse(citation)
        if citations:
            return citations[0].canonical
        # Fallback: strip excess whitespace
        return re.sub(r"\s+", "", citation).strip()

    def compare(self, citation_a: str, citation_b: str) -> dict[str, bool]:
        """
        Compare two citation strings.

        Returns
        -------
        {
            'exact':     True if canonical strings are identical,
            'article':   True if law body + article number match,
            'law_body':  True if law body matches,
        }
        """
        parsed_a = self.parse(citation_a)
        parsed_b = self.parse(citation_b)

        if not parsed_a or not parsed_b:
            # Can't parse at least one → fall back to raw string comparison
            raw_match = citation_a.strip() == citation_b.strip()
            return {"exact": raw_match, "article": raw_match, "law_body": raw_match}

        a, b = parsed_a[0], parsed_b[0]

        # -- exact -----------------------------------------------------------
        exact = a.canonical == b.canonical

        # -- article level ---------------------------------------------------
        if a.citation_type == "statutory" and b.citation_type == "statutory":
            article_match = (a.law_body == b.law_body) and (a.article == b.article)
            law_body_match = a.law_body == b.law_body
        elif a.citation_type == "case" and b.citation_type == "case":
            # For cases, "article" match = same court + year + type + number
            article_match = (
                a.court == b.court
                and a.year == b.year
                and a.case_type == b.case_type
                and a.case_no == b.case_no
            )
            law_body_match = a.court == b.court
        else:
            article_match = False
            law_body_match = False

        return {
            "exact":    exact,
            "article":  article_match,
            "law_body": law_body_match,
        }

    def extract_from_answer(self, answer_text: str) -> list[Citation]:
        """
        Extract all citations from a full answer text.

        Alias for :meth:`parse` with a more descriptive name.
        """
        return self.parse(answer_text)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _overlaps(span: tuple[int, int], existing: list[tuple[int, int]]) -> bool:
    """Return True if *span* overlaps with any span in *existing*."""
    s, e = span
    for es, ee in existing:
        if s < ee and e > es:
            return True
    return False


# ---------------------------------------------------------------------------
# CLI smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _EXAMPLES = [
        "民法第767條",
        "民法第767條第1項",
        "民法第767條第1項前段",
        "刑法第339條",
        "刑事訴訟法第156條第1項",
        "民事訴訟法第400條第1項",
        "最高法院112年度台上字第1234號判決",
        "台灣高等法院111年度上字第5678號判決",
        # Mixed prose
        "依民法第184條第1項前段及民法第213條之規定，原告請求被告賠償損害。",
        "最高法院108年度台上字第345號判決認為，刑法第339條之詐欺罪…",
    ]

    parser = TaiwanLegalCitationParser()
    for text in _EXAMPLES:
        print(f"\nInput : {text}")
        for c in parser.parse(text):
            print(f"  → [{c.citation_type}] canonical={c.canonical!r}  raw={c.raw!r}")

