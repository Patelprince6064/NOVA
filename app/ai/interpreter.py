"""LLM-backed natural language interpreter for Nova Phase 5.

The interpreter converts transcribed text into validated structured actions.
It NEVER executes PC actions — it only returns validated dicts.
LLM output is treated as untrusted: JSON parsed, schema validated, allowlisted.

Fast path: local router handles known exact commands without LLM.

If LLM disabled / no key / failure / timeout / invalid schema -> returns None
and caller should fall back to local routing or error message.

Only sends transcribed text (plus allowed schema) to LLM — no audio, files, screenshots.
"""

import json
import logging
import re
import time
from typing import Optional, Dict, Any, Tuple

from app.config import Config
from app.ai.prompts import SYSTEM_PROMPT
from app.ai.schemas import validate_action

logger = logging.getLogger(__name__)

# Allowed simple patterns for local fast-path without LLM — reused from actions
# Instead of duplicating, we will try local router first; interpreter is only for ambiguous.


class CommandInterpreter:
    """LLM provider abstraction. Currently supports openai."""

    def __init__(self, config: Config):
        self.enabled = config.llm_enabled
        self.provider = config.llm_provider.lower().strip() if config.llm_provider else "openai"
        self.model = config.llm_model.strip() if config.llm_model else ""
        self.api_key = config.llm_api_key.strip() if config.llm_api_key else ""
        self.timeout = int(config.llm_timeout_seconds) if config.llm_timeout_seconds else 10

        # Default models if not configured
        if not self.model:
            if self.provider == "openai":
                self.model = "gpt-4o-mini"
            else:
                self.model = "gpt-4o-mini"

        # Trim key for logging safety — never log full key
        key_hint = (self.api_key[:4] + "…") if self.api_key else "none"
        logger.info("CommandInterpreter init: enabled=%s provider=%s model=%s key=%s timeout=%s",
                    self.enabled, self.provider, self.model, key_hint, self.timeout)

    def is_available(self) -> bool:
        return bool(self.enabled and self.api_key and self.provider in ("openai",))

    def _extract_json(self, raw: str) -> Optional[str]:
        """Extract JSON object from LLM response (handle markdown code blocks)."""
        if not raw:
            return None
        s = raw.strip()
        # Remove markdown code fences
        if "```" in s:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL)
            if m:
                return m.group(1).strip()
        # Find first { ... } block
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            return s[start:end+1]
        return s if s.startswith("{") else None

    def interpret(self, text: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """Interpret text via LLM. Returns (validated_action_dict_or_None, error_message).

        Validated dict will have 'action' key if successful. None means failure
        — caller should handle fallback.
        """
        if not text or not text.strip():
            return None, "Empty text"
        if not self.is_available():
            logger.debug("LLM interpreter not available (disabled/no key)")
            return None, "LLM not configured"

        # Only send transcribed text + schema — no sensitive data
        user_msg = text.strip()
        # Truncate very long input to avoid cost/abuse
        if len(user_msg) > 500:
            user_msg = user_msg[:500]
            logger.warning("Truncated LLM input to 500 chars")

        logger.info("LLM interpreter called for: %r", user_msg[:80])
        t0 = time.perf_counter()

        try:
            raw_response = self._call_llm(user_msg)
            dt = time.perf_counter() - t0
            logger.info("LLM responded in %.2fs", dt)
            if not raw_response or not raw_response.strip():
                logger.warning("LLM empty response")
                return None, "Empty LLM response"

            json_str = self._extract_json(raw_response)
            if not json_str:
                logger.warning("Failed to extract JSON from LLM: %r", raw_response[:200])
                return None, "Invalid LLM output"

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as exc:
                logger.warning("LLM JSON parse failed: %s raw=%r", exc, json_str[:300])
                return None, f"Invalid JSON: {exc}"

            # Validate against strict schema
            ok, err, normalized = validate_action(data)
            if not ok:
                logger.warning("LLM action validation failed: %s data=%r", err, data)
                return None, f"Validation failed: {err}"
            logger.info("LLM validated action: %r", normalized)
            return normalized, ""

        except TimeoutError as exc:
            logger.warning("LLM timeout after %ds: %s", self.timeout, exc)
            return None, "LLM timeout"
        except Exception as exc:
            logger.warning("LLM interpreter error: %s", exc)
            return None, str(exc)

    def _call_llm(self, user_text: str) -> str:
        """Call provider. Currently openai."""
        if self.provider != "openai":
            raise RuntimeError(f"Unsupported LLM provider: {self.provider}")

        # Lazy import openai
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package not installed. pip install openai")

        if not self.api_key:
            raise RuntimeError("LLM_API_KEY not configured")

        client = OpenAI(api_key=self.api_key, timeout=self.timeout)
        # Use chat completions — ask for JSON object
        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_text},
                ],
                temperature=0.1,
                max_tokens=300,
                timeout=self.timeout,
                # Request JSON mode if supported
                response_format={"type": "json_object"} if self.model.startswith("gpt-4") or "mini" in self.model else None,
            )
        except TypeError:
            # Fallback without response_format for older models/clients
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_text},
                ],
                temperature=0.1,
                max_tokens=300,
                timeout=self.timeout,
            )

        if not resp.choices or not resp.choices[0].message or not resp.choices[0].message.content:
            return ""
        return resp.choices[0].message.content.strip()
