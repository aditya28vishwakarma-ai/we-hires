import os
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "wehires-secret-key-2026"

DATA_FILE = "candidates.json"
RECRUITER_LOG_FILE = "recruiter_log.json"


# Helper function to read data safely
def load_candidates():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


# Helper function to write data safely
def save_candidates(candidates):
    with open(DATA_FILE, "w") as f:
        json.dump(candidates, f, indent=2)


def load_recruiter_log():
    if not os.path.exists(RECRUITER_LOG_FILE):
        return []
    with open(RECRUITER_LOG_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_recruiter_log(log):
    with open(RECRUITER_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def log_recruiter_login(name):
    log = load_recruiter_log()
    # Update existing or add new entry
    existing = next((r for r in log if r["name"].lower() == name.lower()), None)
    if existing:
        existing["last_login"] = datetime.now().isoformat()
        existing["login_count"] = existing.get("login_count", 1) + 1
    else:
        log.append(
            {
                "name": name,
                "initials": "".join([w[0].upper() for w in name.split()[:2]]),
                "last_login": datetime.now().isoformat(),
                "login_count": 1,
            }
        )
    save_recruiter_log(log)


VALID_ROLES = [
    "Software Engineer",
    "Frontend Developer",
    "Backend Developer",
    "Data Analyst",
    "DevOps Engineer",
]

# ── Pages ──────────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    return redirect(url_for("recruiter_login"))


# Recruiter login (simple name-based, no password — for future upgrade)
@app.route("/login", methods=["GET", "POST"])
def recruiter_login():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if name:
            session["recruiter_name"] = name
            log_recruiter_login(name)
            return redirect(url_for("recruiter_dashboard"))
    return render_template("recruiter_login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("recruiter_login"))


@app.route("/dashboard")
def recruiter_dashboard():
    candidates = load_candidates()
    recruiter_name = session.get("recruiter_name", "Recruiter")

    # Build per-role stats for "Active Roles" panel
    role_stats = []
    for role in VALID_ROLES:
        role_candidates = [c for c in candidates if c["role"] == role]
        total = len(role_candidates)
        finalists = len(
            [c for c in role_candidates if c["stage"] in ("Technical Test", "Offered")]
        )
        offered = len([c for c in role_candidates if c["stage"] == "Offered"])
        rejected = len([c for c in role_candidates if c["stage"] == "Rejected"])
        in_progress = total - rejected
        if total == 0:
            status_label = "No applicants"
        elif offered > 0:
            status_label = f"{offered} Offered"
        elif finalists > 0:
            status_label = f"{finalists} Finalist{'s' if finalists != 1 else ''}"
        elif in_progress > 0:
            status_label = "Sourcing"
        else:
            status_label = "All Rejected"
        role_stats.append(
            {
                "role": role,
                "total": total,
                "finalists": finalists,
                "offered": offered,
                "rejected": rejected,
                "in_progress": in_progress,
                "status_label": status_label,
            }
        )

    total_candidates = len(candidates)
    total_offered = len([c for c in candidates if c["stage"] == "Offered"])
    total_rejected = len([c for c in candidates if c["stage"] == "Rejected"])
    total_in_progress = total_candidates - total_rejected - total_offered

    summary = {
        "total_candidates": total_candidates,
        "total_offered": total_offered,
        "total_rejected": total_rejected,
        "total_in_progress": total_in_progress,
    }

    # Feedback pending = candidates in Technical Test (need recruiter decision)
    pending_feedback = [c for c in candidates if c["stage"] == "Technical Test"]

    # Recruiter activity log (recent logins)
    recruiter_log = sorted(
        load_recruiter_log(), key=lambda r: r["last_login"], reverse=True
    )

    return render_template(
        "recruiter_dashboard.html",
        role_stats=role_stats,
        summary=summary,
        pending_feedback=pending_feedback,
        recruiter_log=recruiter_log,
        recruiter_name=recruiter_name,
    )


@app.route("/candidates-board")
def candidates_board():
    candidates = load_candidates()
    recruiter_name = session.get("recruiter_name", "Recruiter")
    # Group by stage for template rendering
    stages = {
        "Applied": [],
        "Interviewing": [],
        "Technical Test": [],
        "Offered": [],
        "Rejected": [],
    }
    for c in candidates:
        stage = c.get("stage", "Applied")
        if stage in stages:
            stages[stage].append(c)
    return render_template(
        "candidates_board.html", stages=stages, recruiter_name=recruiter_name
    )


@app.route("/analytics")
def analytics():
    candidates = load_candidates()
    recruiter_name = session.get("recruiter_name", "Recruiter")

    # Stage counts for pipeline velocity
    stage_counts = {
        "Applied": len([c for c in candidates if c["stage"] == "Applied"]),
        "Interviewing": len([c for c in candidates if c["stage"] == "Interviewing"]),
        "Technical Test": len(
            [c for c in candidates if c["stage"] == "Technical Test"]
        ),
        "Offered": len([c for c in candidates if c["stage"] == "Offered"]),
        "Rejected": len([c for c in candidates if c["stage"] == "Rejected"]),
    }
    total = len(candidates)
    offer_rate = round((stage_counts["Offered"] / total * 100), 1) if total > 0 else 0
    rejection_rate = (
        round((stage_counts["Rejected"] / total * 100), 1) if total > 0 else 0
    )

    # Avg scores
    interview_scores = [
        c["interview_score"] for c in candidates if c.get("interview_score") is not None
    ]
    tech_scores = [
        c["tech_score"] for c in candidates if c.get("tech_score") is not None
    ]
    avg_interview = (
        round(sum(interview_scores) / len(interview_scores), 1)
        if interview_scores
        else 0
    )
    avg_tech = round(sum(tech_scores) / len(tech_scores), 1) if tech_scores else 0

    return render_template(
        "analytics.html",
        recruiter_name=recruiter_name,
        stage_counts=stage_counts,
        total=total,
        offer_rate=offer_rate,
        rejection_rate=rejection_rate,
        avg_interview=avg_interview,
        avg_tech=avg_tech,
    )


@app.route("/settings")
def settings():
    recruiter_name = session.get("recruiter_name", "Recruiter")
    return render_template("settings.html", recruiter_name=recruiter_name)


# ── Candidate-facing pages ──────────────────────────────────────────────────────
@app.route("/candidate")
def candidate_page():
    return render_template("candidate.html")


# ── API endpoints ───────────────────────────────────────────────────────────────
@app.route("/api/recruiter-log", methods=["GET"])
def get_recruiter_log():
    return jsonify(load_recruiter_log())


# 1c3. POST /api/result — Student looks up their application status
@app.route("/api/result", methods=["POST"])
def check_result():
    data = request.json or {}
    name = (data.get("name") or "").strip()
    roll_number = (data.get("roll_number") or "").strip().upper()

    if not name or not roll_number:
        return jsonify({"error": "Both name and roll number are required."}), 400

    candidates = load_candidates()

    # Match on roll number AND name (case-insensitive name match for usability)
    matches = [
        c
        for c in candidates
        if c["roll_number"].upper() == roll_number
        and c["name"].strip().lower() == name.lower()
    ]

    if not matches:
        return (
            jsonify(
                {
                    "error": "No application found with that name and roll number. Please check your details and try again."
                }
            ),
            404,
        )

    # A student may have applied for multiple roles — return all matching applications
    results = []
    for c in matches:
        hide_scores = c["stage"] in ("Applied", "Interviewing")
        results.append(
            {
                "name": c["name"],
                "roll_number": c["roll_number"],
                "role": c["role"],
                "stage": c["stage"],
                "interview_score": None if hide_scores else c.get("interview_score"),
                "tech_score": None if hide_scores else c.get("tech_score"),
                "rejection_reason": (
                    c.get("rejection_reason") if c["stage"] == "Rejected" else None
                ),
            }
        )

    return jsonify({"results": results}), 200


# 1c. POST /api/apply — Student self-registration
@app.route("/api/apply", methods=["POST"])
def apply():
    data = request.json or {}
    name = (data.get("name") or "").strip()
    roll_number = (data.get("roll_number") or "").strip().upper()
    role = (data.get("role") or "").strip()

    if not name or not roll_number or not role:
        return (
            jsonify({"error": "Missing required fields: name, roll_number, or role"}),
            400,
        )

    if role not in VALID_ROLES:
        return (
            jsonify(
                {"error": f"Invalid role. Choose one of: {', '.join(VALID_ROLES)}"}
            ),
            400,
        )

    candidates = load_candidates()

    # Duplicate prevention: same roll number + same role
    duplicate = any(
        c["roll_number"].upper() == roll_number and c["role"] == role
        for c in candidates
    )
    if duplicate:
        return jsonify({"error": "You have already applied for this role."}), 409

    new_id = max([c["id"] for c in candidates], default=0) + 1
    new_candidate = {
        "id": new_id,
        "name": name,
        "roll_number": roll_number,
        "role": role,
        "stage": "Applied",
        "tech_score": None,
        "interview_score": None,
        "rejection_reason": None,
        "is_locked": False,
    }

    candidates.append(new_candidate)
    save_candidates(candidates)
    return (
        jsonify(
            {
                "message": "Application submitted successfully!",
                "candidate": new_candidate,
            }
        ),
        201,
    )


# 2. GET /api/candidates — Return all candidates from JSON
@app.route("/api/candidates", methods=["GET"])
def get_candidates():
    return jsonify(load_candidates())


# 3. POST /api/candidates — Add new candidate
@app.route("/api/candidates", methods=["POST"])
def add_candidate():
    data = request.json or {}
    name = data.get("name")
    roll_number = data.get("roll_number")
    role = data.get("role")

    if not name or not roll_number or not role:
        return (
            jsonify({"error": "Missing required fields: name, roll_number, or role"}),
            400,
        )

    candidates = load_candidates()

    # Auto-increment ID strategy
    new_id = max([c["id"] for c in candidates], default=0) + 1

    new_candidate = {
        "id": new_id,
        "name": name,
        "roll_number": roll_number,
        "role": role,
        "stage": "Applied",
        "tech_score": None,
        "interview_score": None,
        "rejection_reason": None,
        "is_locked": False,
    }

    candidates.append(new_candidate)
    save_candidates(candidates)
    return jsonify(new_candidate), 201


# 4. POST /api/candidates/<id>/move — Handle stage transition + gate logic
@app.route("/api/candidates/<int:cid>/move", methods=["POST"])
def move_candidate(cid):
    data = request.json or {}
    target_stage = data.get("target_stage")
    input_score = data.get("tech_score")  # used for Technical Test -> Offered/Rejected
    interview_score_input = data.get(
        "interview_score"
    )  # used for Interviewing -> Technical Test/Rejected

    candidates = load_candidates()
    candidate = next((c for c in candidates if c["id"] == cid), None)

    if not candidate:
        return jsonify({"error": "Candidate not found"}), 404

    VALID_STAGES = ["Applied", "Interviewing", "Technical Test", "Offered", "Rejected"]

    # --- RULE 4: Permanent Lock (checked first, before anything else) ---
    if candidate.get("is_locked", False):
        return (
            jsonify(
                {"error": "Candidate card is locked. No further movements allowed."}
            ),
            403,
        )

    if target_stage not in VALID_STAGES:
        return jsonify({"error": f"Invalid target_stage: {target_stage}"}), 400

    # --- GATE: Interviewing -> Technical Test (requires interview_score, threshold 50) ---
    if target_stage == "Technical Test":
        # Sequencing check: must come from Interviewing, cannot skip Interview
        if candidate["stage"] != "Interviewing":
            return (
                jsonify(
                    {
                        "error": "Candidate must complete the Interviewing stage before Technical Test."
                    }
                ),
                400,
            )

        if interview_score_input is None:
            return (
                jsonify(
                    {
                        "error": "Moving to Technical Test requires an interview_score (0-100)."
                    }
                ),
                400,
            )

        try:
            interview_score_int = int(interview_score_input)
            if interview_score_int < 0 or interview_score_int > 100:
                raise ValueError
        except (ValueError, TypeError):
            return (
                jsonify(
                    {"error": "Interview score must be an integer between 0 and 100."}
                ),
                400,
            )

        candidate["interview_score"] = interview_score_int

        # Auto-rejection: interview_score < 50
        if interview_score_int < 50:
            candidate["stage"] = "Rejected"
            candidate["is_locked"] = True
            candidate["rejection_reason"] = (
                f"Scored {interview_score_int} on the Interview (minimum required: 50)."
            )
            save_candidates(candidates)
            return (
                jsonify(
                    {
                        "message": "Candidate auto-rejected due to low interview score.",
                        "candidate": candidate,
                    }
                ),
                200,
            )

        candidate["stage"] = "Technical Test"
        save_candidates(candidates)
        return (
            jsonify(
                {"message": "Candidate updated successfully.", "candidate": candidate}
            ),
            200,
        )

    # --- GATE: Technical Test -> Offered/Rejected (requires tech_score, threshold 70) ---
    if target_stage == "Offered":
        # Sequencing check: must come from Technical Test
        if candidate["stage"] != "Technical Test":
            return (
                jsonify(
                    {
                        "error": "Candidate must complete the Technical Test stage before being Offered."
                    }
                ),
                400,
            )

        if input_score is None:
            return (
                jsonify({"error": "Moving to Offered requires a tech_score (0-100)."}),
                400,
            )

        try:
            score_int = int(input_score)
            if score_int < 0 or score_int > 100:
                raise ValueError
        except (ValueError, TypeError):
            return (
                jsonify(
                    {"error": "Technical score must be an integer between 0 and 100."}
                ),
                400,
            )

        candidate["tech_score"] = score_int

        # Auto-rejection: tech_score < 70
        if score_int < 70:
            candidate["stage"] = "Rejected"
            candidate["is_locked"] = True
            candidate["rejection_reason"] = (
                f"Scored {score_int} on the Technical Test (minimum required: 70)."
            )
            save_candidates(candidates)
            return (
                jsonify(
                    {
                        "message": "Candidate auto-rejected due to low technical score.",
                        "candidate": candidate,
                    }
                ),
                200,
            )

        candidate["stage"] = "Offered"
        save_candidates(candidates)
        return (
            jsonify(
                {"message": "Candidate updated successfully.", "candidate": candidate}
            ),
            200,
        )

    # Manual rejection from any stage
    if target_stage == "Rejected":
        candidate["stage"] = "Rejected"
        candidate["is_locked"] = True
        candidate["rejection_reason"] = "Manually rejected by recruiter."
        save_candidates(candidates)
        return jsonify({"message": "Candidate rejected.", "candidate": candidate}), 200

    # Normal moves: Applied <-> Interviewing
    candidate["stage"] = target_stage

    save_candidates(candidates)
    return (
        jsonify({"message": "Candidate updated successfully.", "candidate": candidate}),
        200,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
