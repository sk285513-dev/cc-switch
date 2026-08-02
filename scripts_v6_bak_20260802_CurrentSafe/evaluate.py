"""
evaluate.py — Main evaluation runner for the Taiwan Legal RAG Benchmark.

Usage
-----
from evaluate import BenchmarkEvaluator, mock_rag_system

evaluator = BenchmarkEvaluator(
    benchmark_path="path/to/benchmark_samples.jsonl",
    results_path="path/to/rag_results.json",   # optional – use mock if absent
)
evaluator.evaluate_all()
evaluator.generate_report("results/benchmark_report.json")
evaluator.print_summary()
"""

from __future__ import annotations
import json

import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Allow running from any working directory
_SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS_DIR))

from citation_parser import TaiwanLegalCitationParser
from metrics import LegalRAGMetrics


# ---------------------------------------------------------------------------
# Mock RAG system
# ---------------------------------------------------------------------------

def mock_rag_system(benchmark_samples: list[dict]) -> list[dict]:
    """
    Generate realistic *simulated* RAG output for every benchmark sample.

    Performance profile:
        • ~30 % of samples get high-quality results   (citation F1 0.85–0.95)
        • ~40 % get medium-quality results            (citation F1 0.55–0.75)
        • ~30 % get low-quality results               (citation F1 0.20–0.45)

    Within each tier the exact scores are further modulated by:
        • domain  — constitutional / expert samples are harder
        • difficulty — basic < intermediate < advanced < expert
        • query_type — multi_doc_synthesis hardest, factual_retrieval easiest

    The function also produces synthetic retrieved_docs, predicted_citations,
    and predicted_answer fields so that all downstream metric functions have
    realistic inputs.
    """
    rng = random.Random(42)  # deterministic

    # Difficulty multipliers (higher = easier to get right)
    DIFF_MULT = {
        "basic":        1.00,
        "intermediate": 0.85,
        "advanced":     0.70,
        "expert":       0.55,
    }
    DOMAIN_MULT = {
        "civil":          1.00,
        "criminal":       0.90,
        "procedure":      0.80,
        "constitutional": 0.70,
    }
    QTYPE_MULT = {
        "factual_retrieval":    1.00,
        "single_doc":           0.95,
        "procedural_reasoning": 0.85,
        "citation_chain":       0.80,
        "multi_doc_synthesis":  0.70,
    }

    def _tier_range(tier: str) -> tuple[float, float]:
        return {"high": (0.85, 0.95), "medium": (0.55, 0.75), "low": (0.20, 0.45)}[tier]

    def _pick_tier(rng: random.Random, multiplier: float) -> str:
        """Pick quality tier probabilistically, biased by *multiplier*."""
        high_p   = 0.30 * multiplier
        medium_p = 0.40
        # clamp so probabilities sum to ≤1
        high_p   = min(high_p,   0.55)
        medium_p = min(medium_p, 1 - high_p)
        low_p    = 1.0 - high_p - medium_p
        return rng.choices(["high", "medium", "low"], weights=[high_p, medium_p, low_p])[0]

    def _make_synthetic_doc_pool(sample: dict, n_pool: int = 20) -> list[str]:
        """Create a fake pool of doc IDs from which the mock system retrieves."""
        relevant = sample.get("relevant_doc_ids", [f"doc_{sample['id']}_0"])
        distractors = [f"distractor_{sample['id']}_{i}" for i in range(n_pool - len(relevant))]
        pool = list(relevant) + distractors
        rng.shuffle(pool)
        return pool

    def _make_retrieved_docs(
        sample: dict,
        pool: list[str],
        citation_f1: float,
    ) -> list[dict]:
        """Rank documents so that P@5 ≈ citation_f1 (rough proxy)."""
        relevant_set = set(sample.get("relevant_doc_ids", [f"doc_{sample['id']}_0"]))
        n_relevant = len(relevant_set)
        # How many relevant docs should appear in top-5?
        top5_hits = round(citation_f1 * min(5, n_relevant))
        top5_hits = min(top5_hits, n_relevant, 5)

        relevant_list = [d for d in pool if d in relevant_set]
        distractor_list = [d for d in pool if d not in relevant_set]

        rng.shuffle(relevant_list)
        rng.shuffle(distractor_list)

        top5_relevant   = relevant_list[:top5_hits]
        top5_distractor = distractor_list[:5 - top5_hits]
        top5 = top5_relevant + top5_distractor
        rng.shuffle(top5)

        # Remaining docs beyond rank 5
        rest = [d for d in pool if d not in set(top5)][:15]

        retrieved = []
        for rank, doc_id in enumerate(top5 + rest, start=1):
            score = max(0.1, 1.0 - (rank - 1) * 0.04 + rng.gauss(0, 0.02))
            retrieved.append({"doc_id": doc_id, "content": f"[mock content for {doc_id}]", "score": round(score, 4)})

        return retrieved

    def _make_citations(
        sample: dict,
        citation_f1: float,
    ) -> list[str]:
        expected = sample.get("expected_citations", [])
        if not expected:
            return []

        # Decide how many expected citations to include correctly
        n_correct = round(citation_f1 * len(expected))
        n_correct = min(n_correct, len(expected))
        correct   = rng.sample(expected, n_correct)

        # Add some plausible wrong citations (same law body, different article)
        _FALLBACK_WRONG = [
            "民法第184條", "民法第213條", "刑法第271條",
            "民事訴訟法第277條", "刑事訴訟法第161條",
        ]
        n_wrong = rng.randint(0, max(0, len(expected) - n_correct))
        wrong   = rng.choices(_FALLBACK_WRONG, k=n_wrong)

        combined = correct + wrong
        rng.shuffle(combined)
        return combined

    def _make_answer(sample: dict, citation_f1: float) -> str:
        """Construct a heuristic mock answer with variable quality."""
        q = sample.get("query", "")
        cits = sample.get("expected_citations", [])
        domain = sample.get("domain", "civil")
        difficulty = sample.get("difficulty", "basic")
        key_concepts = sample.get("key_concepts", [])

        # High quality → include structure signals + key concepts
        if citation_f1 >= 0.80:
            concept_snippet = "、".join(key_concepts[:3]) if key_concepts else "相關法律概念"
            cit_snippet = "、".join(cits[:2]) if cits else "相關條文"
            return (
                f"依{cit_snippet}之規定，本件涉及{concept_snippet}。"
                f"查原告主張之事實，依法律三段論分析："
                f"大前提為{cit_snippet}所定構成要件；"
                f"小前提為本案事實符合上述要件；"
                f"因此，被告應負相應法律責任。"
                f"（{domain}法，{difficulty}難度，模擬答案）"
            )
        elif citation_f1 >= 0.50:
            cit_snippet = cits[0] if cits else "相關條文"
            return (
                f"依{cit_snippet}規定，當事人應注意相關法律效果。"
                f"本件事實需進一步審酌。"
                f"（{domain}法，{difficulty}難度，模擬答案）"
            )
        else:
            return (
                f"本案涉及{domain}法律問題，建議諮詢專業律師。"
                f"（模擬低品質答案）"
            )

    results = []
    for sample in benchmark_samples:
        sid = sample.get("id", f"UNKNOWN-{len(results)}")
        domain     = sample.get("domain",     "civil")
        difficulty = sample.get("difficulty", "basic")
        query_type = sample.get("query_type", "single_doc")

        # Composite quality multiplier
        mult = (
            DIFF_MULT.get(difficulty, 0.75) *
            DOMAIN_MULT.get(domain, 0.85) *
            QTYPE_MULT.get(query_type, 0.85)
        )

        tier        = _pick_tier(rng, mult)
        lo, hi      = _tier_range(tier)
        citation_f1 = rng.uniform(lo, hi)

        pool            = _make_synthetic_doc_pool(sample)
        retrieved_docs  = _make_retrieved_docs(sample, pool, citation_f1)
        predicted_cits  = _make_citations(sample, citation_f1)
        predicted_ans   = _make_answer(sample, citation_f1)

        results.append({
            "id":                   sid,
            "retrieved_docs":       retrieved_docs,
            "predicted_citations":  predicted_cits,
            "predicted_answer":     predicted_ans,
            "_mock_tier":           tier,            # internal metadata
            "_mock_citation_f1":    round(citation_f1, 4),
        })

    return results


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

class BenchmarkEvaluator:
    """
    Load a benchmark JSONL and RAG system results, evaluate, and report.

    Parameters
    ----------
    benchmark_path : path to benchmark_samples.jsonl
    results_path   : path to RAG system output JSON (optional; if None or
                     the file does not exist, mock_rag_system() is used)
    """

    def __init__(self, benchmark_path: str | Path, results_path: str | Path | None = None):
        self.benchmark_path = Path(benchmark_path)
        self.results_path   = Path(results_path) if results_path else None
        self.metrics        = LegalRAGMetrics()
        self.parser         = TaiwanLegalCitationParser()

        self.samples: list[dict]  = []
        self.rag_results: list[dict] = []
        self.evaluated: list[dict] = []

        self._load_benchmark()

    # -----------------------------------------------------------------------
    # Data loading
    # -----------------------------------------------------------------------

    def _load_benchmark(self) -> None:
        """Load benchmark_samples.jsonl into self.samples."""
        if not self.benchmark_path.exists():
            raise FileNotFoundError(f"Benchmark file not found: {self.benchmark_path}")

        samples = []
        with open(self.benchmark_path, encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    s = json.loads(line)
                    # Normalize keys for compatibility
                    s["query"] = s.get("query_zh", s.get("query", ""))
                    s["expected_citations"] = s.get("expected_law_citations", []) + s.get("expected_case_refs", [])
                    s["key_concepts"] = s.get("key_legal_concepts", s.get("key_concepts", []))
                    s["ground_truth_answer"] = s.get("ground_truth_answer_zh", s.get("ground_truth_answer", ""))
                    samples.append(s)
        self.samples = samples
        print(f"[BenchmarkEvaluator] Loaded {len(samples)} benchmark samples.")

    def load_rag_results(self, results_file: str | Path) -> None:
        """
        Load RAG system output from *results_file*.

        Expected JSON format (array of objects):
        [
          {
            "id": "TW-BENCH-0001",
            "retrieved_docs": [{"doc_id": "...", "content": "...", "score": 0.95}],
            "predicted_citations": ["民法第767條", "民法第179條"],
            "predicted_answer": "..."
          },
          ...
        ]
        """
        results_file = Path(results_file)
        if not results_file.exists():
            raise FileNotFoundError(f"Results file not found: {results_file}")

        with open(results_file, encoding="utf-8-sig") as fh:
            data = json.load(fh)

        if isinstance(data, list):
            self.rag_results = data
        elif isinstance(data, dict) and "results" in data:
            self.rag_results = data["results"]
        else:
            raise ValueError("Unexpected results file format.")

        print(f"[BenchmarkEvaluator] Loaded {len(self.rag_results)} RAG results.")

    def _get_results(self) -> list[dict]:
        """Return RAG results, generating mock ones if necessary."""
        if self.rag_results:
            return self.rag_results
        if self.results_path and self.results_path.exists():
            self.load_rag_results(self.results_path)
            return self.rag_results
        # Fall back to mock
        print("[BenchmarkEvaluator] No real RAG results found — using mock_rag_system().")
        self.rag_results = mock_rag_system(self.samples)
        return self.rag_results

    # -----------------------------------------------------------------------
    # Evaluation
    # -----------------------------------------------------------------------

    def evaluate_single(self, sample: dict, result: dict) -> dict:
        """
        Full evaluation of one (sample, result) pair.

        Returns a flat dict suitable for aggregation.
        """
        sid = sample.get("id", result.get("id", "UNKNOWN"))

        # -- Retrieval -------------------------------------------------------
        retrieved_doc_ids = [d["doc_id"] for d in result.get("retrieved_docs", [])]
        relevant_doc_ids  = sample.get("relevant_doc_ids", [f"doc_{sid}_0"])

        p5  = self.metrics.retrieval_precision_at_k(retrieved_doc_ids, relevant_doc_ids, 5)
        r5  = self.metrics.retrieval_recall_at_k(   retrieved_doc_ids, relevant_doc_ids, 5)
        p10 = self.metrics.retrieval_precision_at_k(retrieved_doc_ids, relevant_doc_ids, 10)
        r10 = self.metrics.retrieval_recall_at_k(   retrieved_doc_ids, relevant_doc_ids, 10)

        # MRR for this single sample (wrap in lists)
        mrr = self.metrics.mean_reciprocal_rank([retrieved_doc_ids], [relevant_doc_ids])

        # -- Citation --------------------------------------------------------
        predicted_cits = result.get("predicted_citations", [])
        expected_cits  = sample.get("expected_citations",  [])

        cit_metrics = self.metrics.citation_accuracy(predicted_cits, expected_cits)
        citation_f1 = cit_metrics["f1"]

        # -- Answer quality --------------------------------------------------
        predicted_answer = result.get("predicted_answer", "")
        ground_truth     = sample.get("ground_truth_answer", sample.get("answer", ""))
        key_concepts     = sample.get("key_concepts", [])

        ans_metrics = self.metrics.answer_relevance_score(
            predicted_answer, ground_truth, key_concepts
        )

        # -- Multi-doc synthesis (only for relevant query types) -------------
        multi_doc: dict[str, float] = {}
        if sample.get("query_type") in ("multi_doc_synthesis", "citation_chain"):
            multi_doc = self.metrics.multi_doc_synthesis_score(predicted_answer, sample)

        # -- Overall score ---------------------------------------------------
        combined = {
            "precision_at_5":  p5,
            "recall_at_5":     r5,
            "citation_f1":     citation_f1,
            "concept_coverage": ans_metrics["concept_coverage"],
            "structure_score":  ans_metrics["structure_score"],
        }
        overall = self.metrics.overall_rag_score(combined)

        return {
            # Identity
            "id":               sid,
            "domain":           sample.get("domain",     "civil"),
            "difficulty":       sample.get("difficulty", "basic"),
            "query_type":       sample.get("query_type", "single_doc"),
            "retrieval_difficulty": sample.get("retrieval_difficulty", 0.5),
            # Retrieval
            "precision_at_5":  round(p5,  4),
            "recall_at_5":     round(r5,  4),
            "precision_at_10": round(p10, 4),
            "recall_at_10":    round(r10, 4),
            "mrr":             round(mrr, 4),
            # Citation
            "citation_exact_match":   cit_metrics["exact_match"],
            "citation_article_match": cit_metrics["article_match"],
            "citation_law_match":     cit_metrics["law_match"],
            "citation_f1":            cit_metrics["f1"],
            # Answer quality
            "concept_coverage":    ans_metrics["concept_coverage"],
            "legal_term_accuracy": ans_metrics["legal_term_accuracy"],
            "structure_score":     ans_metrics["structure_score"],
            # Multi-doc (may be empty dict)
            **{f"multidoc_{k}": v for k, v in multi_doc.items()},
            # Overall
            "overall_score": overall,
            # Pass-through fields for report
            "predicted_citations": predicted_cits,
            "expected_citations":  expected_cits,
            "query":               sample.get("query", ""),
        }

    def evaluate_all(self) -> dict:
        """
        Evaluate every sample in the benchmark.

        Returns the full aggregated results dict (also stored in
        self.evaluated).
        """
        results = self._get_results()

        # Build lookup by ID
        result_by_id = {r["id"]: r for r in results}
        sample_by_id = {s["id"]: s for s in self.samples}

        evaluated = []
        for sample in self.samples:
            sid = sample["id"]
            result = result_by_id.get(sid)
            if result is None:
                # Generate a blank result for missing IDs
                result = {
                    "id": sid,
                    "retrieved_docs": [],
                    "predicted_citations": [],
                    "predicted_answer": "",
                }
            evaluated.append(self.evaluate_single(sample, result))

        self.evaluated = evaluated
        print(f"[BenchmarkEvaluator] Evaluated {len(evaluated)} samples.")
        return self._build_full_report()

    # -----------------------------------------------------------------------
    # Reporting helpers
    # -----------------------------------------------------------------------

    def _build_full_report(self) -> dict:
        """Construct the full benchmark_report.json structure."""
        ev = self.evaluated
        if not ev:
            return {}

        def _mean(vals: list[float]) -> float:
            return round(sum(vals) / len(vals), 4) if vals else 0.0

        def _agg_group(subset: list[dict]) -> dict:
            if not subset:
                return {
                    "samples": 0, "overall_score": 0.0,
                    "precision_at_5": 0.0, "recall_at_5": 0.0,
                    "citation_f1": 0.0,
                }
            return {
                "samples":        len(subset),
                "overall_score":  _mean([r["overall_score"]  for r in subset]),
                "precision_at_5": _mean([r["precision_at_5"] for r in subset]),
                "recall_at_5":    _mean([r["recall_at_5"]    for r in subset]),
                "citation_f1":    _mean([r["citation_f1"]    for r in subset]),
                "mrr":            _mean([r["mrr"]            for r in subset]),
                "concept_coverage": _mean([r["concept_coverage"] for r in subset]),
            }

        # -- Summary ---------------------------------------------------------
        summary = {
            "total_samples":   len(ev),
            "overall_score":   _mean([r["overall_score"]  for r in ev]),
            "precision_at_5":  _mean([r["precision_at_5"] for r in ev]),
            "recall_at_5":     _mean([r["recall_at_5"]    for r in ev]),
            "mrr":             _mean([r["mrr"]            for r in ev]),
            "citation_f1":     _mean([r["citation_f1"]    for r in ev]),
            "concept_coverage": _mean([r["concept_coverage"] for r in ev]),
        }

        # -- By domain -------------------------------------------------------
        domains = defaultdict(list)
        for r in ev:
            domains[r["domain"]].append(r)
        by_domain = {d: _agg_group(v) for d, v in domains.items()}
        # Ensure all expected keys exist
        for d in ("civil", "criminal", "procedure", "constitutional"):
            by_domain.setdefault(d, _agg_group([]))

        # -- By difficulty ---------------------------------------------------
        diffs = defaultdict(list)
        for r in ev:
            diffs[r["difficulty"]].append(r)
        by_difficulty = {d: _agg_group(v) for d, v in diffs.items()}
        for d in ("basic", "intermediate", "advanced", "expert"):
            by_difficulty.setdefault(d, _agg_group([]))

        # -- By query type ---------------------------------------------------
        qtypes = defaultdict(list)
        for r in ev:
            qtypes[r["query_type"]].append(r)
        by_query_type = {qt: _agg_group(v) for qt, v in qtypes.items()}
        for qt in ("single_doc", "multi_doc_synthesis", "citation_chain",
                   "procedural_reasoning", "factual_retrieval"):
            by_query_type.setdefault(qt, _agg_group([]))

        # -- Score distribution (for histogram) ------------------------------
        score_distribution = [round(r["overall_score"], 3) for r in ev]

        # -- Per domain × difficulty -----------------------------------------
        per_domain_per_difficulty: dict[str, dict] = {}
        for domain in by_domain:
            per_domain_per_difficulty[domain] = {}
            for diff in by_difficulty:
                subset = [r for r in ev if r["domain"] == domain and r["difficulty"] == diff]
                per_domain_per_difficulty[domain][diff] = _agg_group(subset)

        # -- Top failures / successes ----------------------------------------
        sorted_by_score = sorted(ev, key=lambda r: r["overall_score"])
        top_failures  = self._format_highlights(sorted_by_score[:10])
        top_successes = self._format_highlights(sorted_by_score[-10:][::-1])

        # -- First 100 detailed results for table ----------------------------
        sample_results = self._format_sample_results(ev[:100])

        report = {
            "summary":                 summary,
            "by_domain":               by_domain,
            "by_difficulty":           by_difficulty,
            "by_query_type":           by_query_type,
            "score_distribution":      score_distribution,
            "per_domain_per_difficulty": per_domain_per_difficulty,
            "top_failures":            top_failures,
            "top_successes":           top_successes,
            "sample_results":          sample_results,
        }
        return report

    @staticmethod
    def _format_highlights(items: list[dict]) -> list[dict]:
        return [
            {
                "id":             r["id"],
                "domain":         r["domain"],
                "difficulty":     r["difficulty"],
                "query_type":     r["query_type"],
                "overall_score":  r["overall_score"],
                "citation_f1":    r["citation_f1"],
                "precision_at_5": r["precision_at_5"],
                "query":          r.get("query", ""),
            }
            for r in items
        ]

    @staticmethod
    def _format_sample_results(items: list[dict]) -> list[dict]:
        keys = [
            "id", "domain", "difficulty", "query_type",
            "overall_score", "precision_at_5", "recall_at_5",
            "mrr", "citation_f1", "concept_coverage", "structure_score",
            "query", "predicted_citations", "expected_citations",
        ]
        return [{k: r.get(k) for k in keys} for r in items]

    # -----------------------------------------------------------------------
    # Output
    # -----------------------------------------------------------------------

    def generate_report(self, output_path: str | Path) -> None:
        """Write the full JSON report to *output_path*."""
        if not self.evaluated:
            self.evaluate_all()

        report = self._build_full_report()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8-sig") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)

        print(f"[BenchmarkEvaluator] Report written to {output_path}")

    def generate_detailed_results(self, output_path: str | Path) -> None:
        """Write per-sample detailed results to *output_path*."""
        if not self.evaluated:
            self.evaluate_all()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Exclude the pass-through text fields to keep file manageable
        slim_keys = [
            "id", "domain", "difficulty", "query_type", "retrieval_difficulty",
            "precision_at_5", "recall_at_5", "precision_at_10", "recall_at_10",
            "mrr", "citation_exact_match", "citation_article_match",
            "citation_law_match", "citation_f1",
            "concept_coverage", "legal_term_accuracy", "structure_score",
            "overall_score",
            "predicted_citations", "expected_citations", "query",
        ]
        slim = [{k: r.get(k) for k in slim_keys} for r in self.evaluated]

        with open(output_path, "w", encoding="utf-8-sig") as fh:
            json.dump(slim, fh, ensure_ascii=False, indent=2)

        print(f"[BenchmarkEvaluator] Detailed results written to {output_path}")

    def print_summary(self) -> None:
        """Pretty-print a summary table to stdout."""
        if not self.evaluated:
            self.evaluate_all()

        report = self._build_full_report()
        s = report["summary"]

        sep = "=" * 70
        print(f"\n{sep}")
        print("  TAIWAN LEGAL RAG BENCHMARK — SUMMARY")
        print(sep)
        print(f"  Total samples   : {s['total_samples']}")
        print(f"  Overall score   : {s['overall_score']:.4f}")
        print(f"  Precision@5     : {s['precision_at_5']:.4f}")
        print(f"  Recall@5        : {s['recall_at_5']:.4f}")
        print(f"  MRR             : {s['mrr']:.4f}")
        print(f"  Citation F1     : {s['citation_f1']:.4f}")
        print(f"  Concept coverage: {s['concept_coverage']:.4f}")

        print(f"\n{'─' * 70}")
        print("  BY DOMAIN")
        print(f"  {'Domain':<20} {'Samples':>7} {'Score':>8} {'P@5':>8} {'R@5':>8} {'Cite F1':>8}")
        print(f"  {'─'*20} {'─'*7} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
        for d, v in sorted(report["by_domain"].items()):
            print(f"  {d:<20} {v['samples']:>7} {v['overall_score']:>8.4f} "
                  f"{v['precision_at_5']:>8.4f} {v['recall_at_5']:>8.4f} {v['citation_f1']:>8.4f}")

        print(f"\n{'─' * 70}")
        print("  BY DIFFICULTY")
        print(f"  {'Difficulty':<20} {'Samples':>7} {'Score':>8} {'Cite F1':>8}")
        print(f"  {'─'*20} {'─'*7} {'─'*8} {'─'*8}")
        for d, v in sorted(report["by_difficulty"].items()):
            print(f"  {d:<20} {v['samples']:>7} {v['overall_score']:>8.4f} {v['citation_f1']:>8.4f}")

        print(f"\n{'─' * 70}")
        print("  BY QUERY TYPE")
        print(f"  {'Query Type':<25} {'Samples':>7} {'Score':>8} {'Cite F1':>8}")
        print(f"  {'─'*25} {'─'*7} {'─'*8} {'─'*8}")
        for qt, v in sorted(report["by_query_type"].items()):
            print(f"  {qt:<25} {v['samples']:>7} {v['overall_score']:>8.4f} {v['citation_f1']:>8.4f}")

        print(f"\n{'─' * 70}")
        print("  TOP 5 FAILURES")
        for r in report["top_failures"][:5]:
            print(f"  [{r['id']}] score={r['overall_score']:.4f}  "
                  f"domain={r['domain']}  diff={r['difficulty']}")

        print(f"\n{'─' * 70}")
        print("  TOP 5 SUCCESSES")
        for r in report["top_successes"][:5]:
            print(f"  [{r['id']}] score={r['overall_score']:.4f}  "
                  f"domain={r['domain']}  diff={r['difficulty']}")

        print(f"{sep}\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Taiwan Legal RAG Benchmark Evaluator")
    parser.add_argument("--benchmark", default="data/benchmark_samples.jsonl", help="Path to benchmark_samples.jsonl")
    parser.add_argument("--results", default=None, help="Path to RAG results JSON")
    parser.add_argument("--report", default="data/benchmark_report.json", help="Path to output report JSON")
    parser.add_argument("--detailed", default="data/benchmark_detailed.json", help="Path to output detailed results JSON")
    args = parser.parse_args()
    
    # Ensure relative paths are handled correctly
    base_dir = Path(__file__).resolve().parent.parent
    bench_path = Path(args.benchmark)
    if not bench_path.is_absolute():
        bench_path = base_dir / bench_path
        
    results_path = None
    if args.results:
        results_path = Path(args.results)
        if not results_path.is_absolute():
            results_path = base_dir / results_path
            
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = base_dir / report_path
        
    detailed_path = Path(args.detailed)
    if not detailed_path.is_absolute():
        detailed_path = base_dir / detailed_path
        
    evaluator = BenchmarkEvaluator(benchmark_path=bench_path, results_path=results_path)
    evaluator.evaluate_all()
    evaluator.generate_report(report_path)
    evaluator.generate_detailed_results(detailed_path)
    evaluator.print_summary()

