"""Small Gemini HTTP abstraction; it is never called from a route handler."""

import httpx


class GeminiConfigurationError(Exception): pass


class GeminiProviderError(Exception):
    def __init__(self, category: str = "provider_response_shape"):
        self.category = category
        super().__init__("Gemini request failed")


# This mirrors AICompletedSummary exactly. The Phase 9A validator remains the
# final authority; this schema only makes Gemini's JSON-mode response stricter.
AI_SUMMARY_RESPONSE_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["profile_summary", "requirements_analysis", "interview_questions"],
    "properties": {
        "profile_summary": {
            "type": "array", "minItems": 3, "maxItems": 5,
            "items": {"type": "string"},
        },
        "requirements_analysis": {
            "type": "object", "additionalProperties": False,
            "required": ["requirements_mentioned", "requirements_not_found"],
            "properties": {
                "requirements_mentioned": {"type": "array", "items": {"type": "string"}},
                "requirements_not_found": {"type": "array", "items": {"type": "string"}},
            },
        },
        "interview_questions": {
            "type": "array", "minItems": 3, "maxItems": 3,
            "items": {"type": "string"},
        },
    },
}


class GeminiProvider:
    def __init__(self, api_key: str | None, model: str, timeout_seconds: float = 120.0):
        self.api_key, self.model, self.timeout_seconds = api_key, model, timeout_seconds

    def generate_summary(self, prompt: str) -> str:
        if not self.api_key:
            raise GeminiConfigurationError("Gemini is not configured")
        try:
            response = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                params={"key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "responseJsonSchema": AI_SUMMARY_RESPONSE_JSON_SCHEMA,
                    },
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return self._usable_text(response.json())
        except httpx.TimeoutException as error:
            raise GeminiProviderError("provider_timeout") from error
        except httpx.HTTPError as error:
            raise GeminiProviderError("provider_http") from error
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise GeminiProviderError("provider_response_shape") from error

    @staticmethod
    def _usable_text(data: object) -> str:
        """Return the final non-thought text part without retaining provider output."""
        if not isinstance(data, dict) or not isinstance(data.get("candidates"), list):
            raise ValueError("invalid candidate response")
        for candidate in data["candidates"]:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content")
            parts = content.get("parts") if isinstance(content, dict) else None
            if not isinstance(parts, list):
                continue
            for part in reversed(parts):
                if not isinstance(part, dict) or part.get("thought") is True:
                    continue
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    return text
        raise ValueError("no usable text response")
