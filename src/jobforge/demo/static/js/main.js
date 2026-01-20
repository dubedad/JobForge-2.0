/**
 * Main Application Entry Point - JobForge Demo
 *
 * Initializes i18n, wizard controller, and SSE integration.
 * Coordinates all UI interactions and deployment narration.
 */

document.addEventListener('DOMContentLoaded', async () => {
  // Initialize internationalization
  const i18n = new I18n();
  await i18n.load(i18n.locale);

  // Initialize wizard controller
  const wizard = new WizardController();

  // Deployment stream instance (created on load)
  let deploymentStream = null;

  // Track deployment state
  let deploymentState = {
    totalTables: 0,
    currentTable: 0,
    totalRelationships: 0,
    currentRelationship: 0,
    started: false,
    completed: false
  };

  // ===== Language Toggle =====
  const langToggle = document.getElementById('lang-toggle');
  if (langToggle) {
    langToggle.addEventListener('click', async () => {
      await i18n.toggle();
      updateLangToggleLabel(langToggle, i18n);
    });

    // Initialize toggle label
    updateLangToggleLabel(langToggle, i18n);
  }

  function updateLangToggleLabel(button, i18n) {
    // Button shows the OTHER language (what you switch TO)
    button.textContent = i18n.isFrench() ? 'EN' : 'FR';
    const ariaKey = i18n.isFrench() ? 'a11y.langToggle' : 'a11y.langToggle';
    button.setAttribute('aria-label', i18n.t(ariaKey));
  }

  // ===== Theme Toggle =====
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    // Initialize theme from localStorage or system preference
    initializeTheme();

    themeToggle.addEventListener('click', () => {
      toggleTheme();
    });
  }

  function initializeTheme() {
    const savedTheme = localStorage.getItem('jobforge-theme');
    if (savedTheme) {
      document.documentElement.setAttribute('data-theme', savedTheme);
    }
    // If no saved preference, system preference is handled by CSS
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    let newTheme;

    if (current === 'dark') {
      newTheme = 'light';
    } else if (current === 'light') {
      newTheme = 'dark';
    } else {
      // No explicit theme set, check system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      newTheme = prefersDark ? 'light' : 'dark';
    }

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('jobforge-theme', newTheme);

    // Announce theme change
    wizard.announce(`Theme changed to ${newTheme} mode`);
  }

  // ===== Navigation Buttons =====
  const backButton = document.getElementById('back-button');
  const nextButton = document.getElementById('next-button');

  if (backButton) {
    backButton.addEventListener('click', () => {
      wizard.previous();
    });
  }

  if (nextButton) {
    nextButton.addEventListener('click', () => {
      wizard.next();
    });
  }

  // ===== Load Button =====
  const loadButton = document.getElementById('load-button');
  if (loadButton) {
    loadButton.addEventListener('click', () => {
      handleLoadClick();
    });
  }

  function handleLoadClick() {
    // Get the data path (optional - uses default if empty)
    const dataPathInput = document.getElementById('data-path');
    const schemaPath = dataPathInput ? dataPathInput.value.trim() : '';

    // Show loading state
    loadButton.classList.add('loading');
    loadButton.disabled = true;

    // Transition to Step 2
    wizard.goToStep(2);

    // Connect to SSE stream for narration
    connectToStream(schemaPath);
  }

  // ===== SSE Stream Connection =====
  function connectToStream(schemaPath) {
    // Build URL with optional schema path
    let url = '/api/deploy/stream';
    if (schemaPath) {
      url += `?schema_path=${encodeURIComponent(schemaPath)}`;
    }

    // Clear previous log entries
    const activityLog = document.getElementById('activity-log');
    if (activityLog) {
      activityLog.innerHTML = '';
    }

    // Reset deployment state
    deploymentState = {
      totalTables: 0,
      currentTable: 0,
      totalRelationships: 0,
      currentRelationship: 0,
      started: false,
      completed: false
    };

    // Create and connect stream
    deploymentStream = new DeploymentStream(url, {
      onStart: handleStartEvent,
      onTable: handleTableEvent,
      onRelationship: handleRelationshipEvent,
      onMeasure: handleMeasureEvent,
      onComplete: handleCompleteEvent,
      onError: handleErrorEvent,
      onHeartbeat: handleHeartbeatEvent
    });

    deploymentStream.connect();
  }

  function handleStartEvent(data) {
    deploymentState.started = true;
    deploymentState.totalTables = data.total_tables || 0;
    deploymentState.totalRelationships = data.total_relationships || 0;

    // Update counters
    updateCounters();

    // Add log entry
    addLogEntry('start', 'Deployment starting', `${deploymentState.totalTables} tables, ${deploymentState.totalRelationships} relationships`);

    // Announce to screen reader
    wizard.announce(`Deployment started: ${deploymentState.totalTables} tables to deploy`);
  }

  function handleTableEvent(data) {
    deploymentState.currentTable++;

    // Update counters and progress
    updateCounters();
    updateProgress();

    // Add log entry
    const detail = data.table_type ? `${data.table_type} table` : 'table';
    addLogEntry('table', `Creating ${data.name}`, detail);
  }

  function handleRelationshipEvent(data) {
    deploymentState.currentRelationship++;

    // Update counters
    updateCounters();

    // Add log entry
    const detail = `${data.from_table} -> ${data.to_table}`;
    addLogEntry('relationship', `Adding relationship`, detail);
  }

  function handleMeasureEvent(data) {
    // Add log entry
    const detail = data.folder ? `in ${data.folder}` : '';
    addLogEntry('measure', `Creating measure: ${data.name}`, detail);
  }

  function handleCompleteEvent(data) {
    deploymentState.completed = true;

    // Update progress to 100%
    const progressFill = document.querySelector('.progress-fill');
    if (progressFill) {
      progressFill.style.width = '100%';
    }

    // Add completion log entry
    const duration = data.duration ? ` (${data.duration.toFixed(1)}s)` : '';
    addLogEntry('complete', 'Deployment complete', `Success${duration}`);

    // Mark step 2 as complete
    wizard.markComplete(2);

    // Reset load button
    if (loadButton) {
      loadButton.classList.remove('loading');
      loadButton.disabled = false;
    }

    // Announce completion
    wizard.announce('Deployment narration complete. You may proceed to the Review step.');

    // Load catalogue data for step 4
    loadCatalogueData();
  }

  function handleErrorEvent(data) {
    const message = data.message || 'An error occurred';
    addLogEntry('error', 'Error', message);

    // Reset load button
    if (loadButton) {
      loadButton.classList.remove('loading');
      loadButton.disabled = false;
    }

    // Announce error
    wizard.announce(`Error: ${message}`);
  }

  function handleHeartbeatEvent(data) {
    // Heartbeat - just log for debugging
    console.log('Heartbeat received:', data);
  }

  function updateCounters() {
    const tablesCurrentEl = document.getElementById('tables-current');
    const tablesTotalEl = document.getElementById('tables-total');
    const relCurrentEl = document.getElementById('relationships-current');
    const relTotalEl = document.getElementById('relationships-total');

    if (tablesCurrentEl) tablesCurrentEl.textContent = deploymentState.currentTable;
    if (tablesTotalEl) tablesTotalEl.textContent = deploymentState.totalTables;
    if (relCurrentEl) relCurrentEl.textContent = deploymentState.currentRelationship;
    if (relTotalEl) relTotalEl.textContent = deploymentState.totalRelationships;
  }

  function updateProgress() {
    const total = deploymentState.totalTables + deploymentState.totalRelationships;
    const current = deploymentState.currentTable + deploymentState.currentRelationship;
    const percent = total > 0 ? Math.round((current / total) * 100) : 0;

    const progressBar = document.getElementById('deployment-progress');
    const progressFill = document.querySelector('.progress-fill');

    if (progressBar) {
      progressBar.setAttribute('aria-valuenow', percent);
    }
    if (progressFill) {
      progressFill.style.width = `${percent}%`;
    }
  }

  function addLogEntry(type, title, detail) {
    const activityLog = document.getElementById('activity-log');
    if (!activityLog) return;

    // Remove placeholder if present
    const placeholder = activityLog.querySelector('.log-placeholder');
    if (placeholder) {
      placeholder.remove();
    }

    // Fade older entries
    const existingEntries = activityLog.querySelectorAll('.log-entry');
    existingEntries.forEach((entry, index) => {
      if (index >= 3) {
        entry.classList.add('faded');
      }
    });

    // Create new entry
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
      <span class="log-icon ${type}-icon">
        ${getIconForType(type)}
      </span>
      <span class="log-content">
        <span class="log-title">${escapeHtml(title)}</span>
        ${detail ? `<span class="log-detail">${escapeHtml(detail)}</span>` : ''}
      </span>
    `;

    // Insert at top
    activityLog.insertBefore(entry, activityLog.firstChild);
  }

  function getIconForType(type) {
    switch (type) {
      case 'start':
        return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>';
      case 'table':
        return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>';
      case 'relationship':
        return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>';
      case 'measure':
        return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20V10"></path><path d="M18 20V4"></path><path d="M6 20v-4"></path></svg>';
      case 'complete':
        return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>';
      case 'error':
        return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>';
      default:
        return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle></svg>';
    }
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ===== Catalogue Data =====
  async function loadCatalogueData() {
    try {
      const response = await fetch('/api/catalogue');
      if (!response.ok) {
        throw new Error('Failed to load catalogue data');
      }

      const data = await response.json();
      populateCatalogueTable(data.tables || []);

      // Update review stats
      const totalTablesEl = document.getElementById('total-tables');
      const totalRelEl = document.getElementById('total-relationships');
      if (totalTablesEl) totalTablesEl.textContent = data.tables?.length || 0;
      if (totalRelEl) totalRelEl.textContent = deploymentState.totalRelationships;

    } catch (err) {
      console.error('Error loading catalogue:', err);
    }
  }

  function populateCatalogueTable(tables) {
    const tbody = document.getElementById('catalogue-body');
    if (!tbody) return;

    tbody.innerHTML = '';

    tables.forEach(table => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${escapeHtml(table.name || '')}</td>
        <td>${escapeHtml(table.table_type || '')}</td>
        <td>${table.columns || 0}</td>
        <td>${escapeHtml(table.source || '')}</td>
      `;
      tbody.appendChild(row);
    });
  }

  // ===== Export CSV Button =====
  const exportCsvButton = document.getElementById('export-csv-button');
  if (exportCsvButton) {
    exportCsvButton.addEventListener('click', () => {
      exportCatalogue();
    });
  }

  function exportCatalogue() {
    const tbody = document.getElementById('catalogue-body');
    if (!tbody) return;

    // Build CSV content
    const headers = ['Table Name', 'Type', 'Columns', 'Source'];
    const rows = Array.from(tbody.querySelectorAll('tr')).map(row => {
      return Array.from(row.querySelectorAll('td')).map(cell => {
        // Escape quotes and wrap in quotes
        return `"${cell.textContent.replace(/"/g, '""')}"`;
      }).join(',');
    });

    const csv = [headers.join(','), ...rows].join('\n');

    // Create download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'jobforge-catalogue.csv';
    link.click();
    URL.revokeObjectURL(url);

    // Show completion message
    const completionMessage = document.getElementById('completion-message');
    if (completionMessage) {
      completionMessage.classList.add('visible');
    }

    // Announce export
    wizard.announce('Catalogue exported to CSV file');
  }

  // ===== Refresh Button =====
  const refreshButton = document.getElementById('refresh-button');
  if (refreshButton) {
    refreshButton.addEventListener('click', () => {
      loadCatalogueData();
      wizard.announce('Data refreshed');
    });
  }

  // ===== Progress Step Clicks =====
  const progressItems = document.querySelectorAll('.wizard-progress .step');
  progressItems.forEach((item, index) => {
    item.addEventListener('click', () => {
      const stepNum = index + 1;
      // Only allow clicking on completed steps or current step
      if (wizard.completedSteps.has(stepNum) || stepNum <= wizard.getCurrentStep()) {
        wizard.goToStep(stepNum);
      }
    });

    // Make focusable for keyboard users
    item.setAttribute('tabindex', '0');
    item.setAttribute('role', 'button');
    item.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        item.click();
      }
    });
  });

  // Initialize nav button states
  wizard.updateNavButtons();
});
