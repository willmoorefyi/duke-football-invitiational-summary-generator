"""
Tests for the "Read the Weekly Roast" banner on the weekly report page.

The banner is hidden-by-default and revealed client-side by a HEAD existence
check, so it self-heals both the brief upload delay and a permanent newsletter
failure. It is only emitted when the newsletter stage is expected to run.
"""

import tempfile
import unittest
from pathlib import Path

from src.generators.templated_html_generator import TemplatedFantasyHTMLGenerator


def _sample_data():
    """Minimal enhanced structure sufficient for generate_html."""
    current_week = {
        'week': 2,
        'season': 2025,
        'league_id': '380491',
        'league_name': 'Test Fantasy League',
        'report_date': '2025-09-18T12:00:00Z',
        'divisions': [
            {
                'name': 'Test Division',
                'teams': [
                    {'id': 'team1', 'name': 'Team A', 'logo': 'http://example.com/a.png',
                     'overall_rank': 1, 'wins': 1, 'losses': 1,
                     'points_for': 216.3, 'points_against': 207.5},
                    {'id': 'team2', 'name': 'Team B', 'logo': 'http://example.com/b.png',
                     'overall_rank': 2, 'wins': 1, 'losses': 1,
                     'points_for': 207.5, 'points_against': 216.3},
                ],
            }
        ],
        'matchups': [
            {
                'home_team': {'id': 'team1', 'name': 'Team A'},
                'away_team': {'id': 'team2', 'name': 'Team B'},
                'home_score': 105.8, 'away_score': 112.3,
                'home_projected_score': 108.0, 'away_projected_score': 103.0,
                'home_optimal_score': 120.0, 'away_optimal_score': 115.0,
                'players': [],
            }
        ],
        'awards': {},
    }
    return {'current_week': current_week, 'season_context': {}}


class TestNewsletterBanner(unittest.TestCase):
    def setUp(self):
        self.generator = TemplatedFantasyHTMLGenerator()
        self.data = _sample_data()

    def _render(self, show_banner):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.html"
            self.generator.generate_html(self.data, str(out), show_newsletter_banner=show_banner)
            return out.read_text()

    def test_template_vars_expose_newsletter_url(self):
        tv = self.generator._prepare_template_variables(self.data, show_newsletter_banner=True)
        assert tv['show_newsletter_banner'] is True
        assert tv['newsletter_url'].endswith(
            "duke-football-invitational/weekly-reports/newsletters/newsletter_2025_week_2.html"
        )

    def test_banner_hidden_by_default_with_fetch_guard(self):
        """Part H item 3: banner present but hidden, with the HEAD existence guard."""
        html = self._render(show_banner=True)
        assert 'id="newsletter-banner"' in html
        assert 'display:none' in html
        # Client-side existence check (HEAD) that self-heals delay / permanent failure.
        assert 'fetch(url, { method: "HEAD" })' in html
        # Links to the exact newsletter object it will reveal.
        assert 'newsletter_2025_week_2.html' in html

    def test_banner_present_when_enabled(self):
        assert 'id="newsletter-banner"' in self._render(show_banner=True)

    def test_banner_absent_when_disabled(self):
        """Part H item 7: --no-newsletter omits the banner markup entirely."""
        html = self._render(show_banner=False)
        assert 'id="newsletter-banner"' not in html
        assert 'Read the Weekly Roast' not in html


if __name__ == '__main__':
    unittest.main()
