"""
Newsletter Stage

Stage 6: Roast Newsletter Generation
Generates the humorous weekly HTML email from the condensed JSON via Amazon Bedrock.
Grounded entirely in the supplied condensed data; writes an audit record per edition.

Generation is multi-call: one Bedrock Converse call per section (overview, matchups,
awards, standings & divisional analysis, final recap), then the fragments are assembled
into one HTML email. Each section receives ONLY its own tailored data slice (see
_section_payload) rather than the whole condensed blob, so sections don't overlap and
the standings section gets the season-anchored computed insights. This honors the
prompt's "write in phases" instruction and avoids the single-call max_tokens truncation
observed in the Step-0 spike.
"""

import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import PipelineStage
from ..utils.s3_deploy import upload_html_string, invalidate_cloudfront_cache
from ..utils.urls import (
    newsletter_public_url,
    newsletter_s3_key,
    survivor_public_url,
    weekly_report_public_url,
)

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
REQUIRED_KEYS = ("league_name", "week", "season", "team_standings", "matchups", "awards")

# (key, human description) for each section-scoped Bedrock call. This list is the single
# source of truth for BOTH the generation order and the assembly order (_assemble
# iterates it). The code key `intro` is retained for the Overview section.
SECTIONS: List[Tuple[str, str]] = [
    ("intro", "Section 1 — Overview (the email subject line, header, and a brief intro ONLY — NOT the standings/divisional analysis)"),
    ("matchups", "Section 2 (the matchup summaries)"),
    ("awards", "Section 3 (the awards)"),
    ("standings", "Section 4 (the standings & divisional analysis)"),
    ("recap", "Section 5 (the final recap)"),
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
        Generate the roast newsletter from a condensed JSON file, then deploy + audit it.

        Composes the reusable building blocks: ``_generate`` (Bedrock loop + assemble +
        write local file), ``_upload`` (S3 deploy + CloudFront invalidation), and
        ``_write_audit`` (per-edition DynamoDB row). This is the full pipeline path used
        by ``pipeline run`` and the ``newsletter`` command.

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
        condensed, condensed_text = self._load_condensed(condensed_file)
        week = condensed["week"]
        # Season is the single source of truth for both the newsletter and weekly-report
        # S3 keys (see src/utils/urls.py); it comes from the condensed JSON, not the clock,
        # so re-generating a past season lands under the correct year.
        season = condensed["season"]

        if self.dry_run:
            out_path = self._ensure_output_directory(output_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = out_path / f"newsletter_week_{week}_{timestamp}.html"
            self.logger.info(f"DRY RUN: Would generate newsletter to {output_file}")
            return None, {
                "dry_run": True,
                "html_file": str(output_file),
                "model_id": model_id,
                "prompt_version": prompt_version,
                "week": week,
                "season": season,
            }

        # GENERATION — Bedrock per-section loop, assemble, normalize, write local file.
        gen = self._generate(condensed, prompt_version, output_dir)

        # DEPLOY — S3 upload + CloudFront invalidation (non-blocking on failure).
        upload = self._upload(gen["html"], season, week)
        # On a failed upload we still audit, pointing at the local copy instead of the URL.
        output_html_ref = (
            upload["public_url"] if upload["delivery_result"] == "deployed"
            else str(gen["output_file"])
        )

        # Audit trail.
        audit_key = self._write_audit(
            region=region,
            week=week,
            season=season,
            model_id=model_id,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            prompt_version=prompt_version,
            prompt_hash=gen["prompt_hash"],
            condensed_text=condensed_text,
            condensed_file=condensed_file,
            output_html_ref=output_html_ref,
            local_html_ref=str(gen["output_file"]),
            delivery_result=upload["delivery_result"],
            subject=gen["subject"],
            input_tokens=gen["input_tokens"],
            output_tokens=gen["output_tokens"],
            sections=[key for key, _ in SECTIONS],
        )

        metadata = {
            "html_file": str(gen["output_file"]),
            "subject": gen["subject"],
            "model_id": model_id,
            "prompt_version": prompt_version,
            "week": week,
            "season": season,
            "newsletter_url": upload["public_url"],
            "delivery_result": upload["delivery_result"],
            "input_tokens": gen["input_tokens"],
            "output_tokens": gen["output_tokens"],
            "audit_key": audit_key,
        }
        return str(gen["output_file"]), metadata

    # --- composable steps --------------------------------------------------

    def _load_condensed(self, condensed_file: str) -> Tuple[Dict[str, Any], str]:
        """Read and validate the condensed JSON. Returns (parsed_dict, raw_text)."""
        condensed_text = Path(condensed_file).read_text()
        condensed = json.loads(condensed_text)
        missing = [k for k in REQUIRED_KEYS if k not in condensed]
        if missing:
            raise ValueError(f"Condensed JSON missing required keys: {missing}")
        return condensed, condensed_text

    def _generate(
        self, condensed: Dict[str, Any], prompt_version: str, output_dir: str,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the Bedrock per-section generation loop and write the local HTML file.

        This is the LOCAL-ONLY generation half of the stage (no S3, no audit), so both
        ``execute`` and the ``newsletter-regenerate`` review command can share it. Each
        section gets the full task spec (award definitions, etc.) plus ONLY that
        section's data slice, then the fragments are assembled + normalized.

        Args:
            condensed: Parsed condensed JSON.
            prompt_version: Prompt version to use.
            output_dir: Output directory for the HTML email.
            model_id: Optional Bedrock model id / inference-profile id override for THIS
                run only. When None, falls back to config's ``bedrock_model_id``. This
                does not mutate or persist config.

        Returns a dict with the assembled ``html``, ``subject``, token counts, resolved
        ``week``/``season``, the written ``output_file`` path, and the ``prompt_hash``
        (needed by the audit trail).
        """
        if not AWS_AVAILABLE:
            raise RuntimeError("boto3 is required for newsletter generation but is not installed")

        cfg = self.config.pipeline.newsletter
        # Per-run model override (e.g. `newsletter-regenerate --model`) takes precedence
        # over the configured default without persisting any config change.
        model_id = model_id or cfg.bedrock_model_id
        region = cfg.region or self.config.pipeline.aws.region
        week = condensed["week"]
        season = condensed["season"]

        # Load versioned prompts.
        system_prompt, task_prompt, prompt_hash = self._load_prompts(prompt_version)

        out_path = self._ensure_output_directory(output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = out_path / f"newsletter_week_{week}_{timestamp}.html"

        client = self._get_bedrock_client(region)

        # Generate each section in its own call, then assemble. Each call gets the full
        # task spec (award definitions, etc.) plus ONLY that section's data slice.
        subject: Optional[str] = None
        fragments: Dict[str, str] = {}
        total_in = total_out = 0
        for key, description in SECTIONS:
            directive = self._section_directive(key, description, week, season)
            payload_json = json.dumps(self._section_payload(key, condensed), default=str)
            user = f"{directive}\n\n{task_prompt}\n\n--- DATA (JSON) ---\n{payload_json}"
            text, usage, stop_reason = self._invoke(
                client, model_id, system_prompt, user, cfg.temperature, cfg.max_tokens,
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

        html = self._assemble(condensed["league_name"], week, season, fragments)
        html = self._normalize_html(html)
        output_file.write_text(html)
        self.logger.info(f"Assembled newsletter written to {output_file}")

        return {
            "html": html,
            "subject": subject,
            "input_tokens": total_in,
            "output_tokens": total_out,
            "week": week,
            "season": season,
            "output_file": output_file,
            "prompt_hash": prompt_hash,
        }

    def _upload(self, html: str, season: Any, week: Any) -> Dict[str, Any]:
        """
        Deploy the assembled HTML to S3 and invalidate CloudFront for its key.

        Reusable by both ``execute`` (full pipeline) and the ``newsletter-upload``
        review command. Non-blocking: if the upload fails we log it and report
        ``delivery_result`` 'not_sent' so callers can still write the audit row and
        keep this optional stage from crashing.

        Returns {delivery_result, public_url, s3_key}.
        """
        region = self.config.pipeline.newsletter.region or self.config.pipeline.aws.region
        bucket = self.config.pipeline.aws.s3_bucket
        s3_key = newsletter_s3_key(season, week)
        public_url = newsletter_public_url(season, week, bucket)
        delivery_result = "not_sent"
        try:
            session = self._boto3_session(region)
            s3_client = session.client("s3")
            upload_html_string(s3_client, bucket, s3_key, html, self.logger)
            # Upload succeeded — record it as deployed before attempting the best-effort
            # invalidation below.
            delivery_result = "deployed"
            self.logger.info(f"Newsletter deployed to {public_url}")
            try:
                dist_id = self.config.pipeline.aws.cloudfront_distribution_id
                cloudfront_client = session.client("cloudfront")
                invalidate_cloudfront_cache(cloudfront_client, dist_id, [s3_key], self.logger)
            except Exception as e:
                # A failed invalidation doesn't undo a successful upload; leave it deployed.
                self.logger.warning(f"Newsletter CloudFront invalidation failed: {e}")
        except Exception as e:
            self.logger.error(f"Newsletter S3 upload failed (non-blocking): {e}")
        return {
            "delivery_result": delivery_result,
            "public_url": public_url,
            "s3_key": s3_key,
        }

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

    def _section_directive(self, key: str, description: str, week: Any, season: Any) -> str:
        """Per-section instruction that scopes one Bedrock call to a single section.

        The week/season are grounded in EVERY directive so the model never guesses or
        copies a week number from the prompt's example (the bug this fixes: a Week 3
        newsletter emitting a "WEEK 1 MATCHUP" heading lifted from the example intro).
        """
        directive = (
            f"This newsletter is for Week {week} of the {season} season. Refer to the "
            f"current week as Week {week} everywhere; do not invent or copy a different "
            f"week number. "
            f"You are writing the weekly roast newsletter in phases. For THIS response, "
            f"write ONLY {description}. Emit an HTML fragment using inline styles only — "
            f"do NOT include <html>, <head>, or <body> tags, and do NOT write any other "
            f"section. Do not wrap the output in markdown code fences or add any commentary."
        )
        if key == "intro":
            directive += (
                " Begin your response with the email subject line on its own line, prefixed "
                "exactly with 'SUBJECT: '. After that line, output the HTML fragment for the "
                "header and brief intro."
            )
        return directive

    # --- per-section data slicing -----------------------------------------

    def _section_payload(self, key: str, condensed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return ONLY the data slice a given section needs.

        Each section gets a tailored subset of the condensed JSON so sections don't
        all receive the same blob (the overlap this refactor fixes). Every lookup uses
        ``.get()`` and omits missing keys, so older condensed files that lack the newer
        fields (draft_board, standings_insights, team_week_by_week) degrade gracefully
        without raising KeyError.
        """
        def pick(*keys: str) -> Dict[str, Any]:
            return {k: condensed[k] for k in keys if k in condensed}

        if key == "intro":
            # Overview: enough to set the scene, not the full standings analysis.
            payload = pick("league_name", "week", "season")
            standings = condensed.get("team_standings")
            if standings:
                payload["standings_framing"] = {"division_leaders": self._division_leaders(standings)}
            return payload

        if key == "matchups":
            # Current-week matchups (with players), plus week/season so the section
            # anchors its heading to the right week instead of guessing (belt-and-
            # suspenders alongside the week grounded in _section_directive).
            return pick("matchups", "week", "season")

        if key == "awards":
            # Awards plus the referenced players (flattened from the matchups) so the
            # section can cite exact stat lines without the full matchup structure.
            payload = pick("awards")
            players = self._flatten_players(condensed.get("matchups", []))
            if players:
                payload["players"] = players
            return payload

        if key == "standings":
            # Season-anchored standings section: standings, position strength, the
            # computed insights, and per-team week-by-week — but NOT current-week matchups.
            return pick(
                "team_standings", "position_strength",
                "standings_insights", "team_week_by_week",
            )

        if key == "recap":
            # Closes the week: standings, award highlights, and a MINIMAL current-week
            # results slice (winners + final scores), not the full matchup detail.
            payload = pick("team_standings", "awards")
            results = self._minimal_week_results(condensed.get("matchups", []))
            if results:
                payload["week_results"] = results
            return payload

        # Unknown section: send nothing rather than the whole blob.
        return {}

    @staticmethod
    def _division_leaders(team_standings: List[Dict[str, Any]]) -> Dict[str, str]:
        """Map each division to its current leader (lowest overall_rank)."""
        leaders: Dict[str, Dict[str, Any]] = {}
        for team in team_standings:
            div = team.get("division", "Unknown")
            name = team.get("name") or team.get("team_name", "Unknown")
            rank = team.get("overall_rank", 999)
            cur = leaders.get(div)
            if cur is None or rank < cur["rank"]:
                leaders[div] = {"name": name, "rank": rank}
        return {div: info["name"] for div, info in leaders.items()}

    @staticmethod
    def _flatten_players(matchups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flatten a compact per-player list (name/team/position/scores/injury) from matchups."""
        players: List[Dict[str, Any]] = []
        for matchup in matchups:
            for side in ("home_team", "away_team"):
                team = matchup.get(side, {})
                if not isinstance(team, dict):
                    continue  # degraded/old shape (e.g. a bare team name) — skip
                team_name = team.get("name", "")
                for p in team.get("players", []):
                    players.append({
                        "name": p.get("name"),
                        "team": team_name,
                        "position": p.get("position"),
                        "roster_slot": p.get("roster_slot"),
                        "projected_score": p.get("projected_score"),
                        "actual_score": p.get("actual_score"),
                        "injury_status": p.get("injury_status"),
                    })
        return players

    @staticmethod
    def _minimal_week_results(matchups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Winners + final scores for each matchup (no player-level detail)."""
        results: List[Dict[str, Any]] = []
        for matchup in matchups:
            home = matchup.get("home_team", {})
            away = matchup.get("away_team", {})
            if not isinstance(home, dict) or not isinstance(away, dict):
                continue  # degraded/old shape — skip rather than crash
            results.append({
                "home_team": home.get("name"),
                "home_score": home.get("points_scored"),
                "away_team": away.get("name"),
                "away_score": away.get("points_scored"),
                "winning_team": matchup.get("winning_team"),
            })
        return results

    # --- bedrock -----------------------------------------------------------

    def _boto3_session(self, region: str):
        """Profile-aware boto3 session (mirrors deploy_stage's session handling)."""
        profile = getattr(self.config.pipeline.aws, "profile", None)
        if profile:
            return boto3.Session(profile_name=profile, region_name=region)
        return boto3.Session(region_name=region)

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

    def _assemble(self, league_name: str, week: Any, season: Any, fragments: Dict[str, str]) -> str:
        """Concatenate section fragments into a single Gmail-pasteable HTML document."""
        preamble = self._preamble(season, week)
        body = "\n".join(fragments[key] for key, _ in SECTIONS if key in fragments)
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f"<title>{league_name} — Week {week} Recap</title>\n</head>\n"
            '<body style="margin:0;padding:0;background-color:#1a1a1a;">\n'
            '<div style="max-width:800px;margin:0 auto;">\n'
            f"{preamble}\n"
            f"{body}\n"
            "</div>\n</body>\n</html>\n"
        )

    def _preamble(self, season: Any, week: Any) -> str:
        """
        Static (non-AI) link block placed above the generated sections.

        Uses Gmail-safe inline styles only (no <style> blocks / external CSS) and
        neutral wording — links to the full weekly report and the Survivor pool.
        """
        report_url = weekly_report_public_url(season, week, self.config.pipeline.aws.s3_bucket)
        survivor_url = survivor_public_url(self.config.pipeline.aws.s3_bucket)
        link_style = "color:#e8e8e8;text-decoration:underline;"
        line_style = "margin:0 0 6px;font-family:" + APPROVED_FONT_STACK + ";color:#e8e8e8;font-size:14px;"
        return (
            '<div style="padding:12px 20px;border-bottom:1px solid #333;">\n'
            f'<p style="{line_style}">Weekly Rundown: '
            f'<a href="{report_url}" style="{link_style}">Week {week} report</a></p>\n'
            f'<p style="{line_style}">Survivor Pool Results: '
            f'<a href="{survivor_url}" style="{link_style}">standings and eliminations</a></p>\n'
            "</div>"
        )

    # --- audit -------------------------------------------------------------

    def _write_audit(
        self, *, region: str, week: Any, season: Any, model_id: str, temperature: float,
        max_tokens: int, prompt_version: str, prompt_hash: str, condensed_text: str,
        condensed_file: str, output_html_ref: str, local_html_ref: str,
        delivery_result: str, subject: Optional[str],
        input_tokens: int, output_tokens: int, sections: List[str],
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
        sk = f"SEASON#{season}#WEEK#{week}#{generated_at}"
        item = {
            "season_week": pk,          # table's partition key attribute
            "data_type_id": sk,         # table's sort key attribute
            "league_id": str(self.league_id),
            "week": week,
            "season": season,
            "model_id": model_id,
            "temperature": Decimal(str(temperature)),
            "max_tokens": max_tokens,
            "prompt_version": prompt_version,
            "prompt_content_hash": prompt_hash,
            "condensed_input_ref": condensed_file,
            "condensed_input_hash": hashlib.sha256(condensed_text.encode("utf-8")).hexdigest(),
            "input_token_count": input_tokens,
            "output_token_count": output_tokens,
            "output_html_ref": output_html_ref,   # public URL when deployed, else local path
            "local_html_ref": local_html_ref,     # always the local copy for reference
            "subject": subject or "",
            "generated_at": generated_at,
            "delivery_result": delivery_result,
            "sections": sections,  # ordered section keys actually generated
        }
        table.put_item(Item=item)
        self.logger.info(f"Audit record written: {pk} / {sk}")
        return {"pk": pk, "sk": sk}
