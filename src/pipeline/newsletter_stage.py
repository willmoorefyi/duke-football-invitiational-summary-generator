"""
Newsletter Stage

Stage 6: Roast Newsletter Generation
Generates the humorous weekly HTML email from the condensed JSON via Amazon Bedrock.
Grounded entirely in the supplied condensed data; writes an audit record per edition.

Generation is multi-call: one Bedrock Converse call per section (intro/summary,
matchups, awards, recap), then the fragments are assembled into one HTML email. This
honors the prompt's "write in phases" instruction and avoids the single-call
max_tokens truncation observed in the Step-0 spike.
"""

import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import PipelineStage

# AWS imports (mirrors deploy_stage's optional-import guard)
try:
    import boto3
    from botocore.config import Config as BotoConfig
    AWS_AVAILABLE = True
except ImportError:
    boto3 = None
    BotoConfig = None
    AWS_AVAILABLE = False

# Required top-level keys in the condensed JSON; fail fast if missing.
REQUIRED_KEYS = ("league_name", "week", "team_standings", "matchups", "awards")

# (key, human description) for each section-scoped Bedrock call, in email order.
SECTIONS: List[Tuple[str, str]] = [
    ("intro", "Section 1 (the email subject line, header, intro, and summary)"),
    ("matchups", "Section 2 (the matchup summaries)"),
    ("awards", "Section 3 (the awards)"),
    ("recap", "Section 4 (the final recap)"),
]

# Bedrock read can take >2min for a large model; extend the default 60s read timeout.
_READ_TIMEOUT_SECONDS = 600

# Design guardrails enforced on the assembled HTML regardless of what the model emits.
APPROVED_FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
_BANNED_FONT_TOKENS = ("impact", "arial black", "comic sans")
_SOFT_WHITE = "#e8e8e8"  # off-white body text; pure #fff on dark backgrounds causes glare


class NewsletterStage(PipelineStage):
    """
    Stage 6: Roast Newsletter Generation.

    Reads condensed JSON + versioned prompts, calls Bedrock once per section, assembles
    the HTML email locally, and records an audit row in DynamoDB.
    """

    def execute(
        self,
        condensed_file: str,
        prompt_version: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Generate the roast newsletter from a condensed JSON file.

        Args:
            condensed_file: Path to the condensed JSON (from the aggregate stage).
            prompt_version: Prompt version to use (defaults to config).
            output_dir: Output directory for the HTML email (defaults to config).

        Returns:
            Tuple of (html_file_path, metadata).
        """
        cfg = self.config.pipeline.newsletter
        prompt_version = prompt_version or cfg.prompt_version
        output_dir = output_dir or cfg.output_dir
        model_id = cfg.bedrock_model_id
        region = cfg.region or self.config.pipeline.aws.region

        self.logger.info(
            f"Starting newsletter generation for {condensed_file} "
            f"(model={model_id}, prompt={prompt_version})"
        )

        # Load and validate the condensed input.
        condensed_text = Path(condensed_file).read_text()
        condensed = json.loads(condensed_text)
        missing = [k for k in REQUIRED_KEYS if k not in condensed]
        if missing:
            raise ValueError(f"Condensed JSON missing required keys: {missing}")
        week = condensed["week"]

        # Load versioned prompts.
        system_prompt, task_prompt, prompt_hash = self._load_prompts(prompt_version)

        out_path = self._ensure_output_directory(output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = out_path / f"newsletter_week_{week}_{timestamp}.html"

        if self.dry_run:
            self.logger.info(f"DRY RUN: Would generate newsletter to {output_file}")
            return None, {
                "dry_run": True,
                "html_file": str(output_file),
                "model_id": model_id,
                "prompt_version": prompt_version,
                "week": week,
            }

        if not AWS_AVAILABLE:
            raise RuntimeError("boto3 is required for newsletter generation but is not installed")

        user_context = f"{task_prompt}\n\n--- CONDENSED LEAGUE DATA (JSON) ---\n{condensed_text}"

        client = self._get_bedrock_client(region)

        # Generate each section in its own call, then assemble.
        subject: Optional[str] = None
        fragments: Dict[str, str] = {}
        total_in = total_out = 0
        for key, description in SECTIONS:
            directive = self._section_directive(key, description)
            text, usage, stop_reason = self._invoke(
                client, model_id, system_prompt,
                f"{directive}\n\n{user_context}", cfg.temperature, cfg.max_tokens,
            )
            if stop_reason == "max_tokens":
                raise RuntimeError(
                    f"Section '{key}' hit max_tokens ({cfg.max_tokens}); newsletter would be "
                    f"truncated. Raise pipeline.newsletter.max_tokens or split the section."
                )
            total_in += usage.get("inputTokens", 0)
            total_out += usage.get("outputTokens", 0)
            sec_subject, fragment = self._extract_fragment(text, want_subject=(key == "intro"))
            if sec_subject:
                subject = sec_subject
            fragments[key] = fragment
            self.logger.info(f"Section '{key}' generated ({len(fragment)} chars, stop={stop_reason})")

        html = self._assemble(condensed["league_name"], week, fragments)
        html = self._normalize_html(html)
        output_file.write_text(html)
        self.logger.info(f"Assembled newsletter written to {output_file}")

        # Audit trail.
        year = datetime.now().year
        audit_key = self._write_audit(
            region=region,
            week=week,
            year=year,
            model_id=model_id,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            prompt_version=prompt_version,
            prompt_hash=prompt_hash,
            condensed_text=condensed_text,
            condensed_file=condensed_file,
            output_file=str(output_file),
            subject=subject,
            input_tokens=total_in,
            output_tokens=total_out,
        )

        metadata = {
            "html_file": str(output_file),
            "subject": subject,
            "model_id": model_id,
            "prompt_version": prompt_version,
            "week": week,
            "year": year,
            "input_tokens": total_in,
            "output_tokens": total_out,
            "audit_key": audit_key,
        }
        return str(output_file), metadata

    # --- prompts -----------------------------------------------------------

    def _load_prompts(self, version: str) -> Tuple[str, str, str]:
        """Load system + task prompts for a version and return them with a content hash."""
        prompts_dir = Path(__file__).parent.parent.parent / "prompts" / "newsletter"
        system_prompt = (prompts_dir / f"system_{version}.md").read_text()
        task_prompt = (prompts_dir / f"task_{version}.md").read_text()
        prompt_hash = hashlib.sha256(
            (system_prompt + task_prompt).encode("utf-8")
        ).hexdigest()
        return system_prompt, task_prompt, prompt_hash

    def _section_directive(self, key: str, description: str) -> str:
        """Per-section instruction that scopes one Bedrock call to a single section."""
        directive = (
            f"You are writing the weekly roast newsletter in phases. For THIS response, "
            f"write ONLY {description}. Emit an HTML fragment using inline styles only — "
            f"do NOT include <html>, <head>, or <body> tags, and do NOT write any other "
            f"section. Do not wrap the output in markdown code fences or add any commentary."
        )
        if key == "intro":
            directive += (
                " Begin your response with the email subject line on its own line, prefixed "
                "exactly with 'SUBJECT: '. After that line, output the HTML fragment for the "
                "header, intro, and summary."
            )
        return directive

    # --- bedrock -----------------------------------------------------------

    def _get_bedrock_client(self, region: str):
        """Bedrock runtime client with profile support and an extended read timeout."""
        profile = getattr(self.config.pipeline.aws, "profile", None)
        boto_cfg = BotoConfig(read_timeout=_READ_TIMEOUT_SECONDS, retries={"max_attempts": 2})
        if profile:
            session = boto3.Session(profile_name=profile, region_name=region)
        else:
            session = boto3.Session(region_name=region)
        return session.client("bedrock-runtime", config=boto_cfg)

    def _invoke(
        self, client, model_id: str, system: str, user: str,
        temperature: float, max_tokens: int,
    ) -> Tuple[str, Dict[str, Any], Optional[str]]:
        """Single Converse call; returns (text, usage, stopReason)."""
        resp = client.converse(
            modelId=model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig={"temperature": temperature, "maxTokens": max_tokens},
        )
        text = "".join(
            block.get("text", "") for block in resp["output"]["message"]["content"]
        )
        return text, resp.get("usage", {}), resp.get("stopReason")

    # --- output handling ---------------------------------------------------

    def _extract_fragment(self, text: str, want_subject: bool) -> Tuple[Optional[str], str]:
        """
        Pull an optional 'SUBJECT:' line and a clean HTML fragment from a model response.

        Strips a leading 'SUBJECT: ...' line, markdown code fences, and any prose
        preamble/postamble surrounding the HTML (slices first '<' to last '>').
        """
        subject: Optional[str] = None
        if want_subject:
            m = re.search(r"^\s*SUBJECT:\s*(.+?)\s*$", text, re.MULTILINE)
            if m:
                subject = m.group(1).strip()
                text = text[: m.start()] + text[m.end():]

        # Remove markdown code fences (```html ... ``` or ``` ... ```).
        text = re.sub(r"```[a-zA-Z]*\n?", "", text)

        # Slice to the outermost HTML tags, dropping any prose before/after.
        start = text.find("<")
        end = text.rfind(">")
        fragment = text[start : end + 1].strip() if start != -1 and end != -1 else text.strip()
        return subject, fragment

    def _normalize_html(self, html: str) -> str:
        """
        Enforce design guardrails on the assembled HTML, independent of the model's choices.

        - Replaces garish/novelty font families (Impact, Arial Black, Comic Sans) with the
          approved stack.
        - Softens pure-white text (#fff/#ffffff/white) to off-white to cut glare on dark
          backgrounds — leaves `background-color` and accent colors untouched.
        """
        def _font_repl(match: "re.Match[str]") -> str:
            value = match.group(1)
            if any(token in value.lower() for token in _BANNED_FONT_TOKENS):
                return f"font-family: {APPROVED_FONT_STACK}"
            return match.group(0)

        html = re.sub(r"font-family\s*:\s*([^;\"]*)", _font_repl, html)
        html = re.sub(
            r"(?<![-\w])color\s*:\s*(?:#fff(?:fff)?|white)\b",
            f"color: {_SOFT_WHITE}",
            html,
            flags=re.IGNORECASE,
        )
        return html

    def _assemble(self, league_name: str, week: Any, fragments: Dict[str, str]) -> str:
        """Concatenate section fragments into a single Gmail-pasteable HTML document."""
        body = "\n".join(fragments[key] for key, _ in SECTIONS if key in fragments)
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f"<title>{league_name} — Week {week} Recap</title>\n</head>\n"
            '<body style="margin:0;padding:0;background-color:#1a1a1a;">\n'
            '<div style="max-width:800px;margin:0 auto;">\n'
            f"{body}\n"
            "</div>\n</body>\n</html>\n"
        )

    # --- audit -------------------------------------------------------------

    def _write_audit(
        self, *, region: str, week: Any, year: int, model_id: str, temperature: float,
        max_tokens: int, prompt_version: str, prompt_hash: str, condensed_text: str,
        condensed_file: str, output_file: str, subject: Optional[str],
        input_tokens: int, output_tokens: int,
    ) -> Dict[str, str]:
        """Write a per-edition audit record to the shared DynamoDB table."""
        table_name = self.config.pipeline.aws.dynamodb_table
        profile = getattr(self.config.pipeline.aws, "profile", None)
        if profile:
            session = boto3.Session(profile_name=profile, region_name=region)
            dynamodb = session.resource("dynamodb")
        else:
            dynamodb = boto3.resource("dynamodb", region_name=region)
        table = dynamodb.Table(table_name)

        generated_at = datetime.now().isoformat()
        pk = f"NEWSLETTER#{self.league_id}"
        sk = f"SEASON#{year}#WEEK#{week}#{generated_at}"
        item = {
            "season_week": pk,          # table's partition key attribute
            "data_type_id": sk,         # table's sort key attribute
            "league_id": str(self.league_id),
            "week": week,
            "season": year,
            "model_id": model_id,
            "temperature": Decimal(str(temperature)),
            "max_tokens": max_tokens,
            "prompt_version": prompt_version,
            "prompt_content_hash": prompt_hash,
            "condensed_input_ref": condensed_file,
            "condensed_input_hash": hashlib.sha256(condensed_text.encode("utf-8")).hexdigest(),
            "input_token_count": input_tokens,
            "output_token_count": output_tokens,
            "output_html_ref": output_file,
            "subject": subject or "",
            "generated_at": generated_at,
            "delivery_result": "not_sent",
        }
        table.put_item(Item=item)
        self.logger.info(f"Audit record written: {pk} / {sk}")
        return {"pk": pk, "sk": sk}
