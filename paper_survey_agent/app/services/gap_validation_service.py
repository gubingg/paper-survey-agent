from __future__ import annotations

from app.schemas.agent_schema import EvidenceSnippet
from app.schemas.gap_schema import GapCandidate
from app.schemas.paper_schema import CompareResult, PaperSchema
from app.services.gap_service import GapService


class GapValidationService:
    """Business logic used by light and strict gap validation flows."""

    def __init__(self) -> None:
        self.gap_service = GapService()

    def normalize_gap_candidate(
        self,
        candidate: GapCandidate,
        compare_result: CompareResult | None,
        paper_schemas: list[PaperSchema],
    ) -> dict:
        """Rewrite a raw gap candidate into a structured proposition."""

        statement = candidate.original_statement or candidate.statement
        keywords = self.gap_service.extract_gap_keywords(statement)
        top_method = ""
        if compare_result and compare_result.method_categories:
            top_method = compare_result.method_categories[0]
        top_dataset = ""
        if compare_result and compare_result.dataset_trends:
            top_dataset = compare_result.dataset_trends[0]
        scope_parts = [part for part in [top_method, top_dataset, candidate.source_context] if part]
        return {
            "topic": keywords[0] if keywords else (top_method or "current paper set"),
            "problem": statement,
            "target_scope": "; ".join(scope_parts) or "current paper set",
            "possible_direction": candidate.suggested_direction or "Refine the gap into a concrete next-step study.",
            "why_gap": (candidate.evidence_summary[0] if candidate.evidence_summary else candidate.source_context or statement),
            "verification_query_terms": keywords[:8],
            "source_paper_count": len(candidate.supporting_papers),
            "project_paper_count": len(paper_schemas),
        }

    def decompose_gap(self, candidate: GapCandidate) -> list[str]:
        """Keep a short list of verification points for logging and retrieval."""

        points = [candidate.original_statement or candidate.statement]
        if candidate.source_context:
            points.append(candidate.source_context)
        if candidate.suggested_direction:
            points.append(candidate.suggested_direction)
        return [point for point in points if point][:3]

    def build_light_query(self, candidate: GapCandidate) -> str:
        """Build one single retrieval query for light validation."""

        parts = [candidate.original_statement or candidate.statement, candidate.source_context, candidate.suggested_direction]
        return " ".join(part for part in parts if part).strip()

    @staticmethod
    def check_coverage(evidences: list[EvidenceSnippet]) -> int:
        """Count how many distinct papers are covered by evidence."""

        return len({item.paper_id for item in evidences})

    def judge_light_gap_candidate(self, candidate: GapCandidate, evidence: list[EvidenceSnippet]) -> tuple[str, str, str, float]:
        """Return status, revised text, reason, and confidence for light validation."""

        support_score = sum(item.score for item in evidence)
        coverage_count = self.check_coverage(evidence)
        original = candidate.original_statement or candidate.statement
        if coverage_count >= 2 and support_score >= 0.04:
            return "supported", original, "One-pass retrieval found clear multi-paper support for keeping this direction.", 0.82
        if evidence and (coverage_count >= 1 or support_score >= 0.012):
            return (
                "weakened",
                self.soften_statement(original),
                "Evidence points in the same direction, but the wording should be softened to avoid over-claiming.",
                0.58,
            )
        return "insufficient", self.soften_statement(original), "One-pass retrieval did not return enough direct support for a strong gap claim.", 0.28

    def build_support_queries(self, normalized_gap: dict) -> list[str]:
        """Generate multiple support-side retrieval queries for strict validation."""

        problem = normalized_gap.get("problem", "")
        topic = normalized_gap.get("topic", "")
        scope = normalized_gap.get("target_scope", "")
        direction = normalized_gap.get("possible_direction", "")
        keywords = " ".join(normalized_gap.get("verification_query_terms", [])[:5])
        return [
            " ".join(part for part in [topic, problem, "limitation challenge unresolved", scope] if part).strip(),
            " ".join(part for part in [topic, direction, "method gap benchmark comparison"] if part).strip(),
            " ".join(part for part in [topic, keywords, "future work remains challenging"] if part).strip(),
        ]

    def judge_support_strength(self, supporting_evidence: list[EvidenceSnippet]) -> dict:
        """Assess whether retrieved evidence really supports the candidate as a gap."""

        support_score = sum(item.score for item in supporting_evidence)
        support_count = len(supporting_evidence)
        distinct_paper_count = self.check_coverage(supporting_evidence)
        if distinct_paper_count >= 3 and support_score >= 0.05:
            return {
                "support_strength": "high",
                "support_reason": "Support evidence covers multiple papers with consistent retrieval signals.",
                "support_count": support_count,
                "distinct_paper_count": distinct_paper_count,
            }
        if distinct_paper_count >= 2 and support_score >= 0.02:
            return {
                "support_strength": "medium",
                "support_reason": "Support exists, but it is not broad enough yet for a very strong claim.",
                "support_count": support_count,
                "distinct_paper_count": distinct_paper_count,
            }
        return {
            "support_strength": "low",
            "support_reason": "Retrieved evidence is sparse or too concentrated to strongly support a gap claim.",
            "support_count": support_count,
            "distinct_paper_count": distinct_paper_count,
        }

    def build_counter_queries(self, candidate: GapCandidate, normalized_gap: dict | None = None) -> list[str]:
        """Generate queries intended to find conflict evidence."""

        normalized_gap = normalized_gap or {}
        problem = normalized_gap.get("problem", candidate.original_statement or candidate.statement)
        topic = normalized_gap.get("topic", "")
        return [
            " ".join(part for part in [topic, problem, "solved systematic study"] if part).strip(),
            " ".join(part for part in [topic, problem, "benchmark robust adaptive"] if part).strip(),
            " ".join(part for part in [topic, problem, "already addressed existing work"] if part).strip(),
        ]

    def summarize_counter_evidence(self, counter_evidence: list[EvidenceSnippet]) -> dict:
        """Assess how strong the counter-evidence is."""

        counter_score = sum(item.score for item in counter_evidence)
        distinct_paper_count = self.check_coverage(counter_evidence)
        if distinct_paper_count >= 2 and counter_score >= 0.05:
            return {
                "counter_strength": "high",
                "counter_reason": "Counter-evidence suggests the claimed gap may already be substantially addressed.",
                "counter_evidence_found": True,
            }
        if counter_evidence and counter_score >= 0.02:
            return {
                "counter_strength": "medium",
                "counter_reason": "Some counter-evidence exists, so the claim should be softened or treated cautiously.",
                "counter_evidence_found": True,
            }
        if counter_evidence:
            return {
                "counter_strength": "low",
                "counter_reason": "Weak counter-evidence was found, but it does not overturn the candidate on its own.",
                "counter_evidence_found": True,
            }
        return {
            "counter_strength": "low",
            "counter_reason": "No strong counter-evidence was found in the current evidence pool.",
            "counter_evidence_found": False,
        }

    def assess_coverage(
        self,
        supporting_evidence: list[EvidenceSnippet],
        paper_schemas: list[PaperSchema],
    ) -> dict:
        """Check paper-level coverage to avoid over-generalizing from a narrow sample."""

        coverage_count = self.check_coverage(supporting_evidence)
        total_papers = max(len(paper_schemas), 1)
        ratio = coverage_count / total_papers
        risks: list[str] = []
        if coverage_count < 2:
            risks.append("Support currently comes from fewer than two distinct papers.")
        if ratio < 0.5:
            risks.append("Support covers less than half of the current paper set.")
        if not risks:
            return {
                "coverage_status": "sufficient",
                "coverage_reason": "Support evidence covers a meaningful slice of the current paper set.",
                "coverage_risks": [],
            }
        if coverage_count >= 2:
            return {
                "coverage_status": "limited",
                "coverage_reason": "Support exists, but coverage is still somewhat narrow for a strong general claim.",
                "coverage_risks": risks,
            }
        return {
            "coverage_status": "insufficient",
            "coverage_reason": "Coverage is too narrow to confidently generalize this candidate as a research gap.",
            "coverage_risks": risks,
        }

    def should_trigger_external_search(
        self,
        candidate: GapCandidate,
        support_strength: str,
        counter_strength: str,
        coverage_status: str,
    ) -> bool:
        """Decide whether an external search fallback would be useful."""

        strong_claim_terms = {"no ", "none ", "unresolved", "not solved", "first"}
        statement = (candidate.original_statement or candidate.statement).lower()
        if any(term in statement for term in strong_claim_terms):
            return True
        if support_strength == "medium" and counter_strength in {"medium", "high"}:
            return True
        if coverage_status != "sufficient":
            return True
        return False

    def final_gap_decision(
        self,
        support_strength: str,
        counter_strength: str,
        coverage_status: str,
    ) -> tuple[str, float, str]:
        """Map strict validation signals into the final four-way decision."""

        if counter_strength == "high" and support_strength != "high":
            return "rejected", 0.24, "Strong counter-evidence outweighs current support."
        if support_strength == "high" and counter_strength != "high" and coverage_status == "sufficient":
            return "confirmed_gap", 0.86, "Support is strong, counter-evidence is weak, and coverage is sufficient."
        if support_strength in {"high", "medium"} and counter_strength != "high" and coverage_status in {"sufficient", "limited"}:
            return "likely_gap", 0.62, "The candidate is directionally supported, but the wording should remain cautious."
        if counter_strength == "high":
            return "rejected", 0.2, "The evidence pool suggests this gap is already addressed."
        return "insufficient_evidence", 0.34, "Current internal evidence is not strong enough for a confident gap conclusion."

    def human_review_gate(
        self,
        validation_result: str,
        support_strength: str,
        counter_strength: str,
        coverage_status: str,
        external_search_needed: bool,
    ) -> tuple[bool, str]:
        """Flag high-risk outcomes for manual review."""

        reasons: list[str] = []
        if support_strength == "high" and counter_strength == "high":
            reasons.append("support-counter conflict")
        if validation_result in {"likely_gap", "insufficient_evidence"}:
            reasons.append("non-final strict decision")
        if coverage_status != "sufficient" and validation_result != "rejected":
            reasons.append("limited coverage")
        if external_search_needed:
            reasons.append("external check recommended")
        if reasons:
            return True, ", ".join(reasons)
        return False, ""

    @staticmethod
    def attach_validation(
        candidate: GapCandidate,
        supporting: list[EvidenceSnippet],
        counter: list[EvidenceSnippet],
        coverage_count: int,
        validation_result: str,
        confidence: float,
        requires_human_review: bool,
        validation_level: str,
        validation_reason: str = "",
        normalized_gap: dict | None = None,
        support_strength: str = "",
        support_reason: str = "",
        support_count: int = 0,
        distinct_paper_count: int = 0,
        counter_strength: str = "",
        counter_reason: str = "",
        coverage_status: str = "",
        coverage_reason: str = "",
        coverage_risks: list[str] | None = None,
        external_search_used: bool = False,
        human_review_reason: str = "",
    ) -> GapCandidate:
        """Attach validation evidence to the candidate."""

        candidate.supporting_evidence = supporting
        candidate.counter_evidence = counter
        candidate.coverage_count = coverage_count
        candidate.validation_result = validation_result
        candidate.validation_level = validation_level
        candidate.confidence = confidence
        candidate.validation_reason = validation_reason
        candidate.normalized_gap = normalized_gap or {}
        candidate.support_strength = support_strength
        candidate.support_reason = support_reason
        candidate.support_count = support_count
        candidate.distinct_paper_count = distinct_paper_count
        candidate.counter_strength = counter_strength
        candidate.counter_reason = counter_reason
        candidate.coverage_status = coverage_status
        candidate.coverage_reason = coverage_reason
        candidate.coverage_risks = coverage_risks or []
        candidate.external_search_used = external_search_used
        candidate.requires_human_review = requires_human_review
        candidate.human_review_reason = human_review_reason
        candidate.evidence_summary = [
            *candidate.evidence_summary[:2],
            f"Validation level: {validation_level}",
            f"Decision: {validation_result}",
            f"Support={support_strength or 'n/a'} Counter={counter_strength or 'n/a'} Coverage={coverage_status or coverage_count}",
        ]
        return candidate

    def collect_counter_evidence_from_schemas(self, candidate: GapCandidate, paper_schemas: list[PaperSchema]) -> list[EvidenceSnippet]:
        """Build coarse counter-evidence from schema-level contradictions."""

        statement = (candidate.original_statement or candidate.statement).lower()
        counter: list[EvidenceSnippet] = []
        if "dataset" in statement or "generalization" in statement:
            for schema in paper_schemas:
                if len(schema.datasets) >= 3:
                    counter.append(
                        EvidenceSnippet(
                            paper_id=schema.paper_id,
                            content=f"{schema.title} evaluates on datasets: {', '.join(schema.datasets[:4])}",
                            score=0.03,
                        )
                    )
        if "metric" in statement or "evaluation" in statement:
            for schema in paper_schemas:
                if len(schema.metrics) >= 3:
                    counter.append(
                        EvidenceSnippet(
                            paper_id=schema.paper_id,
                            content=f"{schema.title} reports metrics: {', '.join(schema.metrics[:4])}",
                            score=0.03,
                        )
                    )
        if "limitation" in statement or "issue" in statement or "underexplored" in statement:
            for schema in paper_schemas:
                if schema.strengths:
                    counter.append(
                        EvidenceSnippet(
                            paper_id=schema.paper_id,
                            content=f"{schema.title} strength: {schema.strengths[0]}",
                            score=0.02,
                        )
                    )
        return counter[:4]

    @staticmethod
    def soften_statement(statement: str) -> str:
        """Soften over-strong wording for light validation."""

        softened = statement
        replacements = {
            "Current papers still leave": "Current papers suggest",
            "insufficiently addressed": "not yet fully addressed",
            "underexplored": "relatively less explored",
            "no ": "limited ",
            "not solved": "not yet fully solved",
        }
        for source, target in replacements.items():
            softened = softened.replace(source, target)
        return softened
