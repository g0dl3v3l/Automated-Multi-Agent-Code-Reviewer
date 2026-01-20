"""
The Judge Component.

This module contains the logic for evaluating findings from all agents,
calculating quality scores, and issuing a final verdict for the Pull Request.
"""
from typing import List, Dict, Any, Set
from collections import Counter
from src.schemas.common import ReviewIssue, FinalVerdict, Severity
from src.utils.logger import get_logger

logger = get_logger(__name__)

class Judge:
    """
    The Decision Maker.

    Aggregates issues from multiple agents, deduplicates findings based on
    range and content, and produces a final quality score and verdict.
    """

    def evaluate(self, issues: List[ReviewIssue]) -> Dict[str, Any]:
        """
        Analyzes the aggregated issues to produce a final report.

        This method performs three key actions:
        1. Deduplicates issues to remove redundant findings.
        2. Calculates a weighted 'Quality Score' (0-100) based on severity.
        3. Determines the final verdict (APPROVE, REQUEST_CHANGES, etc.).

        Args:
            issues (List[ReviewIssue]): A raw list of issues collected from all agents.

        Returns:
            Dict[str, Any]: A dictionary containing the evaluation results, structured
            to match the `ReviewMeta` schema fields:
                - final_verdict (FinalVerdict): The decision (e.g., APPROVE).
                - quality_score (int): The calculated score (0-100).
                - risk_level (str): The overall risk (SAFE, HIGH, CRITICAL).
                - total_vulnerabilities (int): Count of unique issues.
                - summary (str): A human-readable summary string.
                - clean_issues (List[ReviewIssue]): The deduplicated list of issues.
        """
        # 1. Deduplication (Now Multi-Line Aware)
        clean_issues = self._deduplicate_issues(issues)
        logger.info(f"Judge processed {len(issues)} raw issues -> {len(clean_issues)} unique issues.")

        # 2. Scoring & Counting Logic (Using CLEAN issues)
        score = 100
        critical_count = 0
        high_count = 0
        category_counts = Counter()

        for issue in clean_issues:
            # Deduction
            deduction = self._get_deduction(issue.severity)
            score -= deduction
            
            # Severity Counters
            if issue.severity == Severity.CRITICAL:
                critical_count += 1
            if issue.severity == Severity.HIGH:
                high_count += 1
            
            # Category Counter
            category_counts[issue.category] += 1

        score = max(0, min(100, score)) # Clamp 0-100

        # 3. Risk Level
        if critical_count > 0:
            risk_level = "CRITICAL"
        elif high_count > 0:
            risk_level = "HIGH"
        else:
            risk_level = "SAFE"

        # 4. Verdict
        final_verdict = self._determine_verdict(score, critical_count)

        # 5. Summary
        cat_summary = ", ".join([f"{count} {cat.value}" for cat, count in category_counts.items()])
        if not cat_summary:
            cat_summary = "0 issues"
        
        summary_text = f"Found {len(clean_issues)} unique issues ({cat_summary}). Risk: {risk_level}."

        logger.info(f"Verdict: {final_verdict.value} | Score: {score} | Breakdown: {cat_summary}")

        return {
            "final_verdict": final_verdict,
            "quality_score": score,
            "risk_level": risk_level,
            "total_vulnerabilities": len(clean_issues),
            "summary": summary_text,
            "clean_issues": clean_issues 
        }

    def _deduplicate_issues(self, issues: List[ReviewIssue]) -> List[ReviewIssue]:
        """
        Removes exact duplicates while respecting multi-line ranges.

        Creates a unique fingerprint for each issue. If multiple agents report
        the exact same issue (same file, range, category, and title), only one
        instance is preserved.

        Args:
            issues (List[ReviewIssue]): The raw list of issues.

        Returns:
            List[ReviewIssue]: A sorted list of unique issues.
        """
        unique_issues = []
        seen_fingerprints: Set[str] = set()

        # Sort by line number so they appear nicely in the UI
        sorted_issues = sorted(issues, key=lambda x: (x.file_path, x.line_start))

        for issue in sorted_issues:
            # The Multi-Line Aware Fingerprint
            # We include Category and Title to allow "stacking" (different issues on same line)
            fingerprint = f"{issue.file_path}|{issue.line_start}|{issue.line_end}|{issue.category}|{issue.title}"
            
            if fingerprint not in seen_fingerprints:
                seen_fingerprints.add(fingerprint)
                unique_issues.append(issue)
            else:
                logger.debug(f"Duplicate issue dropped: {fingerprint}")
        
        return unique_issues

    def _get_deduction(self, severity: Severity) -> int:
        """
        Determines the score penalty for a given severity level.

        Args:
            severity (Severity): The severity enum of the issue.

        Returns:
            int: The number of points to deduct from the quality score.
        """
        if severity == Severity.CRITICAL: return 40
        if severity == Severity.HIGH: return 15
        if severity == Severity.MEDIUM: return 5
        if severity == Severity.LOW: return 1
        return 0

    def _determine_verdict(self, score: int, critical_count: int) -> FinalVerdict:
        """
        Decides the final verdict based on the score and critical issues.

        Enforces a Zero Tolerance Policy: Any critical issue results in
        REQUEST_CHANGES, regardless of the numeric score.

        Args:
            score (int): The final calculated quality score (0-100).
            critical_count (int): The number of critical issues found.

        Returns:
            FinalVerdict: The decision (APPROVE, COMMENT_ONLY, REQUEST_CHANGES).
        """
        if critical_count > 0:
            return FinalVerdict.REQUEST_CHANGES
        if score >= 90:
            return FinalVerdict.APPROVE
        elif score >= 70:
            return FinalVerdict.COMMENT_ONLY
        else:
            return FinalVerdict.REQUEST_CHANGES