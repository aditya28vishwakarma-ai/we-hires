document.addEventListener('DOMContentLoaded', () => {
    fetchCandidates();
});

// Cache of candidates by id, used for pre-drop validation
let candidateCache = {};

// Fetch data from Flask API and render columns dynamically
function fetchCandidates() {
    fetch('/api/candidates')
        .then(res => res.json())
        .then(candidates => {
            // Update cache
            candidateCache = {};
            candidates.forEach(c => { candidateCache[c.id] = c; });

            // Clear all containers first
            const stages = ['Applied', 'Interviewing', 'Technical Test', 'Offered', 'Rejected'];
            stages.forEach(stage => {
                document.getElementById(stage).innerHTML = '';
            });

            // Populate cards into containers
            candidates.forEach(candidate => {
                const card = document.createElement('div');
                card.className = 'candidate-card';
                card.id = `candidate-${candidate.id}`;

                // Stage-based color accent
                const stageClassMap = {
                    'Applied': 'stage-applied',
                    'Interviewing': 'stage-interviewing',
                    'Technical Test': 'stage-technical-test',
                    'Offered': 'stage-offered',
                    'Rejected': 'stage-rejected'
                };
                if (stageClassMap[candidate.stage]) {
                    card.classList.add(stageClassMap[candidate.stage]);
                }
                
                // Simplified card content — name and role only
                card.innerHTML = `
                    <strong>${candidate.name}</strong><br>
                    <small>Role: ${candidate.role}</small>
                `;

                // Open detail modal on click
                card.addEventListener('click', () => openDetailModal(candidate));

                // Handle Lock Gate Rule visually and mechanically
                if (candidate.is_locked) {
                    card.classList.add('locked-card');
                    card.setAttribute('draggable', 'false');
                    card.innerHTML += ' 🔒';
                } else {
                    card.setAttribute('draggable', 'true');
                    card.ondragstart = (e) => {
                        e.dataTransfer.setData('text/plain', candidate.id);
                    };
                }

                document.getElementById(candidate.stage).appendChild(card);
            });
        })
        .catch(err => console.error('Error fetching data:', err));
}

// Drag & Drop Handlers
function allowDrop(event) {
    event.preventDefault();
}

function drop(event) {
    event.preventDefault();

    // Find target column stage string
    let column = event.target.closest('.column');
    if (!column) return;
    const targetStage = column.getAttribute('data-stage');

    // Extract candidate ID from transfer data
    const candidateId = event.dataTransfer.getData('text/plain');
    const candidate = candidateCache[candidateId];

    if (!candidate) return;

    // Locked candidates (Rejected) can never be moved
    if (candidate.is_locked) {
        openErrorModal('Candidate Locked', `${candidate.name} has already been Rejected and is locked. No further moves are allowed for this candidate.`);
        return;
    }

    const currentStage = candidate.stage;

    // Define the required "from" stage for each gated target stage
    const requiredFromStage = {
        'Technical Test': 'Interviewing',
        'Offered': 'Technical Test'
    };

    // Sequencing pre-check: block moves that skip a required prior stage
    if (targetStage in requiredFromStage && currentStage !== requiredFromStage[targetStage]) {
        openErrorModal(
            'Stage Skipped',
            `${candidate.name} is currently in "${currentStage}". They must complete the "${requiredFromStage[targetStage]}" stage before moving to "${targetStage}".`
        );
        return;
    }

    // No-op: dropping in the same column
    if (targetStage === currentStage) {
        return;
    }

    // Moving into Technical Test requires an Interview Score (>= 50 advances, else Rejected)
    if (targetStage === 'Technical Test') {
        openScoreModal({
            title: 'Interview Score',
            description: 'Enter the Interview Score (0-100). A score of 50 or above moves the candidate to Technical Test; otherwise the candidate is automatically Rejected.',
            onSubmit: (score) => {
                sendMoveRequest(candidateId, targetStage, null, score, {
                    candidateName: candidate.name,
                    scoreLabel: 'Interview Score',
                    score: score,
                    threshold: 50,
                    nextStageOnPass: 'Technical Test'
                });
            }
        });
        return;
    }

    // Moving into Offered requires a Technical Test Score (>= 70 offers, else Rejected)
    if (targetStage === 'Offered') {
        openScoreModal({
            title: 'Technical Test Score',
            description: 'Enter the Technical Test Score (0-100). A score of 70 or above results in an Offer; otherwise the candidate is automatically Rejected.',
            onSubmit: (score) => {
                sendMoveRequest(candidateId, targetStage, score, null, {
                    candidateName: candidate.name,
                    scoreLabel: 'Technical Test Score',
                    score: score,
                    threshold: 70,
                    nextStageOnPass: 'Offered'
                });
            }
        });
        return;
    }

    // Normal moves (Applied <-> Interviewing, manual Rejected) — no score needed
    sendMoveRequest(candidateId, targetStage, null, null, { candidateName: candidate.name });
}

// --- Candidate Detail Modal ---
const detailModalOverlay = document.getElementById('detailModalOverlay');
const detailModalName = document.getElementById('detailModalName');
const detailModalBody = document.getElementById('detailModalBody');
const detailModalClose = document.getElementById('detailModalClose');

function openDetailModal(candidate) {
    detailModalName.textContent = candidate.name;

    const hideScores = candidate.stage === 'Applied' || candidate.stage === 'Interviewing';

    let bodyHtml = `
        <p><span class="detail-label">Roll Number:</span> ${candidate.roll_number}</p>
        <p><span class="detail-label">Role Applied:</span> ${candidate.role}</p>
        <p><span class="detail-label">Current Stage:</span> ${candidate.stage}</p>
    `;

    if (!hideScores && candidate.interview_score !== null && candidate.interview_score !== undefined) {
        bodyHtml += `<p><span class="detail-label">Interview Score:</span> ${candidate.interview_score}</p>`;
    }

    if (!hideScores && candidate.tech_score !== null && candidate.tech_score !== undefined) {
        bodyHtml += `<p><span class="detail-label">Technical Test Score:</span> ${candidate.tech_score}</p>`;
    }

    if (candidate.stage === 'Rejected' && candidate.rejection_reason) {
        bodyHtml += `<div class="rejection-reason"><strong>Rejection Reason:</strong> ${candidate.rejection_reason}</div>`;
    }

    detailModalBody.innerHTML = bodyHtml;
    detailModalOverlay.style.display = 'flex';
}

function closeDetailModal() {
    detailModalOverlay.style.display = 'none';
}

detailModalClose.addEventListener('click', closeDetailModal);

detailModalOverlay.addEventListener('click', (e) => {
    if (e.target === detailModalOverlay) closeDetailModal();
});

// --- Score Input Modal ---
const scoreModalOverlay = document.getElementById('scoreModalOverlay');
const scoreModalTitle = document.getElementById('scoreModalTitle');
const scoreModalDescription = document.getElementById('scoreModalDescription');
const scoreModalInput = document.getElementById('scoreModalInput');
const scoreModalError = document.getElementById('scoreModalError');
const scoreModalCancel = document.getElementById('scoreModalCancel');
const scoreModalSubmit = document.getElementById('scoreModalSubmit');

let currentModalSubmitHandler = null;

function openScoreModal({ title, description, onSubmit }) {
    scoreModalTitle.textContent = title;
    scoreModalDescription.textContent = description;
    scoreModalInput.value = '';
    scoreModalError.textContent = '';
    currentModalSubmitHandler = onSubmit;
    scoreModalOverlay.style.display = 'flex';
    scoreModalInput.focus();
}

function closeScoreModal() {
    scoreModalOverlay.style.display = 'none';
    currentModalSubmitHandler = null;
}

scoreModalCancel.addEventListener('click', closeScoreModal);

scoreModalOverlay.addEventListener('click', (e) => {
    if (e.target === scoreModalOverlay) closeScoreModal();
});

scoreModalSubmit.addEventListener('click', submitScoreModal);

scoreModalInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitScoreModal();
});

function submitScoreModal() {
    const raw = scoreModalInput.value.trim();
    const score = Number(raw);

    if (raw === '' || !Number.isInteger(score) || score < 0 || score > 100) {
        scoreModalError.textContent = 'Please enter a whole number between 0 and 100.';
        return;
    }

    const handler = currentModalSubmitHandler;
    closeScoreModal();
    if (handler) handler(score);
}

// --- Error Modal (blocked actions) ---
const errorModalOverlay = document.getElementById('errorModalOverlay');
const errorModalTitle = document.getElementById('errorModalTitle');
const errorModalMessage = document.getElementById('errorModalMessage');
const errorModalClose = document.getElementById('errorModalClose');

function openErrorModal(title, message) {
    errorModalTitle.textContent = title || 'Action Not Allowed';
    errorModalMessage.textContent = message;
    errorModalOverlay.style.display = 'flex';
}

function closeErrorModal() {
    errorModalOverlay.style.display = 'none';
}

errorModalClose.addEventListener('click', closeErrorModal);

errorModalOverlay.addEventListener('click', (e) => {
    if (e.target === errorModalOverlay) closeErrorModal();
});

// --- Rejection Modal (candidate auto-rejected) ---
const rejectionModalOverlay = document.getElementById('rejectionModalOverlay');
const rejectionModalTitle = document.getElementById('rejectionModalTitle');
const rejectionModalMessage = document.getElementById('rejectionModalMessage');
const rejectionModalClose = document.getElementById('rejectionModalClose');

function openRejectionModal(title, message) {
    rejectionModalTitle.textContent = title || 'Candidate Rejected';
    rejectionModalMessage.textContent = message;
    rejectionModalOverlay.style.display = 'flex';
}

function closeRejectionModal() {
    rejectionModalOverlay.style.display = 'none';
}

rejectionModalClose.addEventListener('click', closeRejectionModal);

rejectionModalOverlay.addEventListener('click', (e) => {
    if (e.target === rejectionModalOverlay) closeRejectionModal();
});

function sendMoveRequest(id, targetStage, techScore, interviewScore, context = {}) {
    const payload = { target_stage: targetStage };
    if (techScore !== null) payload.tech_score = techScore;
    if (interviewScore !== null) payload.interview_score = interviewScore;

    fetch(`/api/candidates/${id}/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(async response => {
        const data = await response.json();

        if (!response.ok) {
            // Server-side validation failure (400, 403, 404) — distinct titles per status
            let title = 'Action Not Allowed';
            if (response.status === 403) title = 'Candidate Locked';
            else if (response.status === 404) title = 'Candidate Not Found';
            else if (response.status === 400) title = 'Invalid Move';
            openErrorModal(title, data.error || 'An unexpected error occurred.');
        } else if (data.candidate && data.candidate.stage === 'Rejected' && data.candidate.is_locked) {
            // Auto-rejection from a score gate — show a dedicated rejection card with the reason
            const name = context.candidateName || data.candidate.name;
            let reasonLine = data.message || 'The candidate did not meet the required threshold.';

            if (context.scoreLabel && context.score !== undefined && context.threshold !== undefined) {
                reasonLine = `${name} scored ${context.score} on the ${context.scoreLabel}, below the required minimum of ${context.threshold}.`;
            }

            openRejectionModal('Candidate Rejected', reasonLine);
        }

        // Refresh the whole board state to display the true data layout
        fetchCandidates();
    })
    .catch(err => console.error('Network Error:', err));
}