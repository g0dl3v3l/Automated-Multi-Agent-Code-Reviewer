"""The Judge module responsible for scoring and verdicts.

This module defines the `Judge` class, which acts as the deterministic logic engine
for the review process. It aggregates issues found by various agents, calculates
a quality score based on a penalty system, and determines the final verdict
(Approve/Reject) based on risk thresholds.
"""

from typing import List, Dict
from src.schemas.common import ReviewIssue, ReviewMeta, Severity, FinalVerdict
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Judge:
    """Evaluates collected review issues to generate scores and verdicts.

    Attributes:
        PENALTIES (Dict[Severity, int]): A mapping of issue severity to score
            deductions.
    """

    PENALTIES: Dict[Severity, int] = {
        Severity.CRITICAL: 25,
        Severity.HIGH: 15,
        Severity.MEDIUM: 5,
        Severity.LOW: 2,
        Severity.NITPICK: 0,
    }

    def evaluate(self, issues: List[ReviewIssue], duration_ms: float) -> ReviewMeta:
        """Calculates the quality score and determines the final verdict.

        The score starts at 100 and decreases based on the severity of the issues
        found. The verdict is determined by the presence of critical issues or
        if the score falls below specific thresholds.

        Args:
            issues (List[ReviewIssue]): The list of issues identified by all agents.
            duration_ms (float): The total time taken for the scan in milliseconds.

        Returns:
            ReviewMeta: A metadata object containing the score, verdict, risk level,
                and summary statistics.
        """
        score = 100
        critical_count = 0

        for issue in issues:
            penalty = self.PENALTIES.get(issue.severity, 0)
            score -= penalty
            if issue.severity == Severity.CRITICAL:
                critical_count += 1

        # Ensure score does not drop below zero
        score = max(0, score)

        # Determine Verdict and Risk Level
        if critical_count > 0:
            verdict = FinalVerdict.REQUEST_CHANGES
            risk = "CRITICAL"
        elif score < 70:
            verdict = FinalVerdict.REQUEST_CHANGES
            risk = "HIGH" if score < 50 else "MEDIUM"
        else:
            verdict = FinalVerdict.APPROVE
            risk = "LOW"

        return ReviewMeta(
            final_verdict=verdict,
            quality_score=score,
            risk_level=risk,
            total_vulnerabilities=len(issues),
            scan_duration_ms=duration_ms,
        )

    def generate_summary(self, issues: List[ReviewIssue]) -> str:
        """Generates a text summary of the findings.

        Currently uses simple aggregation logic. In future iterations, this will
        delegate to an LLM for a natural language summary.

        Args:
            issues (List[ReviewIssue]): The list of issues identified.

        Returns:
            str: A formatted string summarizing the count and breakdown of issues.
        """
        if not issues:
            return "No significant issues found. The code looks clean."

        counts = {}
        for i in issues:
            counts[i.category] = counts.get(i.category, 0) + 1

        summary = f"Scan complete. Found {len(issues)} issues. "
        breakdown = ", ".join([f"{k}: {v}" for k, v in counts.items()])
        summary += f"Breakdown: {breakdown}."
        
        return summary