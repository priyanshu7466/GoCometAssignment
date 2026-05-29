/* ── Nova Trade Document Pipeline — Frontend Logic ───────────────── */

// ── State ───────────────────────────────────────────────────────────
let currentResult = null;

// ── Panel Management ────────────────────────────────────────────────

function showPanel(panelId) {
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById(`panel-${panelId}`);
    if (panel) panel.classList.add('active');
}

function togglePanel(panelId) {
    const panel = document.getElementById(`panel-${panelId}`);
    if (panel && panel.classList.contains('active')) {
        showPanel('upload');
    } else {
        showPanel(panelId);
        if (panelId === 'history') loadHistory();
    }
}

// ── File Upload ─────────────────────────────────────────────────────

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
        processFile(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
        processFile(fileInput.files[0]);
    }
});

// ── Pipeline Processing ─────────────────────────────────────────────

async function processFile(file) {
    // Show processing panel
    showPanel('processing');
    document.getElementById('processing-filename').textContent = file.name;

    // Reset steps
    resetSteps();
    activateStep('extract');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Pipeline failed');
        }

        // Simulate step progression (the API does it all at once, but we show steps)
        completeStep('extract');
        activateStep('validate');
        await sleep(400);

        completeStep('validate');
        activateStep('route');
        await sleep(400);

        completeStep('route');
        activateStep('store');
        await sleep(300);

        completeStep('store');

        const result = await response.json();
        currentResult = result;

        await sleep(500);
        showResults(result);

    } catch (error) {
        alert(`Pipeline Error: ${error.message}`);
        showPanel('upload');
    }
}

function resetSteps() {
    document.querySelectorAll('.step').forEach(s => {
        s.classList.remove('active', 'done');
    });
    document.querySelectorAll('.step-status').forEach(s => {
        s.innerHTML = '<span class="waiting">Waiting</span>';
    });
}

function activateStep(stepId) {
    const step = document.getElementById(`step-${stepId}`);
    step.classList.add('active');
    step.querySelector('.step-status').innerHTML = '<span class="spinner"></span>';
}

function completeStep(stepId) {
    const step = document.getElementById(`step-${stepId}`);
    step.classList.remove('active');
    step.classList.add('done');
    step.querySelector('.step-status').innerHTML = '<span style="color: var(--green); font-weight: 600;">✓ Done</span>';
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Results Display ─────────────────────────────────────────────────

function showResults(result) {
    showPanel('results');

    const validation = result.validation;
    const routing = result.routing;
    const extraction = result.extraction;

    // Decision banner
    const banner = document.getElementById('decision-banner');
    const icon = document.getElementById('decision-icon');
    const title = document.getElementById('decision-title');
    const reasoning = document.getElementById('decision-reasoning');
    const badge = document.getElementById('decision-badge');

    banner.className = 'decision-banner';

    const decision = routing.decision;
    if (decision === 'auto_approve') {
        banner.classList.add('approved');
        icon.textContent = '✓';
        title.textContent = 'Document Approved';
        badge.textContent = 'APPROVED';
    } else if (decision === 'amendment_required') {
        banner.classList.add('amendment');
        icon.textContent = '✕';
        title.textContent = 'Amendment Required';
        badge.textContent = 'AMENDMENT';
    } else {
        banner.classList.add('review');
        icon.textContent = '⚠';
        title.textContent = 'Flagged for Review';
        badge.textContent = 'REVIEW';
    }

    reasoning.textContent = routing.reasoning || 'No reasoning provided.';

    // Stats
    const summary = validation.summary;
    document.getElementById('stat-matches').textContent = summary.matches;
    document.getElementById('stat-mismatches').textContent = summary.mismatches;
    document.getElementById('stat-uncertain').textContent = summary.uncertain;
    document.getElementById('stat-total').textContent = summary.total_fields;

    // Fields table
    renderFieldsTable(validation.fields);

    // Extraction grid
    renderExtractionGrid(extraction);

    // Draft email
    const draftArea = document.getElementById('draft-email');
    if (routing.draft_email) {
        draftArea.value = routing.draft_email;
    } else if (routing.review_note) {
        draftArea.value = `[Review Note for CG Operator]\n\n${routing.review_note}`;
    } else {
        draftArea.value = 'No draft email needed — document was approved.';
    }

    // Default to fields tab
    switchTab('fields');
}

function renderFieldsTable(fields) {
    const container = document.getElementById('fields-table');
    container.innerHTML = '';

    // Header
    const header = document.createElement('div');
    header.className = 'field-row field-row-header';
    header.innerHTML = `
        <div>Field</div>
        <div>Reason</div>
        <div>Confidence</div>
        <div>Status</div>
    `;
    container.appendChild(header);

    fields.forEach((field, index) => {
        // Main row
        const row = document.createElement('div');
        row.className = 'field-row';
        row.onclick = () => toggleFieldDetail(index);

        const confidencePercent = Math.round((field.confidence || 0) * 100);
        const confColor = confidencePercent >= 80 ? 'var(--green)' :
                          confidencePercent >= 50 ? 'var(--amber)' : 'var(--red)';

        const fieldLabel = field.field.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

        row.innerHTML = `
            <div class="field-name">${fieldLabel}</div>
            <div class="field-reason">${truncate(field.reason, 60)}</div>
            <div class="field-confidence">
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${confidencePercent}%; background: ${confColor};"></div>
                </div>
                <span class="confidence-value">${confidencePercent}%</span>
            </div>
            <div><span class="status-pill ${field.status}">${field.status}</span></div>
        `;
        container.appendChild(row);

        // Detail row (hidden by default)
        const detail = document.createElement('div');
        detail.className = 'field-detail';
        detail.id = `field-detail-${index}`;
        detail.innerHTML = `
            <div class="field-detail-row">
                <span class="field-detail-label">Found:</span>
                <span class="field-detail-value found">${field.found || '(not found)'}</span>
            </div>
            <div class="field-detail-row">
                <span class="field-detail-label">Expected:</span>
                <span class="field-detail-value expected">${field.expected || '(any / present)'}</span>
            </div>
            <div class="field-detail-row">
                <span class="field-detail-label">Reason:</span>
                <span class="field-detail-value">${field.reason}</span>
            </div>
            <div class="field-detail-row">
                <span class="field-detail-label">Rule:</span>
                <span class="field-detail-value">${field.rule_description || '-'}</span>
            </div>
        `;
        container.appendChild(detail);
    });
}

function toggleFieldDetail(index) {
    const detail = document.getElementById(`field-detail-${index}`);
    if (detail) {
        detail.classList.toggle('expanded');
    }
}

function renderExtractionGrid(extraction) {
    const container = document.getElementById('extraction-grid');
    container.innerHTML = '';

    const fields = [
        'document_type', 'document_reference', 'consignee_name', 'hs_code',
        'port_of_loading', 'port_of_discharge', 'incoterms',
        'description_of_goods', 'gross_weight', 'invoice_number'
    ];

    fields.forEach(field => {
        const data = extraction[field];
        if (!data) return;

        const card = document.createElement('div');
        card.className = 'extraction-card';

        const confidencePercent = Math.round((data.confidence || 0) * 100);
        const confColor = confidencePercent >= 80 ? 'var(--green)' :
                          confidencePercent >= 50 ? 'var(--amber)' : 'var(--red)';

        const label = field.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

        card.innerHTML = `
            <div class="extraction-label">${label}</div>
            <div class="extraction-value">${data.value || '—'}</div>
            <div class="extraction-confidence">
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${confidencePercent}%; background: ${confColor};"></div>
                </div>
                <span class="confidence-value">${confidencePercent}%</span>
            </div>
        `;
        container.appendChild(card);
    });
}

// ── Tabs ─────────────────────────────────────────────────────────────

function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById(`tab-${tabName}`).classList.add('active');
    document.getElementById(`content-${tabName}`).classList.add('active');
}

// ── Draft Email ──────────────────────────────────────────────────────

function copyDraft() {
    const textarea = document.getElementById('draft-email');
    textarea.select();
    navigator.clipboard.writeText(textarea.value);

    const btn = event.target;
    const original = btn.textContent;
    btn.textContent = '✓ Copied!';
    setTimeout(() => btn.textContent = original, 1500);
}

// ── History ──────────────────────────────────────────────────────────

async function loadHistory() {
    const container = document.getElementById('history-list');
    container.innerHTML = '<p class="empty-state">Loading...</p>';

    try {
        const response = await fetch('/api/shipments');
        const data = await response.json();

        if (!data.shipments || data.shipments.length === 0) {
            container.innerHTML = '<p class="empty-state">No documents processed yet.</p>';
            return;
        }

        container.innerHTML = '';
        data.shipments.forEach(s => {
            const item = document.createElement('div');
            item.className = 'history-item';
            item.onclick = () => loadShipmentDetail(s.id);

            const icon = s.decision === 'auto_approve' ? '✅' :
                         s.decision === 'amendment_required' ? '❌' : '⚠️';

            const date = new Date(s.created_at).toLocaleString();

            item.innerHTML = `
                <div class="history-icon">${icon}</div>
                <div class="history-info">
                    <div class="history-name">${s.file_name}</div>
                    <div class="history-meta">${s.customer_name} · ${date}</div>
                </div>
                <span class="status-pill ${s.decision === 'auto_approve' ? 'match' : s.decision === 'amendment_required' ? 'mismatch' : 'uncertain'}">
                    ${s.decision.replace(/_/g, ' ')}
                </span>
            `;
            container.appendChild(item);
        });
    } catch (error) {
        container.innerHTML = `<p class="empty-state">Error loading history: ${error.message}</p>`;
    }
}

async function loadShipmentDetail(id) {
    try {
        const response = await fetch(`/api/shipments/${id}`);
        const shipment = await response.json();

        // Reconstruct the result format
        const result = {
            extraction: shipment.extraction_json,
            validation: shipment.validation_json,
            routing: shipment.routing_json,
        };

        currentResult = result;
        showResults(result);
    } catch (error) {
        alert(`Error loading shipment: ${error.message}`);
    }
}

// ── Query ────────────────────────────────────────────────────────────

function setQuery(text) {
    document.getElementById('query-input').value = text;
    runQuery();
}

async function runQuery() {
    const input = document.getElementById('query-input');
    const question = input.value.trim();
    if (!question) return;

    const resultDiv = document.getElementById('query-result');
    const answerDiv = document.getElementById('query-answer');
    const sqlPre = document.getElementById('query-sql');

    resultDiv.style.display = 'block';
    answerDiv.textContent = 'Thinking...';
    sqlPre.textContent = '';

    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question }),
        });

        const data = await response.json();
        answerDiv.textContent = data.answer;
        sqlPre.textContent = data.sql;
    } catch (error) {
        answerDiv.textContent = `Error: ${error.message}`;
    }
}

// ── Reset ────────────────────────────────────────────────────────────

function resetPipeline() {
    currentResult = null;
    fileInput.value = '';
    showPanel('upload');
}

// ── Helpers ──────────────────────────────────────────────────────────

function truncate(str, maxLen) {
    if (!str) return '';
    return str.length > maxLen ? str.substring(0, maxLen) + '...' : str;
}
