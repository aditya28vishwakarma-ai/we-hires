document.addEventListener('DOMContentLoaded', () => {
    fetchCandidates();
});

// Fetch data from Flask API and render columns dynamically
function fetchCandidates() {
    fetch('/api/candidates')
        .then(res => res.json())
        .then(candidates => {
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
                
                // Add content
                card.innerHTML = `
                    <strong>${candidate.name}</strong><br>
                    <small>Roll: ${candidate.roll_number}</small><br>
                    <small>Role: ${candidate.role}</small>
                    ${candidate.tech_score !== null ? `<br><span class="score-tag">Score: ${candidate.tech_score}</span>` : ''}
                `;

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
    
    let score = null;

    // Rule 1 Contextual UI Trigger: Ask for score if going to Tech Test or higher
    if (targetStage === 'Technical Test' || targetStage === 'Offered') {
        const input = prompt("Enter Technical Score (0-100):");
        if (input === null) return; // Action aborted by user
        score = parseInt(input, 10);
    }

    // Rule 3 Contextual UI Trigger: Confirmation dialog if going to Offered stage
    if (targetStage === 'Offered') {
        const proceed = confirm("Are you sure you want to issue an employment offer to this student?");
        if (!proceed) return; // Action aborted by user
    }

    // Dispatch request to server
    sendMoveRequest(candidateId, targetStage, score);
}

function sendMoveRequest(id, targetStage, score) {
    const payload = { target_stage: targetStage };
    if (score !== null) payload.tech_score = score;

    fetch(`/api/candidates/${id}/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(async response => {
        const data = await response.json();
        
        if (!response.ok) {
            // Displays Server Rule violations (400, 403, 404)
            alert(`Error: ${data.error}`);
        } else if (data.candidate && data.candidate.is_locked) {
            alert(`System Status: ${data.message}`);
        }
        
        // Refresh the whole board state to display the true data layout
        fetchCandidates();
    })
    .catch(err => console.error('Network Error:', err));
}