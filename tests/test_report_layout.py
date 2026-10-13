"""Tests for season-scoped themes and the 2026 compact weekly report layout."""

import re

import pytest

from src.generators.templated_html_generator import (
    LEGACY_THEME,
    REDESIGN_2026_THEME,
    TemplatedFantasyHTMLGenerator,
    theme_for_season,
)


def _redesign_env(generator):
    return generator._env_for(REDESIGN_2026_THEME)


def _player(name, score, is_starter, should_have_started, is_mvp=False, slot='RB'):
    return {
        'name': name,
        'actual_score': score,
        'is_starter': is_starter,
        'should_have_started': should_have_started,
        'is_mvp': is_mvp,
        'roster_slot': slot,
        'injury_status': 'HEALTHY',
    }


class TestBoxScoreTable:
    def setup_method(self):
        self.generator = TemplatedFantasyHTMLGenerator()
        self.template = _redesign_env(self.generator).get_template('team_player_table.html')

    def _render(self, players):
        return self.template.render(
            team_players=players,
            starter_total=sum(p['actual_score'] for p in players if p['is_starter']),
            team_bg_color='rgb(0, 0, 0)',
            team_font_color='#fff',
            optimal_score=100.0,
            accuracy_percentage=80.0,
            get_background_css=self.generator._get_background_css,
        )

    def test_only_optimal_bench_players_shown_rest_collapsed(self):
        players = [
            _player('Starter Good', 20.0, True, True, is_mvp=True),
            _player('Starter Bad', 2.0, True, False),
            _player('Bench Should Start', 15.0, False, True),
            _player('Bench Fine A', 1.0, False, False),
            _player('Bench Fine B', 0.0, False, False),
        ]
        html = self._render(players)

        main_table, _, bench = html.partition('<details class="bench-details">')
        assert 'Bench Should Start' in main_table
        assert 'Bench Fine A' not in main_table
        assert 'Rest of bench (2)' in bench
        assert 'Bench Fine A' in bench and 'Bench Fine B' in bench
        # 1 of 2 starters was in the optimal lineup
        assert '1/2' in html
        assert 'width: 50.0%' in html

    def test_perfect_lineup_message_and_no_bench_toggle_when_empty(self):
        players = [
            _player('Starter A', 20.0, True, True),
            _player('Starter B', 10.0, True, True),
        ]
        html = self._render(players)

        assert 'Perfect lineup' in html
        assert 'bench-details' not in html
        assert '2/2' in html

    def test_full_width_rows_keep_a_leading_cell_for_mobile(self):
        # Mobile CSS hides the first column of matchup tables; full-width rows
        # must not put their content in that first cell.
        html = self._render([_player('Starter A', 20.0, True, True)])
        for row_class in ('box-score-total', 'box-score-band', 'box-score-optimal', 'perfect-lineup-row'):
            row = re.search(rf'<tr class="{row_class}"[^>]*>\s*(<td[^>]*>)', html)
            assert row, row_class
            assert row.group(1) == '<td>', row_class


class TestTeamCell:
    def test_team_cell_renders_swatch_icon_and_name(self):
        generator = TemplatedFantasyHTMLGenerator()
        template = _redesign_env(generator).from_string(
            "{% from 'team_cell.html' import team_cell with context %}{{ team_cell(name, logo) }}"
        )
        html = template.render(
            name='Team Team',
            logo='https://example.com/logo.png',
            get_team_theme_colors=lambda _name: ['rgb(1, 2, 3)', '#fff'],
            get_background_css=generator._get_background_css,
        )
        assert 'class="team-cell"' in html
        assert 'background-color: rgb(1, 2, 3)' in html
        assert 'src="https://example.com/logo.png"' in html
        assert '<span class="team-cell-name">Team Team</span>' in html

    def test_team_cell_omits_icon_without_logo(self):
        generator = TemplatedFantasyHTMLGenerator()
        template = _redesign_env(generator).from_string(
            "{% from 'team_cell.html' import team_cell with context %}{{ team_cell('No Logo') }}"
        )
        html = template.render(
            get_team_theme_colors=lambda _name: ['rgb(1, 2, 3)', '#fff'],
            get_background_css=generator._get_background_css,
        )
        assert 'team-icon' not in html
        assert 'No Logo' in html


class TestMainLayout:
    def test_week_sections_open_before_collapsed_season_stats(self):
        generator = TemplatedFantasyHTMLGenerator()
        env = _redesign_env(generator)
        loader = env.loader
        assert loader is not None
        source = loader.get_source(env, 'main.html')[0]

        order = [source.index(f'id="{sid}"') for sid in
                 ('week-results', 'weekly-awards', 'box-scores', 'season-stats')]
        assert order == sorted(order)

        for sid in ('week-results', 'weekly-awards', 'box-scores'):
            assert re.search(rf'id="{sid}" open>', source), sid
        assert re.search(r'id="season-stats">', source)


class TestSeasonThemes:
    @pytest.mark.parametrize('season, page, expected', [
        (2024, 'weekly', LEGACY_THEME),
        (2025, 'weekly', LEGACY_THEME),
        (2025, 'overview', LEGACY_THEME),
        (2026, 'weekly', REDESIGN_2026_THEME),
        (2027, 'weekly', REDESIGN_2026_THEME),
        ('2026', 'weekly', REDESIGN_2026_THEME),
        (2026, 'overview', None),
    ])
    def test_theme_for_season(self, season, page, expected):
        assert theme_for_season(season, page) == expected

    @staticmethod
    def _source_path(env, name):
        loader = env.loader
        assert loader is not None
        return loader.get_source(env, name)[1]

    def test_redesign_overrides_weekly_templates_only(self):
        generator = TemplatedFantasyHTMLGenerator()
        env = _redesign_env(generator)
        assert '/themes/2026/' in self._source_path(env, 'main.html')
        assert '/themes/2026/' in self._source_path(env, 'team_player_table.html')
        # Shared partials it doesn't override still come from the base templates
        assert '/themes/' not in self._source_path(env, 'header.html')
        assert '/themes/' not in self._source_path(env, 'styles.css')

    def test_base_templates_untouched_by_redesign(self):
        generator = TemplatedFantasyHTMLGenerator()
        loader = generator.env.loader
        assert loader is not None
        assert 'report-section' not in loader.get_source(generator.env, 'main.html')[0]
        with pytest.raises(Exception):
            generator.env.get_template('team_cell.html')

    def test_legacy_theme_freezes_stylesheets_only(self):
        generator = TemplatedFantasyHTMLGenerator()
        env = generator._env_for(LEGACY_THEME)
        assert '/themes/legacy/' in self._source_path(env, 'styles.css')
        assert '/themes/legacy/' in self._source_path(env, 'playoff_styles.css')
        assert '/themes/' not in self._source_path(env, 'main.html')
        # Frozen pre-2026-refresh stylesheet has no design tokens
        loader = env.loader
        assert loader is not None
        assert '--surface:' not in loader.get_source(env, 'styles.css')[0]


def _matchup(home, home_score, home_opt, away, away_score, away_opt):
    return {
        'home_team': {'name': home}, 'home_score': home_score, 'home_optimal_score': home_opt,
        'away_team': {'name': away}, 'away_score': away_score, 'away_optimal_score': away_opt,
    }


class TestWouldHaveWon:
    def test_lists_losers_whose_optimal_beats_opponent_sorted_by_bench_points(self):
        generator = TemplatedFantasyHTMLGenerator()
        rows = generator._prepare_would_have_won([
            _matchup('A', 100.0, 110.0, 'B', 90.0, 120.0),    # B lost 90-100, optimal 120 -> yes (+30)
            _matchup('C', 80.0, 140.0, 'D', 95.0, 96.0),      # C lost 80-95, optimal 140 -> yes (+60)
            _matchup('E', 70.0, 99.0, 'F', 100.0, 100.0),     # E optimal 99 < 100 -> no
            _matchup('G', 100.0, 100.0, 'H', 100.0, 150.0),   # tie -> no
        ])
        assert [r['team_name'] for r in rows] == ['C', 'B']
        assert rows[1] == {'team_name': 'B', 'optimal': 120.0, 'actual': 90.0,
                           'opp_score': 100.0, 'opponent_name': 'A'}


class TestScoreTrendChart:
    WEEKS = [
        {'week': 1, 'max': 150.0, 'median': 120.0, 'min': 90.0, 'max_team_name': 'A', 'min_team_name': 'B'},
        {'week': 2, 'max': 160.0, 'median': 110.0, 'min': 70.0, 'max_team_name': 'C', 'min_team_name': 'D'},
        {'week': 3, 'max': 140.0, 'median': 115.0, 'min': 95.0, 'max_team_name': 'E', 'min_team_name': 'F'},
    ]

    def test_geometry_axes_and_current_week(self):
        chart = TemplatedFantasyHTMLGenerator()._prepare_score_trend_chart(self.WEEKS, 3)
        assert chart is not None
        assert [t['value'] for t in chart['y_ticks']] == [60, 80, 100, 120, 140, 160]
        assert [s['key'] for s in chart['series']] == ['max', 'median', 'min']
        top, bottom = chart['plot']['top'], chart['plot']['bottom']
        max_pts = chart['series'][0]['points']
        assert max_pts[1]['y'] == top                     # 160 = top of domain
        assert all(top <= p['y'] <= bottom for s in chart['series'] for p in s['points'])
        assert chart['series'][0]['path'].startswith('M') and chart['series'][0]['path'].count('L') == 2
        assert chart['current'] == {'week': 3, 'max': 140.0, 'median': 115.0, 'min': 95.0}
        assert [t['current'] for t in chart['x_ticks']] == [False, False, True]
        assert chart['hit_areas'][1]['max_team'] == 'C'

    def test_end_labels_never_overlap(self):
        close = [{'week': 1, 'max': 101.0, 'median': 100.5, 'min': 100.0}]
        chart = TemplatedFantasyHTMLGenerator()._prepare_score_trend_chart(close, 1)
        assert chart is not None
        ys = sorted(s['label_y'] for s in chart['series'])
        assert all(b - a >= 20 for a, b in zip(ys, ys[1:]))

    def test_no_chart_without_scored_weeks(self):
        generator = TemplatedFantasyHTMLGenerator()
        assert generator._prepare_score_trend_chart([], 1) is None
        assert generator._prepare_score_trend_chart(
            [{'week': 1, 'max': 0.0, 'median': 0.0, 'min': 0.0}], 1) is None
