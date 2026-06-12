import os
import json
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
DATA_FILE = 'candidates.json'

# Helper function to read data safely
def load_candidates():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

# Helper function to write data safely
def save_candidates(candidates):
    with open(DATA_FILE, 'w') as f:
        json.dump(candidates, f, indent=2)

# 1. GET / — Render the board page
@app.route('/')
def index():
    return render_template('index.html')

# 2. GET /api/candidates — Return all candidates from JSON
@app.route('/api/candidates', methods=['GET'])
def get_candidates():
    return jsonify(load_candidates())

# 3. POST /api/candidates — Add new candidate
@app.route('/api/candidates', methods=['POST'])
def add_candidate():
    data = request.json or {}
    name = data.get('name')
    roll_number = data.get('roll_number')
    role = data.get('role')

    if not name or not roll_number or not role:
        return jsonify({"error": "Missing required fields: name, roll_number, or role"}), 400

    candidates = load_candidates()
    
    # Auto-increment ID strategy
    new_id = max([c['id'] for c in candidates], default=0) + 1

    new_candidate = {
        "id": new_id,
        "name": name,
        "roll_number": roll_number,
        "role": role,
        "stage": "Applied",
        "tech_score": None,
        "is_locked": False
    }

    candidates.append(new_candidate)
    save_candidates(candidates)
    return jsonify(new_candidate), 201

# 4. POST /api/candidates/<id>/move — Handle stage transition + gate logic
@app.route('/api/candidates/<int:cid>/move', methods=['POST'])
def move_candidate(cid):
    data = request.json or {}
    target_stage = data.get('target_stage')
    input_score = data.get('tech_score') # Optional in request body, depends on the stage

    candidates = load_candidates()
    candidate = next((c for c in candidates if c['id'] == cid), None)

    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404

    # --- RULE 4: Permanent Lock ---
    if candidate.get('is_locked', False):
        return jsonify({"error": "Candidate card is locked. No further movements allowed."}), 403

    # --- RULE 1: Score Requirement ---
    # If explicitly moving to Technical Test (or skipping ahead), look for incoming score or existing score
    if target_stage in ["Technical Test", "Offered"]:
        # Use incoming score if provided; otherwise fall back to what they already have
        score_to_validate = input_score if input_score is not None else candidate.get('tech_score')
        
        if score_to_validate is None:
            return jsonify({"error": "Moving to this stage requires a technical score."}), 400
        
        try:
            score_int = int(score_to_validate)
            if score_int < 0 or score_int > 100:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({"error": "Technical score must be an integer between 0 and 100."}), 400
        
        # Update the candidate's tracking score if a valid one was passed
        if input_score is not None:
            candidate['tech_score'] = int(input_score)

    # --- RULE 2: Auto-Rejection ---
    current_score = candidate.get('tech_score')
    if current_score is not None and current_score < 70:
        candidate['stage'] = "Rejected"
        candidate['is_locked'] = True
        save_candidates(candidates)
        return jsonify({
            "message": "Candidate auto-rejected due to low technical score.",
            "candidate": candidate
        }), 200

    # --- RULE 3: Offer Confirmation Validation ---
    if target_stage == "Offered":
        # Validate they are coming from Technical Test and have a passing grade
        if candidate['stage'] != "Technical Test" or current_score is None or current_score < 70:
            return jsonify({"error": "Candidates can only be offered if they pass the Technical Test stage."}), 400

    # If all rules pass, update the stage normally
    if target_stage:
        candidate['stage'] = target_stage

    save_candidates(candidates)
    return jsonify({
        "message": "Candidate updated successfully.",
        "candidate": candidate
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)