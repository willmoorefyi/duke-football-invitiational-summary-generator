// Client-side scripts for fantasy football reports
// Note: Logo fallback behavior has been removed - all teams now have hard-coded logos

document.addEventListener('DOMContentLoaded', function() {
    console.log('Fantasy football report loaded');

    // Initialize sortable tables
    initializeSortableTables();
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

        return newDirection === 'asc' ? comparison : -comparison;
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