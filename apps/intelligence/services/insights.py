import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from django.conf import settings

from apps.intelligence.services.attribute_semantics import HIGHER_IS_BETTER, LOWER_IS_BETTER

logger = logging.getLogger("apps.intelligence")

SYSTEM_PROMPT = (
    "You are an automotive competitive intelligence analyst.\n"
    "You compare vehicles based ONLY on the structured data provided.\n"
    "Never invent specifications. If data is missing, say so.\n"
    "Respond in Brazilian Portuguese, in 3 to 5 short sentences.\n"
    "Do not use markdown headings. Do not use bullet lists. Plain prose only."
)


class InsightsUpstreamError(Exception):
    pass


class InsightsFeatureDisabledError(Exception):
    pass


@dataclass
class InsightResult:
    summary: str
    key_differences: list[dict] = field(default_factory=list)
    model: str = ""
    generated_at: str = ""


class InsightsBuilder:
    def build_prompt(
        self, vehicles_data: list[dict], attributes: list[str], focus: str | None
    ) -> tuple[str, str]:
        user_prompt = (
            "Compare the following vehicles using only the data below.\n"
            "Highlight the most relevant differences for a buyer.\n\n"
            f"Vehicles:\n{json.dumps(vehicles_data, ensure_ascii=False, indent=2)}\n\n"
            f"Optional buyer focus: {focus or 'general comparison'}\n\n"
            "Output a single paragraph (3-5 sentences)."
        )
        return SYSTEM_PROMPT, user_prompt

    def compute_key_differences(
        self, vehicles_data: list[dict], attributes: list[str]
    ) -> list[dict]:
        """Deterministic key differences — no LLM involved."""
        differences = []

        for key in attributes:
            per_vehicle: list[tuple[str, object]] = []
            for v in vehicles_data:
                slug = v.get("version") or v.get("slug", "")
                value = None
                for attr in v.get("attributes", []):
                    if attr.get("key") == key:
                        value = attr.get("value")
                        break
                per_vehicle.append((slug, value))

            values_only = [val for _, val in per_vehicle if val is not None]
            if not values_only:
                continue

            all_vals = [val for _, val in per_vehicle]
            has_missing = any(v is None for v in all_vals)
            all_non_none_equal = len(set(values_only)) == 1
            if all_non_none_equal and not has_missing:
                continue

            diff: dict = {"attribute": key}

            sample_value = values_only[0]

            if isinstance(sample_value, bool):
                winners = [slug for slug, val in per_vehicle if val is True]
                diff["values"] = {slug: val for slug, val in per_vehicle}
                if winners:
                    diff["winner"] = winners[0] if len(winners) == 1 else winners
                differences.append(diff)

            elif isinstance(sample_value, (int, float)):
                numeric_vals = [(slug, val) for slug, val in per_vehicle if val is not None]
                diff["values"] = {slug: val for slug, val in numeric_vals}

                if key in HIGHER_IS_BETTER:
                    best_val = max(v for _, v in numeric_vals)
                    winners = [s for s, v in numeric_vals if v == best_val]
                    diff["winner"] = winners[0] if len(winners) == 1 else winners
                elif key in LOWER_IS_BETTER:
                    best_val = min(v for _, v in numeric_vals)
                    winners = [s for s, v in numeric_vals if v == best_val]
                    diff["winner"] = winners[0] if len(winners) == 1 else winners
                # else: neutral — no winner

                differences.append(diff)

        return differences


class InsightsClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int,
        temperature: float,
        timeout: int,
    ):
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._timeout = timeout

    def generate(
        self,
        vehicles_data: list[dict],
        requested_attributes: list[str],
        focus: str | None,
    ) -> InsightResult:
        from openai import OpenAI, OpenAIError

        builder = InsightsBuilder()
        system_prompt, user_prompt = builder.build_prompt(
            vehicles_data, requested_attributes, focus
        )

        try:
            client = OpenAI(api_key=self._api_key, timeout=self._timeout)
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )
            summary = response.choices[0].message.content
            if not summary or not summary.strip():
                raise InsightsUpstreamError("Empty response from model.")
        except OpenAIError as exc:
            logger.error("OpenAI call failed: %s", type(exc).__name__)
            raise InsightsUpstreamError("Upstream model unavailable.") from None

        key_diffs = builder.compute_key_differences(vehicles_data, requested_attributes)

        return InsightResult(
            summary=summary.strip(),
            key_differences=key_diffs,
            model=self._model,
            generated_at=datetime.now(tz=UTC).isoformat(),
        )


def get_default_client() -> InsightsClient:
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        raise InsightsFeatureDisabledError("OPENAI_API_KEY is not configured.")
    return InsightsClient(
        api_key=api_key,
        model=settings.OPENAI_MODEL,
        max_tokens=settings.OPENAI_MAX_TOKENS,
        temperature=settings.OPENAI_TEMPERATURE,
        timeout=settings.OPENAI_TIMEOUT_SEC,
    )
