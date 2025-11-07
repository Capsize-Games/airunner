"""
LLM-as-judge evaluators for AI Runner eval testing.

Provides evaluators that use an LLM to judge the quality of model outputs
against reference answers. Supports multiple evaluation criteria like
correctness, conciseness, helpfulness, etc.

Based on the openevals pattern but adapted for AI Runner's architecture.
"""

from typing import Dict, Any, Optional
from airunner.components.eval.client import AIRunnerClient
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)


# Evaluation prompt templates
CORRECTNESS_PROMPT = """You are an expert evaluator assessing the correctness of an AI assistant's response.

Question/Prompt:
{inputs}

Reference Answer:
{reference_outputs}

Assistant's Answer:
{outputs}

Task: Evaluate how correct and accurate the assistant's answer is compared to the reference answer.

Provide your evaluation in the following format:
Score: [0-10, where 0 is completely incorrect and 10 is perfectly correct]
Reasoning: [Brief explanation of your score]

Evaluation:"""

CONCISENESS_PROMPT = """You are an expert evaluator assessing the conciseness of an AI assistant's response.

Question/Prompt:
{inputs}

Reference Answer:
{reference_outputs}

Assistant's Answer:
{outputs}

Task: Evaluate how concise the assistant's answer is. A good answer should be brief while still being complete and accurate.

Provide your evaluation in the following format:
Score: [0-10, where 0 is extremely verbose/wasteful and 10 is perfectly concise]
Reasoning: [Brief explanation of your score]

Evaluation:"""

HELPFULNESS_PROMPT = """You are an expert evaluator assessing the helpfulness of an AI assistant's response.

Question/Prompt:
{inputs}

Reference Answer:
{reference_outputs}

Assistant's Answer:
{outputs}

Task: Evaluate how helpful the assistant's answer is for someone asking this question.

Provide your evaluation in the following format:
Score: [0-10, where 0 is not helpful at all and 10 is extremely helpful]
Reasoning: [Brief explanation of your score]

Evaluation:"""

RELEVANCE_PROMPT = """You are an expert evaluator assessing the relevance of an AI assistant's response.

Question/Prompt:
{inputs}

Reference Answer:
{reference_outputs}

Assistant's Answer:
{outputs}

Task: Evaluate how relevant the assistant's answer is to the question asked.

Provide your evaluation in the following format:
Score: [0-10, where 0 is completely off-topic and 10 is perfectly relevant]
Reasoning: [Brief explanation of your score]

Evaluation:"""


class LLMAsJudge:
    """LLM-as-judge evaluator using AI Runner client.

    Uses an LLM to evaluate the quality of another LLM's outputs
    against reference answers.

    Args:
        client: AIRunnerClient instance to use for evaluation
        prompt_template: Template string with {inputs}, {outputs}, {reference_outputs}
        feedback_key: Key name for this evaluation metric
        model: Optional model name to use for judging

    Attributes:
        client: The AIRunnerClient instance
        prompt_template: The evaluation prompt template
        feedback_key: The metric name
        model: Model to use for evaluation
    """

    def __init__(
        self,
        client: AIRunnerClient,
        prompt_template: str,
        feedback_key: str,
        model: Optional[str] = None,
    ):
        """Initialize the LLM-as-judge evaluator.

        Args:
            client: AIRunnerClient instance
            prompt_template: Prompt template with placeholders
            feedback_key: Name of the evaluation metric
            model: Optional model name
        """
        self.client = client
        self.prompt_template = prompt_template
        self.feedback_key = feedback_key
        self.model = model
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    def _format_evaluation_prompt(
        self, inputs: str, outputs: str, reference_outputs: str
    ) -> str:
        """Format evaluation prompt with inputs."""
        return self.prompt_template.format(
            inputs=inputs,
            outputs=outputs,
            reference_outputs=reference_outputs,
        )

    def _get_llm_judgment(self, eval_prompt: str) -> str:
        """Get LLM's evaluation judgment."""
        kwargs = {
            "use_memory": False,
            "tool_categories": [],
        }
        if self.model:
            kwargs["model"] = self.model

        response = self.client.generate(
            eval_prompt,
            temperature=0.3,
            max_tokens=500,
            **kwargs,
        )

        return response.get("text", "")

    def __call__(
        self,
        inputs: str,
        outputs: str,
        reference_outputs: str,
    ) -> Dict[str, Any]:
        """Evaluate outputs against reference using LLM.

        Args:
            inputs: The original question/prompt
            outputs: The assistant's answer to evaluate
            reference_outputs: The reference/expected answer

        Returns:
            Dict with 'score', 'reasoning', and 'feedback_key' fields
        """
        eval_prompt = self._format_evaluation_prompt(
            inputs, outputs, reference_outputs
        )

        try:
            evaluation_text = self._get_llm_judgment(eval_prompt)
            score, reasoning = self._parse_evaluation(evaluation_text)
            return self._create_result(score, reasoning, evaluation_text)

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return self._create_error_result(e)

    def _create_result(
        self, score: float, reasoning: str, evaluation_text: str
    ) -> Dict[str, Any]:
        """Create successful evaluation result."""
        result = {
            "feedback_key": self.feedback_key,
            "score": score,
            "reasoning": reasoning,
            "raw_evaluation": evaluation_text,
        }
        self.logger.debug(f"{self.feedback_key}: {score}/10 - {reasoning}")
        return result

    def _create_error_result(self, error: Exception) -> Dict[str, Any]:
        """Create error evaluation result."""
        return {
            "feedback_key": self.feedback_key,
            "score": 0,
            "reasoning": f"Evaluation error: {error}",
            "raw_evaluation": "",
        }

    def _parse_evaluation(self, text: str) -> tuple[float, str]:
        """Parse score and reasoning from LLM evaluation text.

        Args:
            text: Raw evaluation text from LLM

        Returns:
            Tuple of (score, reasoning)
        """
        score = 0.0
        reasoning = ""

        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("Score:"):
                score = self._parse_score_line(line)
            elif line.startswith("Reasoning:"):
                reasoning = self._parse_reasoning_line(line)

        return score, reasoning

    def _parse_score_line(self, line: str) -> float:
        """Parse score from a line."""
        score_text = line.replace("Score:", "").strip()
        score_text = score_text.split()[0].strip("[](),")
        try:
            score = float(score_text)
            # Normalize to 0-1 range if it's 0-10
            if score > 1.0:
                score = score / 10.0
            return score
        except ValueError:
            self.logger.warning(f"Could not parse score from: {score_text}")
            return 0.0

    def _parse_reasoning_line(self, line: str) -> str:
        """Parse reasoning from a line."""
        reasoning_text = line.replace("Reasoning:", "").strip()

        if not reasoning_text:
            return ""

        # Handle duplicate text (LLM sometimes repeats itself)
        half_len = len(reasoning_text) // 2
        if half_len > 10:
            first_half = reasoning_text[:half_len]
            second_half = reasoning_text[half_len : half_len * 2]
            if first_half == second_half:
                return first_half

        return reasoning_text


def create_correctness_evaluator(
    client: AIRunnerClient,
    model: Optional[str] = None,
) -> LLMAsJudge:
    """Create a correctness evaluator.

    Args:
        client: AIRunnerClient instance
        model: Optional model name

    Returns:
        LLMAsJudge evaluator for correctness
    """
    return LLMAsJudge(
        client=client,
        prompt_template=CORRECTNESS_PROMPT,
        feedback_key="correctness",
        model=model,
    )


def create_conciseness_evaluator(
    client: AIRunnerClient,
    model: Optional[str] = None,
) -> LLMAsJudge:
    """Create a conciseness evaluator.

    Args:
        client: AIRunnerClient instance
        model: Optional model name

    Returns:
        LLMAsJudge evaluator for conciseness
    """
    return LLMAsJudge(
        client=client,
        prompt_template=CONCISENESS_PROMPT,
        feedback_key="conciseness",
        model=model,
    )


def create_helpfulness_evaluator(
    client: AIRunnerClient,
    model: Optional[str] = None,
) -> LLMAsJudge:
    """Create a helpfulness evaluator.

    Args:
        client: AIRunnerClient instance
        model: Optional model name

    Returns:
        LLMAsJudge evaluator for helpfulness
    """
    return LLMAsJudge(
        client=client,
        prompt_template=HELPFULNESS_PROMPT,
        feedback_key="helpfulness",
        model=model,
    )


def create_relevance_evaluator(
    client: AIRunnerClient,
    model: Optional[str] = None,
) -> LLMAsJudge:
    """Create a relevance evaluator.

    Args:
        client: AIRunnerClient instance
        model: Optional model name

    Returns:
        LLMAsJudge evaluator for relevance
    """
    return LLMAsJudge(
        client=client,
        prompt_template=RELEVANCE_PROMPT,
        feedback_key="relevance",
        model=model,
    )
