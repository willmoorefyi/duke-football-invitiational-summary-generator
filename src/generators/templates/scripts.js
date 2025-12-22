// Client-side scripts for fantasy football reports
// Note: Logo fallback behavior has been removed - all teams now have hard-coded logos

document.addEventListener('DOMContentLoaded', function() {
    console.log('Fantasy football report loaded');

    // Initialize sortable tables
    initializeSortableTables();

    // Initialize team lightbox functionality
    initializeTeamLightbox();
});

/**
 * Initialize sortable functionality for all tables with sortable headers
 */
function initializeSortableTables() {
    // Find all tables with the sortable class or that should be sortable by default
    const tables = document.querySelectorAll('.standings-table');

    tables.forEach(table => {
        // Skip tables that have been marked as non-sortable
        if (table.hasAttribute('data-no-sort')) {
            return;
        }

        const headerCells = table.querySelectorAll('thead th');
        if (headerCells.length === 0) {
            return; // No headers to make sortable
        }

        // Add sortable class and click handlers to header cells
        headerCells.forEach((th, index) => {
            // Skip headers marked as non-sortable
            if (th.hasAttribute('data-no-sort')) {
                return;
            }

            th.classList.add('sortable');
            th.setAttribute('data-sort-column', index);
            th.setAttribute('data-sort-direction', 'none');
            th.style.cursor = 'pointer';
            th.setAttribute('title', 'Click to sort by ' + th.textContent.trim());

            // Add sort indicator
            const indicator = document.createElement('span');
            indicator.className = 'sort-indicator';
            indicator.innerHTML = ' ⇅';
            th.appendChild(indicator);

            // Add click handler
            th.addEventListener('click', () => {
                sortTable(table, index, th);
            });
        });
    });
}

/**
 * Sort table by the specified column
 * @param {HTMLTableElement} table - The table to sort
 * @param {number} columnIndex - Index of the column to sort by
 * @param {HTMLElement} headerCell - The header cell that was clicked
 */
function sortTable(table, columnIndex, headerCell) {
    const tbody = table.querySelector('tbody');
    if (!tbody) {
        return;
    }

    // Get current sort direction and determine new direction
    let currentDirection = headerCell.getAttribute('data-sort-direction');
    let newDirection;

    if (currentDirection === 'none' || currentDirection === 'desc') {
        newDirection = 'asc';
    } else {
        newDirection = 'desc';
    }

    // Clear all other sort indicators in this table
    const allHeaders = table.querySelectorAll('thead th');
    allHeaders.forEach(th => {
        const indicator = th.querySelector('.sort-indicator');
        if (indicator) {
            indicator.innerHTML = ' ⇅';
        }
        th.setAttribute('data-sort-direction', 'none');
    });

    // Update current header
    headerCell.setAttribute('data-sort-direction', newDirection);
    const indicator = headerCell.querySelector('.sort-indicator');
    if (indicator) {
        indicator.innerHTML = newDirection === 'asc' ? ' ↑' : ' ↓';
    }

    // Check if this table has grouped rows (like division + team logo rows)
    const hasGroupedRows = tbody.querySelector('[data-group-id]') !== null;

    if (hasGroupedRows) {
        // Handle tables with grouped rows
        sortTableWithGroups(tbody, columnIndex, newDirection);
    } else {
        // Handle regular tables
        sortTableRegular(tbody, columnIndex, newDirection);
    }
}

/**
 * Sort table with grouped rows (keeps related rows together)
 * @param {HTMLElement} tbody - The table body element
 * @param {number} columnIndex - Index of the column to sort by
 * @param {string} direction - Sort direction ('asc' or 'desc')
 */
function sortTableWithGroups(tbody, columnIndex, direction) {
    // Collect row groups
    const groups = new Map();
    const allRows = Array.from(tbody.querySelectorAll('tr'));

    // Group rows by their data-group-id
    allRows.forEach(row => {
        const groupId = row.getAttribute('data-group-id');
        if (groupId) {
            if (!groups.has(groupId)) {
                groups.set(groupId, []);
            }
            groups.get(groupId).push(row);
        }
    });

    // Convert groups to array and sort by the main row in each group
    const groupArray = Array.from(groups.values()).map(groupRows => {
        // Find the main row (not a child row)
        const mainRow = groupRows.find(row => !row.hasAttribute('data-group-child')) || groupRows[0];
        return {
            mainRow: mainRow,
            allRows: groupRows,
            sortValue: getCellSortValue(mainRow.cells[columnIndex])
        };
    });

    // Sort groups by their main row's value
    groupArray.sort((groupA, groupB) => {
        let valueA = groupA.sortValue;
        let valueB = groupB.sortValue;

        // Handle numeric vs string comparison
        const isNumeric = !isNaN(valueA) && !isNaN(valueB);

        if (isNumeric) {
            valueA = parseFloat(valueA);
            valueB = parseFloat(valueB);
        } else {
            valueA = valueA.toString().toLowerCase();
            valueB = valueB.toString().toLowerCase();
        }

        let comparison = 0;
        if (valueA > valueB) {
            comparison = 1;
        } else if (valueA < valueB) {
            comparison = -1;
        }

        return direction === 'asc' ? comparison : -comparison;
    });

    // Re-insert groups in sorted order
    groupArray.forEach(group => {
        group.allRows.forEach(row => {
            tbody.appendChild(row);
        });
    });
}

/**
 * Sort regular table (original sorting logic)
 * @param {HTMLElement} tbody - The table body element
 * @param {number} columnIndex - Index of the column to sort by
 * @param {string} direction - Sort direction ('asc' or 'desc')
 */
function sortTableRegular(tbody, columnIndex, direction) {
    // Get all rows (excluding any special rows like median markers)
    const rows = Array.from(tbody.querySelectorAll('tr')).filter(row => {
        // Skip rows that span multiple columns (like median markers)
        const firstCell = row.querySelector('td');
        return firstCell && !firstCell.hasAttribute('colspan');
    });

    // Sort the rows
    rows.sort((rowA, rowB) => {
        const cellA = rowA.cells[columnIndex];
        const cellB = rowB.cells[columnIndex];

        if (!cellA || !cellB) {
            return 0;
        }

        let valueA = getCellSortValue(cellA);
        let valueB = getCellSortValue(cellB);

        // Handle numeric vs string comparison
        const isNumeric = !isNaN(valueA) && !isNaN(valueB);

        if (isNumeric) {
            valueA = parseFloat(valueA);
            valueB = parseFloat(valueB);
        } else {
            valueA = valueA.toString().toLowerCase();
            valueB = valueB.toString().toLowerCase();
        }

        let comparison = 0;
        if (valueA > valueB) {
            comparison = 1;
        } else if (valueA < valueB) {
            comparison = -1;
        }

        return direction === 'asc' ? comparison : -comparison;
    });

    // Re-insert sorted rows
    rows.forEach(row => {
        tbody.appendChild(row);
    });
}

/**
 * Extract sortable value from a table cell
 * @param {HTMLTableCellElement} cell - The table cell
 * @returns {string|number} - The value to sort by
 */
function getCellSortValue(cell) {
    // Check if the cell has a data-sort-value attribute
    if (cell.hasAttribute('data-sort-value')) {
        return cell.getAttribute('data-sort-value');
    }

    // For team cells with background images, extract just the text
    if (cell.classList.contains('team-name-with-bg') || cell.classList.contains('team-name')) {
        return cell.textContent.trim();
    }

    // For numeric cells, extract just the number
    if (cell.classList.contains('numeric')) {
        const text = cell.textContent.trim();
        // Handle formatted numbers like "123.45" or percentages like "85%"
        const numMatch = text.match(/[\d.-]+/);
        return numMatch ? parseFloat(numMatch[0]) : text;
    }

    // Default: return text content
    return cell.textContent.trim();
}

/**
 * Initialize team lightbox functionality
 */
function initializeTeamLightbox() {
    // Get team lightbox data from template (will be injected by Jinja2)
    if (typeof teamLightboxData === 'undefined') {
        console.warn('Team lightbox data not available');
        return;
    }

    // Add click event listeners to all team-related elements
    initializeTeamClickHandlers();

    // Add keyboard and backdrop handlers
    document.addEventListener('keydown', handleLightboxKeydown);
}

/**
 * Initialize click handlers for all team-related elements
 */
function initializeTeamClickHandlers() {
    // Team rows in tables (Overall Standings, Lineup Accuracy, etc.)
    const teamRows = document.querySelectorAll('[data-team-id]');
    teamRows.forEach(row => {
        row.style.cursor = 'pointer';
        row.addEventListener('click', handleTeamRowClick);
    });

    // Team logos in Division Strength table
    const teamLogos = document.querySelectorAll('.division-team-logo');
    teamLogos.forEach(logo => {
        logo.style.cursor = 'pointer';
        logo.addEventListener('click', handleTeamLogoClick);
    });

    // Award cards - only add team lightbox click handler for cards without award lightbox
    // (cards with data-award-type use onclick="openAwardLightbox(this)" instead)
    const awardCards = document.querySelectorAll('.award-card[data-team-name]:not([data-award-type]), .award-item[data-team-name]');
    awardCards.forEach(card => {
        card.style.cursor = 'pointer';
        card.addEventListener('click', handleAwardClick);
    });

    // Ensure award cards with award lightbox have pointer cursor
    const awardLightboxCards = document.querySelectorAll('.award-card[data-award-type]');
    awardLightboxCards.forEach(card => {
        card.style.cursor = 'pointer';
    });

    // Team logo containers in Game Summaries (use data-team-id attribute)
    const logoContainers = document.querySelectorAll('.logo-container[data-team-id]');
    logoContainers.forEach(container => {
        container.style.cursor = 'pointer';
        container.addEventListener('click', handleTeamLogoContainerClick);
    });
}

/**
 * Handle click on team row
 */
function handleTeamRowClick(event) {
    const teamId = event.currentTarget.getAttribute('data-team-id');
    if (teamId && teamLightboxData[teamId]) {
        event.preventDefault();
        showTeamLightbox(teamLightboxData[teamId]);
    }
}

/**
 * Handle click on team logo in division strength table
 */
function handleTeamLogoClick(event) {
    const teamName = event.target.getAttribute('title') || event.target.getAttribute('alt');
    if (teamName) {
        const teamData = findTeamDataByName(teamName);
        if (teamData) {
            event.preventDefault();
            showTeamLightbox(teamData);
        }
    }
}

/**
 * Handle click on award card
 */
function handleAwardClick(event) {
    const teamName = event.currentTarget.getAttribute('data-team-name');
    if (teamName) {
        const teamData = findTeamDataByName(teamName);
        if (teamData) {
            event.preventDefault();
            showTeamLightbox(teamData);
        }
    }
}

/**
 * Handle click on team logo container in game summaries
 */
function handleTeamLogoContainerClick(event) {
    const teamId = event.currentTarget.getAttribute('data-team-id');
    if (teamId && teamLightboxData[teamId]) {
        event.preventDefault();
        showTeamLightbox(teamLightboxData[teamId]);
    }
}

/**
 * Find team data by team name
 */
function findTeamDataByName(teamName) {
    for (const teamId in teamLightboxData) {
        if (teamLightboxData[teamId].name === teamName) {
            return teamLightboxData[teamId];
        }
    }
    return null;
}

/**
 * Extract team name from award element
 */
function extractTeamFromAward(awardElement) {
    // Look for team name in award text content
    const textContent = awardElement.textContent || '';

    // Try to find team name patterns (this might need adjustment based on actual award structure)
    const teamNameMatch = textContent.match(/Team:\s*([^,\n]+)/i) ||
                         textContent.match(/([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*-/);

    return teamNameMatch ? teamNameMatch[1].trim() : null;
}

/**
 * Extract team name from team header element
 */
function extractTeamFromHeader(headerElement) {
    // Look for team name in header text or child elements
    const teamNameElement = headerElement.querySelector('.team-name') ||
                           headerElement.querySelector('[data-team-name]');

    if (teamNameElement) {
        return teamNameElement.textContent.trim() || teamNameElement.getAttribute('data-team-name');
    }

    // Fallback: extract from header text content
    const textContent = headerElement.textContent || '';
    return textContent.trim();
}

/**
 * Show team lightbox with team data
 */
function showTeamLightbox(teamData) {
    // Create lightbox if it doesn't exist
    let lightbox = document.getElementById('team-lightbox');
    if (!lightbox) {
        lightbox = createLightboxElement();
        document.body.appendChild(lightbox);
    }

    // Populate lightbox content
    populateLightboxContent(lightbox, teamData);

    // Show lightbox
    lightbox.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevent body scroll

    // Focus trap for accessibility
    const firstFocusable = lightbox.querySelector('button, [tabindex="0"]');
    if (firstFocusable) {
        firstFocusable.focus();
    }
}

/**
 * Create lightbox DOM element
 */
function createLightboxElement() {
    const lightbox = document.createElement('div');
    lightbox.id = 'team-lightbox';
    lightbox.className = 'team-lightbox';

    lightbox.innerHTML = `
        <div class="lightbox-backdrop" onclick="closeTeamLightbox()"></div>
        <div class="lightbox-content">
            <div class="lightbox-header">
                <button class="lightbox-close" onclick="closeTeamLightbox()" aria-label="Close">×</button>
            </div>
            <div class="team-popover">
                <div class="team-header" id="team-header">
                    <img class="lightbox-team-logo" id="team-logo" alt="Team logo">
                    <div class="team-info">
                        <h2 class="team-name" id="team-name"></h2>
                        <div class="team-owner" id="team-owner"></div>
                        <div class="team-division" id="team-division"></div>
                    </div>
                </div>
                <div class="season-stats" id="season-stats">
                    <h3>Season Statistics</h3>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <span class="stat-label">Rank</span>
                            <span class="stat-value" id="stat-rank">-</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Record</span>
                            <span class="stat-value" id="stat-record">-</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Points For</span>
                            <span class="stat-value" id="stat-points-for">-</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Points Against</span>
                            <span class="stat-value" id="stat-points-against">-</span>
                        </div>
                    </div>
                </div>
                <div class="weekly-results" id="weekly-results">
                    <h3>Week-by-Week Results</h3>
                    <div class="results-table-container">
                        <table class="results-table">
                            <thead>
                                <tr>
                                    <th>Week</th>
                                    <th>Opponent</th>
                                    <th>Division</th>
                                    <th>Score</th>
                                    <th>Result</th>
                                    <th>Record</th>
                                </tr>
                            </thead>
                            <tbody id="weekly-results-body">
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;

    return lightbox;
}

/**
 * Populate lightbox content with team data
 */
function populateLightboxContent(lightbox, teamData) {
    // Set team header with theme colors
    const teamHeader = lightbox.querySelector('#team-header');
    const themeColors = teamData.themeColors || ['#333333', '#666666'];
    teamHeader.style.background = `linear-gradient(135deg, ${themeColors[0]}, ${themeColors[1]})`;
    teamHeader.style.color = '#ffffff';

    // Set team logo and info
    const teamLogo = lightbox.querySelector('#team-logo');
    teamLogo.src = teamData.logo || '';
    teamLogo.style.display = teamData.logo ? 'block' : 'none';

    lightbox.querySelector('#team-name').textContent = teamData.name || '';
    lightbox.querySelector('#team-owner').textContent = `Owner: ${teamData.owner || ''}`;
    lightbox.querySelector('#team-division').textContent = `Division: ${teamData.division || ''}`;

    // Set season statistics
    const stats = teamData.seasonStats || {};
    lightbox.querySelector('#stat-rank').textContent = stats.rank || '-';
    lightbox.querySelector('#stat-record').textContent =
        `${stats.wins || 0}-${stats.losses || 0}${stats.ties ? `-${stats.ties}` : ''}`;
    lightbox.querySelector('#stat-points-for').textContent =
        stats.pointsFor ? stats.pointsFor.toFixed(1) : '-';
    lightbox.querySelector('#stat-points-against').textContent =
        stats.pointsAgainst ? stats.pointsAgainst.toFixed(1) : '-';

    // Populate weekly results table
    const resultsBody = lightbox.querySelector('#weekly-results-body');
    resultsBody.innerHTML = '';

    const weeklyResults = teamData.weeklyResults || [];
    weeklyResults.forEach(result => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${result.week}</td>
            <td>${result.opponent}</td>
            <td>${result.opponentDivision}</td>
            <td>${result.teamScore} - ${result.opponentScore}</td>
            <td class="result-${result.result.toLowerCase()}">${result.result}</td>
            <td>${result.recordAfter}</td>
        `;
        resultsBody.appendChild(row);
    });

    // Show message if no weekly results
    if (weeklyResults.length === 0) {
        const noDataRow = document.createElement('tr');
        noDataRow.innerHTML = '<td colspan="6" style="text-align: center; padding: 20px;">No weekly results available</td>';
        resultsBody.appendChild(noDataRow);
    }
}

/**
 * Close team lightbox
 */
function closeTeamLightbox() {
    const lightbox = document.getElementById('team-lightbox');
    if (lightbox) {
        lightbox.style.display = 'none';
        document.body.style.overflow = ''; // Restore body scroll
    }
}

/**
 * Handle keyboard events for lightbox
 */
function handleLightboxKeydown(event) {
    if (event.key === 'Escape') {
        const teamLightbox = document.getElementById('team-lightbox');
        const awardLightbox = document.getElementById('award-lightbox');
        if (teamLightbox && teamLightbox.style.display === 'flex') {
            closeTeamLightbox();
        }
        if (awardLightbox && awardLightbox.style.display === 'flex') {
            closeAwardLightbox();
        }
    }
}

// ============================================
// Award Lightbox Functions
// ============================================

/**
 * Award configuration with emoji, title, gradient, and type
 */
const AWARD_CONFIG = {
    mvp: { emoji: '🏆', title: 'Most Valuable Player', gradient: 'linear-gradient(135deg, #d4af37, #f4d03f)', isPlayerAward: true },
    mwp: { emoji: '😢', title: 'Most Wasted Player', gradient: 'linear-gradient(135deg, #4a90d9, #63b3ed)', isPlayerAward: true },
    mup: { emoji: '💩', title: 'Most Useless Player', gradient: 'linear-gradient(135deg, #555, #777)', isPlayerAward: true },
    mdp: { emoji: '🪑', title: 'Most Disrespected Player', gradient: 'linear-gradient(135deg, #8b5cf6, #a78bfa)', isPlayerAward: true },
    hsl: { emoji: '📉', title: 'Highest Scoring Loser', gradient: 'linear-gradient(135deg, #dc3545, #e85d6a)', isPlayerAward: false },
    lsw: { emoji: '📈', title: 'Lowest Scoring Winner', gradient: 'linear-gradient(135deg, #28a745, #48c764)', isPlayerAward: false },
    ssl: { emoji: '🧠', title: 'Smartest Starting Lineup', gradient: 'linear-gradient(135deg, #007bff, #4da3ff)', isPlayerAward: false },
    ifm: { emoji: '🤦', title: 'I Fucked Myself', gradient: 'linear-gradient(135deg, #8b0000, #b22222)', isPlayerAward: false },
    accidental_genius: { emoji: '🎲', title: 'Accidental Genius', gradient: 'linear-gradient(135deg, #20c997, #48d7ac)', isPlayerAward: false },
    mccollapse: { emoji: '💔', title: 'McCollapse Award', gradient: 'linear-gradient(135deg, #fd7e14, #fea347)', isPlayerAward: false },
    clapper_collapse: { emoji: '👏', title: 'Clapper Collapse', gradient: 'linear-gradient(135deg, #e83e8c, #ec6fa4)', isPlayerAward: false }
};

/**
 * Open award lightbox from card element
 */
function openAwardLightbox(cardElement) {
    const awardType = cardElement.getAttribute('data-award-type');
    const awardDataStr = cardElement.getAttribute('data-award-data');

    if (!awardType || !awardDataStr) {
        console.warn('Award lightbox: missing data attributes');
        return;
    }

    let awardData;
    try {
        awardData = JSON.parse(awardDataStr);
    } catch (e) {
        console.error('Award lightbox: failed to parse award data', e);
        return;
    }

    // Create lightbox if it doesn't exist
    let lightbox = document.getElementById('award-lightbox');
    if (!lightbox) {
        lightbox = createAwardLightboxElement();
        document.body.appendChild(lightbox);
    }

    // Populate and show
    populateAwardLightboxContent(lightbox, awardType, awardData);
    lightbox.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

/**
 * Create award lightbox DOM element
 */
function createAwardLightboxElement() {
    const lightbox = document.createElement('div');
    lightbox.id = 'award-lightbox';
    lightbox.className = 'award-lightbox';

    lightbox.innerHTML = `
        <div class="award-lightbox-backdrop" onclick="closeAwardLightbox()"></div>
        <div class="award-lightbox-content">
            <div class="award-lightbox-header" id="award-header">
                <span class="award-emoji" id="award-emoji"></span>
                <span class="award-title" id="award-title"></span>
                <button class="award-lightbox-close" onclick="closeAwardLightbox()" aria-label="Close">&times;</button>
            </div>
            <div class="award-lightbox-body">
                <div class="award-winner-section" id="award-winner-section"></div>
                <div class="award-week-by-week" id="award-week-by-week">
                    <h3>Week-by-Week Results</h3>
                    <div class="award-results-container">
                        <table class="award-results-table">
                            <thead id="award-table-head"></thead>
                            <tbody id="award-table-body"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;

    return lightbox;
}

/**
 * Populate award lightbox content
 */
function populateAwardLightboxContent(lightbox, awardType, awardData) {
    const config = AWARD_CONFIG[awardType] || { emoji: '🏅', title: awardType.toUpperCase(), gradient: 'linear-gradient(135deg, #333, #666)', isPlayerAward: false };

    // Set header
    const header = lightbox.querySelector('#award-header');
    header.style.background = config.gradient;
    lightbox.querySelector('#award-emoji').textContent = config.emoji;
    lightbox.querySelector('#award-title').textContent = config.title.toUpperCase();

    // Build winner section
    const winnerSection = lightbox.querySelector('#award-winner-section');
    winnerSection.innerHTML = buildWinnerSectionHTML(config, awardData);

    // Build week-by-week table
    const tableHead = lightbox.querySelector('#award-table-head');
    const tableBody = lightbox.querySelector('#award-table-body');
    const weekByWeek = awardData.week_by_week_results || [];

    tableHead.innerHTML = buildTableHeaderHTML(awardType, config.isPlayerAward);
    tableBody.innerHTML = buildTableBodyHTML(awardType, config.isPlayerAward, weekByWeek);
}

/**
 * Build winner section HTML
 */
function buildWinnerSectionHTML(config, awardData) {
    const logoImg = awardData.team_logo ? `<img src="${awardData.team_logo}" alt="" class="award-winner-logo">` : '';

    if (config.isPlayerAward) {
        return `
            <h3>This Week's Winner</h3>
            <div class="award-winner-card">
                ${logoImg}
                <div class="award-winner-info">
                    <div class="award-winner-name">${awardData.player_name || '-'}</div>
                    <div class="award-winner-team">${awardData.team_name || '-'}</div>
                    <div class="award-winner-score">${awardData.score ? awardData.score.toFixed(1) : '-'} pts</div>
                    ${awardData.player_stats ? `<div class="award-winner-stats">${awardData.player_stats}</div>` : ''}
                </div>
            </div>
        `;
    } else {
        let statsHTML = '';
        if (awardData.actual_score != null && awardData.optimal_score != null) {
            const eff = awardData.efficiency_percentage || ((awardData.actual_score / awardData.optimal_score) * 100);
            statsHTML = `<div class="award-winner-stats">Actual: ${awardData.actual_score.toFixed(1)} | Optimal: ${awardData.optimal_score.toFixed(1)} | Eff: ${eff.toFixed(1)}%</div>`;
        } else if (awardData.projected_score != null && awardData.actual_score != null) {
            statsHTML = `<div class="award-winner-stats">Projected: ${awardData.projected_score.toFixed(1)} | Actual: ${awardData.actual_score.toFixed(1)}</div>`;
        }
        return `
            <h3>This Week's Winner</h3>
            <div class="award-winner-card">
                ${logoImg}
                <div class="award-winner-info">
                    <div class="award-winner-name">${awardData.team_name || '-'}</div>
                    <div class="award-winner-score">${(awardData.score || awardData.actual_score || 0).toFixed(1)} pts</div>
                    ${statsHTML}
                </div>
            </div>
        `;
    }
}

/**
 * Build table header HTML based on award type
 */
function buildTableHeaderHTML(awardType, isPlayerAward) {
    if (isPlayerAward) {
        return '<tr><th>Week</th><th>Team</th><th>Player</th><th>Points</th></tr>';
    }
    switch (awardType) {
        case 'hsl':
        case 'lsw':
            return '<tr><th>Week</th><th>Team</th><th>Points</th><th>Opp Pts</th><th>Place</th></tr>';
        case 'ssl':
        case 'ifm':
        case 'accidental_genius':
            return '<tr><th>Week</th><th>Team</th><th>Actual</th><th>Optimal</th><th>Eff %</th></tr>';
        case 'mccollapse':
            return '<tr><th>Week</th><th>Team</th><th>Actual</th><th>Optimal</th><th>Opp</th></tr>';
        case 'clapper_collapse':
            return '<tr><th>Week</th><th>Team</th><th>Proj</th><th>Actual</th><th>Opp</th></tr>';
        default:
            return '<tr><th>Week</th><th>Team</th><th>Points</th></tr>';
    }
}

/**
 * Build table body HTML based on award type and data
 */
function buildTableBodyHTML(awardType, isPlayerAward, weekByWeek) {
    if (!weekByWeek || weekByWeek.length === 0) {
        return '<tr><td colspan="5" style="text-align:center;padding:20px;">No historical data available</td></tr>';
    }

    return weekByWeek.map(row => {
        if (isPlayerAward) {
            return `<tr>
                <td>${row.week}</td>
                <td>${row.team || '-'}</td>
                <td>${row.player || '-'}</td>
                <td>${row.score ? row.score.toFixed(1) : '-'}</td>
            </tr>`;
        }
        switch (awardType) {
            case 'hsl':
            case 'lsw':
                return `<tr>
                    <td>${row.week}</td>
                    <td>${row.team || '-'}</td>
                    <td>${row.score ? row.score.toFixed(1) : '-'}</td>
                    <td>${row.opponent_score ? row.opponent_score.toFixed(1) : '-'}</td>
                    <td>${row.place || '-'}</td>
                </tr>`;
            case 'ssl':
            case 'ifm':
            case 'accidental_genius':
                const eff = row.efficiency || (row.optimal ? (row.actual / row.optimal) * 100 : 0);
                return `<tr>
                    <td>${row.week}</td>
                    <td>${row.team || '-'}</td>
                    <td>${row.actual ? row.actual.toFixed(1) : '-'}</td>
                    <td>${row.optimal ? row.optimal.toFixed(1) : '-'}</td>
                    <td>${eff ? eff.toFixed(1) + '%' : '-'}</td>
                </tr>`;
            case 'mccollapse':
                return `<tr>
                    <td>${row.week}</td>
                    <td>${row.team || '-'}</td>
                    <td>${row.actual ? row.actual.toFixed(1) : '-'}</td>
                    <td>${row.optimal ? row.optimal.toFixed(1) : '-'}</td>
                    <td>${row.opponent_score ? row.opponent_score.toFixed(1) : '-'}</td>
                </tr>`;
            case 'clapper_collapse':
                return `<tr>
                    <td>${row.week}</td>
                    <td>${row.team || '-'}</td>
                    <td>${row.projected ? row.projected.toFixed(1) : '-'}</td>
                    <td>${row.actual ? row.actual.toFixed(1) : '-'}</td>
                    <td>${row.opponent_actual ? row.opponent_actual.toFixed(1) : '-'}</td>
                </tr>`;
            default:
                return `<tr>
                    <td>${row.week}</td>
                    <td>${row.team || '-'}</td>
                    <td>${row.score ? row.score.toFixed(1) : '-'}</td>
                </tr>`;
        }
    }).join('');
}

/**
 * Close award lightbox
 */
function closeAwardLightbox() {
    const lightbox = document.getElementById('award-lightbox');
    if (lightbox) {
        lightbox.style.display = 'none';
        document.body.style.overflow = '';
    }
}