"""The Judge module responsible for scoring and verdicts.

This module defines the `Judge` class, which acts as the deterministic logic engine
for the review process. It aggregates issues found by various agents, calculates
a quality score based on a penalty system, and determines the final verdict
(Approve/Reject) based on risk thresholds.
"""


from typing import List, Dict, Any
from src.schemas.common import ReviewIssue, FinalVerdict, Severity
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Judge:
    """
    The Decision Maker.
    Aggregates issues to produce the final_verdict and quality_score.
    """

    def evaluate(self, issues: List[ReviewIssue]) -> Dict[str, Any]:
        """
        Analyzes the aggregated issues.
        Returns a dictionary matched to the ReviewMeta fields.
        """
        logger.info(f"Judge evaluating {len(issues)} aggregate issues...")

        # 1. Scoring Logic
        score = 100
        critical_count = 0
        high_count = 0
        
        for issue in issues:
            deduction = self._get_deduction(issue.severity)
            score -= deduction
            
            if issue.severity == Severity.CRITICAL:
                critical_count += 1
            if issue.severity == Severity.HIGH:
                high_count += 1

        score = max(0, min(100, score)) # Clamp 0-100

        # 2. Risk Level Calculation
        if critical_count > 0:
            risk_level = "CRITICAL"
        elif high_count > 0:
            risk_level = "HIGH"
        else:
            risk_level = "SAFE"

        # 3. Verdict Logic
        final_verdict = self._determine_verdict(score, critical_count)

        logger.info(f"Verdict: {final_verdict.value} | Score: {score}")

        return {
            "final_verdict": final_verdict,
            "quality_score": score,
            "risk_level": risk_level,
            "total_vulnerabilities": len(issues),
            "summary": f"Found {len(issues)} issues. Risk Level: {risk_level}."
        }

    def _get_deduction(self, severity: Severity) -> int:
        if severity == Severity.CRITICAL: return 40
        if severity == Severity.HIGH: return 15
        if severity == Severity.MEDIUM: return 5
        if severity == Severity.LOW: return 1
        return 0

    def _determine_verdict(self, score: int, critical_count: int) -> FinalVerdict:
        if critical_count > 0:
            return FinalVerdict.REQUEST_CHANGES
        
        if score >= 90:
            return FinalVerdict.APPROVE
        elif score >= 70:
            return FinalVerdict.COMMENT_ONLY
        else:
            return FinalVerdict.REQUEST_CHANGES