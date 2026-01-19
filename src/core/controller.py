"""The Review Controller module.

This module orchestrates the entire code review lifecycle. It serves as the
main entry point for the analysis logic, responsible for dispatching source
files to registered agents, handling asynchronous execution, and aggregating
the results for the Judge.
"""

import time
import asyncio
from typing import List, Any
from src.schemas.common import (
    SourceFile,
    ReviewResponse,
    AgentPayload,
    ReviewContext,
    ReviewIssue,
    ReviewMeta,
    FinalVerdict

)
from src.core.registry import AgentRegistry
from src.core.judge import Judge
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ReviewController:
    """Manages the execution of the code review process.

    This class handles the parallel execution of agents and ensures that
    exceptions in one agent do not halt the entire review process.

    Attributes:
        judge (Judge): The logic engine used to evaluate results.
    """

    def __init__(self):
        """Initializes the ReviewController with a Judge instance."""
        self.judge = Judge()

    
    
    async def run_full_scan(
        self, files: List[SourceFile], review_id: str
    ) -> ReviewResponse:
        """Executes a full system scan using all registered agents.

        This method wraps the files in an `AgentPayload`, dispatches them to
        all agents found in the `AgentRegistry` via `asyncio.gather`, and
        then passes the aggregated results to the `Judge`.

        Args:
            files (List[SourceFile]): The list of source files to analyze.
            review_id (str): A unique identifier for this review request.

        Returns:
            ReviewResponse: The complete review report, including metadata,
                summary, and detailed comments.
        """
        start_time = time.time()
        
        # 1. Prepare Payload
        payload = AgentPayload(
            target_files=files, context=ReviewContext()
        )

        # 2. Run Agents (Security)
        agents = AgentRegistry.get_all()
        if not agents:
             return self._build_empty_response(review_id, 0.0)

        logger.info(f"Dispatching to {len(agents)} agents...")
        tasks = [self._safe_run_agent(agent, payload) for agent in agents]
        results = await asyncio.gather(*tasks)

        # Flatten list of lists
        all_issues = []
        for agent_issues in results:
            all_issues.extend(agent_issues)

        duration_ms = (time.time() - start_time) * 1000

        # 3. Call Judge
        judge_result = self.judge.evaluate(all_issues)

        # 4. Construct Meta (Strict Adherence to Contract)
        review_meta = ReviewMeta(
            final_verdict=judge_result["final_verdict"],
            quality_score=judge_result["quality_score"],
            risk_level=judge_result["risk_level"],
            total_vulnerabilities=judge_result["total_vulnerabilities"],
            scan_duration_ms=duration_ms
        )

        # 5. Return Final Response
        return ReviewResponse(
            review_id=review_id,
            timestamp=str(time.time()),
            meta=review_meta,
            summary=judge_result["summary"],
            praise=["System operational."],
            comments=all_issues
        )

    async def _safe_run_agent(self, agent: Any, payload: AgentPayload) -> List[ReviewIssue]:
        """Runs a single agent safely, catching and logging any exceptions.

        This method wraps the synchronous `agent.run` method in a thread to
        prevent blocking the async event loop.

        Args:
            agent (BaseAgent): The agent instance to execute.
            payload (AgentPayload): The input data for the agent.

        Returns:
            List[ReviewIssue]: The issues found by the agent, or an empty list
                if the agent failed.
        """
        try:
            # Run the synchronous agent logic in a separate thread
            return await asyncio.to_thread(agent.run, payload)
        except Exception as e:
            logger.error(f"Agent {agent.name} failed: {e}")
            return []

    def _build_empty_response(self, review_id: str, duration: float) -> ReviewResponse:
        """Constructs an empty response when no agents are available.

        Args:
            review_id (str): The unique ID for the request.
            duration (float): The duration of the 'scan'.

        Returns:
            ReviewResponse: A response object with zero issues.
        """
        return ReviewResponse(
            review_id=review_id,
            timestamp=str(time.time()),
            meta=ReviewMeta(
                final_verdict=FinalVerdict.COMMENT_ONLY,
                quality_score=0,
                risk_level="Unknown",
                total_vulnerabilities=0,
                scan_duration_ms=duration
            ),
            summary="No agents were active.",
            praise=[],
            comments=[],
        )