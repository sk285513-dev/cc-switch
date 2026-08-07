"""
metrics.py — Core evaluation metrics for the Taiwan Legal RAG Benchmark.

All public functions are pure (no side-effects) so they can be tested in
isolation.  The class LegalRAGMetrics is a namespace-style class with only
@staticmethod / @classmethod members; instantiate it if you want but there is
no required state.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Return numerator / denominator, or *default* when denominator == 0."""
    return numerator / denominator if denominator else default


def _set_overlap(a: list, b: list) -> int:
    """Return |set(a) ∩ set(b)|."""
    return len(set(a) & set(b))


# ---------------------------------------------------------------------------
# Main metrics class
# ---------------------------------------------------------------------------

class LegalRAGMetrics:
    """
    All evaluation metrics for a Taiwan-law RAG benchmark.

    The class can be used either via the class itself (e.g.
    ``LegalRAGMetrics.retrieval_precision_at_k(...)``) or instantiated; it
    holds no mutable state.
    """

    # -----------------------------------------------------------------------
    # 1. Retrieval precision@k
    # -----------------------------------------------------------------------

    @staticmethod
    def retrieval_precision_at_k(
        retrieved_docs: list[str],
        relevant_docs: list[str],
        k: int,
    ) -> float:
        """
        Standard Precision@k.

        |relevant ∩ retrieved[:k]| / k

        Parameters
        ----------
        retrieved_docs : ordered list of retrieved document IDs
        relevant_docs  : set/list of ground-truth relevant document IDs
        k              : cutoff rank
        """
        if k <= 0:
            return 0.0
        topk = retrieved_docs[:k]
        hits = _set_overlap(topk, relevant_docs)
        return hits / k

    # -----------------------------------------------------------------------
    # 2. Retrieval recall@k
    # -----------------------------------------------------------------------

    @staticmethod
    def retrieval_recall_at_k(
        retrieved_docs: list[str],
        relevant_docs: list[str],
        k: int,
    ) -> float:
        """
        Standard Recall@k.

        |relevant ∩ retrieved[:k]| / |relevant|

        Returns 0 when *relevant_docs* is empty.
        """
        if not relevant_docs:
            return 0.0
        topk = retrieved_docs[:k]
        hits = _set_overlap(topk, relevant_docs)
        return _safe_div(hits, len(relevant_docs))

    # -----------------------------------------------------------------------
    # 3. Mean Reciprocal Rank
    # -----------------------------------------------------------------------

    @staticmethod
    def mean_reciprocal_rank(
        retrieved_docs_list: list[list[str]],
        relevant_docs_list: list[list[str]],
    ) -> float:
        """
        MRR across multiple queries.

        Each query contributes 1/rank_of_first_relevant_doc (0 if none found
        in the retrieved list).
        """
        if not retrieved_docs_list:
            return 0.0

        rr_sum = 0.0
        for retrieved, relevant in zip(retrieved_docs_list, relevant_docs_list):
            relevant_set = set(relevant)
            for rank, doc_id in enumerate(retrieved, start=1):
                if doc_id in relevant_set:
                    rr_sum += 1.0 / rank
                    break  # only first hit counts

        return rr_sum / len(retrieved_docs_list)

    # -----------------------------------------------------------------------
    # 4. Citation accuracy (Taiwan-specific)
    # -----------------------------------------------------------------------

    @staticmethod
    def citation_accuracy(
        predicted_citations: list[str],
        expected_citations: list[str],
    ) -> dict[str, float]:
        """
        Multi-level citation matching for Taiwan legal citations.

        Handles formats such as:
            民法第767條
            民法第767條第1項
            民法第767條第1項前段

        Returns
        -------
        dict with keys:
            'exact_match'   – full citation string equality (F1)
            'article_match' – matches ignoring 項/款/前後段
            'law_match'     – matches on the law body only (民法, 刑法, …)
            'f1'            – citation-level F1 (primary score)
        """
        from citation_parser import TaiwanLegalCitationParser  # local import to avoid circularity

        parser = TaiwanLegalCitationParser()

        def _normalise_list(citations: list[str]) -> list[str]:
            out = []
            for c in citations:
                try:
                    out.append(parser.normalize(c))
                except Exception:
                    out.append(c.strip())
            return out

        pred_norm = _normalise_list(predicted_citations)
        exp_norm  = _normalise_list(expected_citations)

        # ---------- exact match (F1 on normalised strings) ----------
        pred_set = set(pred_norm)
        exp_set  = set(exp_norm)
        tp_exact = len(pred_set & exp_set)
        precision_exact = _safe_div(tp_exact, len(pred_set))
        recall_exact    = _safe_div(tp_exact, len(exp_set))
        f1_exact        = _safe_div(
            2 * precision_exact * recall_exact,
            precision_exact + recall_exact,
        )

        # ---------- article-level match (ignore 項/款/前後段) ----------
        def _article_key(c: str) -> str:
            """Extract 'LAW第NNN條' part."""
            m = re.match(r"^(.+?第\d+條)", c)
            return m.group(1) if m else c

        pred_art = set(_article_key(c) for c in pred_norm)
        exp_art  = set(_article_key(c) for c in exp_norm)
        tp_art   = len(pred_art & exp_art)
        prec_art = _safe_div(tp_art, len(pred_art))
        rec_art  = _safe_div(tp_art, len(exp_art))
        f1_art   = _safe_div(2 * prec_art * rec_art, prec_art + rec_art)

        # ---------- law-body match (民法, 刑法, …) ----------
        def _law_key(c: str) -> str:
            """Extract the law body name before 第."""
            m = re.match(r"^([^\d第]+)", c)
            return m.group(1).strip() if m else c

        pred_law = set(_law_key(c) for c in pred_norm)
        exp_law  = set(_law_key(c) for c in exp_norm)
        tp_law   = len(pred_law & exp_law)
        prec_law = _safe_div(tp_law, len(pred_law))
        rec_law  = _safe_div(tp_law, len(exp_law))
        f1_law   = _safe_div(2 * prec_law * rec_law, prec_law + rec_law)

        return {
            "exact_match":   round(f1_exact, 4),
            "article_match": round(f1_art,   4),
            "law_match":     round(f1_law,   4),
            "f1":            round(f1_exact,  4),   # primary score = exact F1
        }

    # -----------------------------------------------------------------------
    # 5. Answer relevance score
    # -----------------------------------------------------------------------

    @staticmethod
    def answer_relevance_score(
        predicted_answer: str,
        ground_truth: str,
        key_concepts: list[str],
    ) -> dict[str, float]:
        """
        Answer quality measured along three axes.

        concept_coverage
            Fraction of *key_concepts* that appear (case-insensitive) in the
            predicted answer.

        legal_term_accuracy
            Overlap of Taiwan-specific legal terms between prediction and
            ground truth (using a simple token F1 on legal vocabulary).

        structure_score
            Heuristic check for 法律三段論 (legal syllogism) structure:
            大前提 (major premise / 法律規定) →
            小前提 (minor premise / 事實認定) →
            結論 (conclusion / 法律效果).
        """
        pred_lower = predicted_answer.lower()

        # -- concept coverage ------------------------------------------------
        covered = sum(
            1 for c in key_concepts if c.lower() in pred_lower
        )
        concept_coverage = _safe_div(covered, len(key_concepts))

        # -- legal term accuracy ---------------------------------------------
        # Extract CJK legal vocabulary tokens (≥2 chars, common in TW law)
        _LEGAL_TERM_RE = re.compile(
            r"[\u4e00-\u9fff]{2,}",   # two-or-more CJK characters
        )
        pred_terms = set(_LEGAL_TERM_RE.findall(predicted_answer))
        gt_terms   = set(_LEGAL_TERM_RE.findall(ground_truth))

        tp_terms = len(pred_terms & gt_terms)
        prec_t   = _safe_div(tp_terms, len(pred_terms))
        rec_t    = _safe_div(tp_terms, len(gt_terms))
        legal_term_accuracy = _safe_div(
            2 * prec_t * rec_t, prec_t + rec_t
        )

        # -- structure score (法律三段論 heuristic) ---------------------------
        # Look for signals of each of the three elements.
        MAJOR_PREMISE_SIGNALS = [
            "依", "按", "依據", "規定", "條規定", "法律規定",
            "依法", "依照", "第.*條", "法第",
        ]
        MINOR_PREMISE_SIGNALS = [
            "本件", "查", "本案", "事實", "原告", "被告", "當事人",
            "依題意", "依案情", "依事實",
        ]
        CONCLUSION_SIGNALS = [
            "因此", "故", "從而", "是以", "綜上", "結論", "應", "得",
            "有無", "成立", "不成立", "爰", "裁判", "判決",
        ]

        def _has_signal(text: str, signals: list[str]) -> bool:
            for s in signals:
                if re.search(s, text):
                    return True
            return False

        has_major    = _has_signal(predicted_answer, MAJOR_PREMISE_SIGNALS)
        has_minor    = _has_signal(predicted_answer, MINOR_PREMISE_SIGNALS)
        has_conc     = _has_signal(predicted_answer, CONCLUSION_SIGNALS)
        structure_score = (has_major + has_minor + has_conc) / 3.0

        return {
            "concept_coverage":     round(concept_coverage,     4),
            "legal_term_accuracy":  round(legal_term_accuracy,  4),
            "structure_score":      round(structure_score,       4),
        }

    # -----------------------------------------------------------------------
    # 6. Multi-document synthesis score
    # -----------------------------------------------------------------------

    @staticmethod
    def multi_doc_synthesis_score(
        predicted_answer: str,
        sample: dict[str, Any],
    ) -> dict[str, float]:
        """
        Score how well the answer synthesises multiple source documents.

        Parameters
        ----------
        predicted_answer : generated answer text
        sample           : benchmark sample dict (must have 'relevant_doc_ids'
                           and 'expected_citations' at minimum)

        Returns
        -------
        dict with:
            source_integration       – fraction of required docs referenced
            reasoning_chain          – heuristic score for fact→law→conclusion
            contradiction_handling   – penalise if conflicting provisions exist
                                       but no hedging language is present
        """
        # -- source integration ----------------------------------------------
        required_docs = sample.get("relevant_doc_ids", [])
        if required_docs:
            mentioned = sum(
                1 for d in required_docs
                if str(d) in predicted_answer
            )
            source_integration = _safe_div(mentioned, len(required_docs))
        else:
            # Fall back to citation coverage as a proxy
            expected_cits = sample.get("expected_citations", [])
            mentioned_cits = sum(
                1 for c in expected_cits
                if c in predicted_answer
            )
            source_integration = _safe_div(mentioned_cits, len(expected_cits)) if expected_cits else 1.0

        # -- reasoning chain -------------------------------------------------
        # Heuristic: award points for presence of factual, legal, and
        # conclusive language in that order.
        FACT_RE  = re.compile(r"(事實|查|本件|原告|被告|當事人|行為)")
        LAW_RE   = re.compile(r"(依|按|第\d+條|法律|規定|構成要件)")
        CONC_RE  = re.compile(r"(因此|從而|綜上|故|爰|結論|應|成立|不成立)")

        has_fact = bool(FACT_RE.search(predicted_answer))
        has_law  = bool(LAW_RE.search(predicted_answer))
        has_conc = bool(CONC_RE.search(predicted_answer))
        reasoning_chain = (has_fact + has_law + has_conc) / 3.0

        # -- contradiction handling ------------------------------------------
        # If the sample flags conflicting_provisions, check for hedging.
        has_conflict = sample.get("conflicting_provisions", False)
        if has_conflict:
            HEDGE_RE = re.compile(
                r"(然而|但|惟|相互矛盾|競合|特別法|優先|例外|衝突|不一致)"
            )
            contradiction_handling = 1.0 if HEDGE_RE.search(predicted_answer) else 0.0
        else:
            contradiction_handling = 1.0  # no conflict → full marks by default

        return {
            "source_integration":      round(source_integration,      4),
            "reasoning_chain":         round(reasoning_chain,          4),
            "contradiction_handling":  round(contradiction_handling,   4),
        }

    # -----------------------------------------------------------------------
    # 7. Overall RAG score
    # -----------------------------------------------------------------------

    @staticmethod
    def overall_rag_score(sample_result: dict[str, Any]) -> float:
        """
        Weighted composite score for a single sample evaluation result.

        Weights
        -------
        retrieval quality   30 %  → average of P@5 and R@5
        citation accuracy   35 %  → citation F1
        answer quality      35 %  → average of concept_coverage + structure_score

        All component scores must already be computed and stored in
        *sample_result* under the expected keys.
        """
        # -- retrieval quality (30 %) ----------------------------------------
        p5 = sample_result.get("precision_at_5", 0.0)
        r5 = sample_result.get("recall_at_5",    0.0)
        retrieval_score = (p5 + r5) / 2.0

        # -- citation accuracy (35 %) ----------------------------------------
        citation_score = sample_result.get("citation_f1", 0.0)

        # -- answer quality (35 %) -------------------------------------------
        concept_cov  = sample_result.get("concept_coverage",  0.0)
        structure    = sample_result.get("structure_score",   0.0)
        answer_score = (concept_cov + structure) / 2.0

        overall = (
            0.30 * retrieval_score +
            0.35 * citation_score  +
            0.35 * answer_score
        )
        return round(overall, 4)

    # -----------------------------------------------------------------------
    # 8. Benchmark summary
    # -----------------------------------------------------------------------

    @classmethod
    def benchmark_summary(cls, results_list: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Aggregate metrics across all evaluated samples.

        The *results_list* must be a list of per-sample result dicts as
        produced by BenchmarkEvaluator.evaluate_single().

        Returns a nested dict with breakdowns by:
            - domain      (civil / criminal / procedure / constitutional)
            - difficulty  (basic / intermediate / advanced / expert)
            - query_type  (single_doc / multi_doc_synthesis / …)
            - retrieval_difficulty score
        """
        if not results_list:
            return {}

        def _mean(values: list[float]) -> float:
            return round(sum(values) / len(values), 4) if values else 0.0

        def _aggregate(subset: list[dict]) -> dict:
            return {
                "samples":        len(subset),
                "overall_score":  _mean([r.get("overall_score",  0.0) for r in subset]),
                "precision_at_5": _mean([r.get("precision_at_5", 0.0) for r in subset]),
                "recall_at_5":    _mean([r.get("recall_at_5",    0.0) for r in subset]),
                "mrr":            _mean([r.get("mrr",            0.0) for r in subset]),
                "citation_f1":    _mean([r.get("citation_f1",    0.0) for r in subset]),
                "concept_coverage": _mean([r.get("concept_coverage", 0.0) for r in subset]),
                "structure_score":  _mean([r.get("structure_score",  0.0) for r in subset]),
            }

        # -- global ----------------------------------------------------------
        global_agg = _aggregate(results_list)

        # -- by domain -------------------------------------------------------
        domains = defaultdict(list)
        for r in results_list:
            domains[r.get("domain", "unknown")].append(r)
        by_domain = {d: _aggregate(v) for d, v in domains.items()}

        # -- by difficulty ---------------------------------------------------
        diffs = defaultdict(list)
        for r in results_list:
            diffs[r.get("difficulty", "unknown")].append(r)
        by_difficulty = {d: _aggregate(v) for d, v in diffs.items()}

        # -- by query type ---------------------------------------------------
        qtypes = defaultdict(list)
        for r in results_list:
            qtypes[r.get("query_type", "unknown")].append(r)
        by_query_type = {qt: _aggregate(v) for qt, v in qtypes.items()}

        # -- by retrieval difficulty (binned) ---------------------------------
        retr_bins: dict[str, list] = {
            "easy":   [],
            "medium": [],
            "hard":   [],
        }
        for r in results_list:
            rd = r.get("retrieval_difficulty", 0.5)
            if rd < 0.33:
                retr_bins["easy"].append(r)
            elif rd < 0.67:
                retr_bins["medium"].append(r)
            else:
                retr_bins["hard"].append(r)
        by_retrieval_difficulty = {b: _aggregate(v) for b, v in retr_bins.items()}

        return {
            "global":                  global_agg,
            "by_domain":               by_domain,
            "by_difficulty":           by_difficulty,
            "by_query_type":           by_query_type,
            "by_retrieval_difficulty": by_retrieval_difficulty,
        }

