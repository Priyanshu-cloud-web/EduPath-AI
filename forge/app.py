
# app.py
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, json, os, time
from dotenv import load_dotenv
from openai import OpenAI
import fitz

# === Load .env ===
load_dotenv()

app = Flask(__name__)
app.secret_key = "edPath-2025"
DB = "edupath_job.db"
# === Create DB & Tables ===
def init_db():
    for _ in range(3):
        try:
            conn = sqlite3.connect(DB, timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.row_factory = sqlite3.Row
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT, cgpa TEXT, interests TEXT, skills TEXT,
                    resume_text TEXT, summary TEXT, gaps TEXT,
                    roadmap TEXT, keywords TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER,
                    type TEXT, data TEXT,
                    FOREIGN KEY(profile_id) REFERENCES profiles(id)
                );
            """)
            conn.close()
            print("DB ready.")
            return
        except:
            time.sleep(1)
    raise Exception("DB failed")

init_db()

# === Flask-Login ===
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id, email):
        self.id = id
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    try:
        with sqlite3.connect(DB) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT id, email FROM users WHERE id = ?", (user_id,)).fetchone()
            return User(row["id"], row["email"]) if row else None
    except:
        return None

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# === AI (FROM .env) ===
api_key = os.getenv("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")
client = OpenAI(api_key="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") if "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" else None
def ai_call(prompt, tokens=200):
    if not client:
        return "AI not configured. Add OPENAI_API_KEY to .env"
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=tokens
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"AI Error: {e}"

def extract_text_from_pdf(path):
    try:
        doc = fitz.open(path)
        text = " ".join(page.get_text() for page in doc)
        doc.close()
        return text
    except:
        return ""

# === ROUTES ===
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        if len(pw) < 6:
            flash("Password too short", "error")
        else:
            try:
                with get_db() as c:
                    c.execute("INSERT INTO users (email, password) VALUES (?, ?)",
                              (email, generate_password_hash(pw)))
                flash("Registered! Login now", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Email exists", "error")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        try:
            with get_db() as c:
                row = c.execute("SELECT id, password FROM users WHERE email = ?", (email,)).fetchone()
                if row and check_password_hash(row["password"], pw):
                    login_user(User(row["id"], email))
                    return redirect(url_for("index"))
                flash("Wrong credentials", "error")
        except:
            flash("Login failed", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "success")
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    summary = gaps = roadmap = ""
    courses = careers = jobs = []

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        cgpa = request.form.get("cgpa", "").strip() or "7.0"
        interests = request.form.get("interests", "").strip()
        skills = request.form.get("skills", "").strip()
        resume_text = ""

        if not name:
            flash("Name required", "error")
        else:
            if "resume" in request.files and request.files["resume"].filename.endswith(".pdf"):
                f = request.files["resume"]
                path = os.path.join("uploads", f.filename)
                f.save(path)
                resume_text = extract_text_from_pdf(path)
                os.remove(path)

            profile = f"CGPA: {cgpa}\nSkills: {skills}\nInterests: {interests}\nResume: {resume_text}"

            summary = ai_call(f"3-bullet student summary:\n{profile}", 150)
            gaps = ai_call(f"3 skill gaps with fixes:\n{profile}", 250)
            roadmap = ai_call(f"6-month roadmap:\n{profile}", 800)

            # Courses & Careers
            courses = ["Python for Data Science", "Machine Learning A-Z", "AWS Cloud Practitioner"]
            careers = ["Data Scientist", "ML Engineer", "Cloud Architect"]

            # FIXED - 5 Jobs
            jobs = [
                {"title": "Python Developer", "company": "TCS", "location": "Pune", "link": "https://naukri.com/python-developer-jobs"},
                {"title": "ML Engineer", "company": "Google", "location": "Bangalore", "link": "https://linkedin.com/jobs/ml-engineer-jobs"},
                {"title": "Data Scientist", "company": "Microsoft", "location": "Hyderabad", "link": "https://linkedin.com/jobs/data-scientist-jobs"},
                {"title": "Full Stack Developer", "company": "Amazon", "location": "Chennai", "link": "https://naukri.com/full-stack-developer-jobs"},
                {"title": "Cloud Engineer", "company": "Infosys", "location": "Delhi", "link": "https://linkedin.com/jobs/cloud-engineer-jobs"}
            ]

            try:
                with get_db() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO profiles (user_id, name, cgpa, interests, skills, resume_text, summary, gaps, roadmap, keywords)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (current_user.id, name, cgpa, interests, skills, resume_text, summary, gaps, roadmap, "python,ml,aws"))
                    pid = cur.lastrowid
                    for c in courses:
                        conn.execute("INSERT INTO recommendations (profile_id, type, data) VALUES (?, ?, ?)", (pid, 'course', json.dumps({"name": c})))
                    for c in careers:
                        conn.execute("INSERT INTO recommendations (profile_id, type, data) VALUES (?, ?, ?)", (pid, 'career', json.dumps({"name": c})))
                    for j in jobs:
                        conn.execute("INSERT INTO recommendations (profile_id, type, data) VALUES (?, ?, ?)", (pid, 'job', json.dumps(j)))
                flash("5 job matches generated!", "success")
            except:
                flash("Save failed", "error")

    return render_template("index.html", summary=summary, gaps=gaps, roadmap=roadmap, courses=courses, careers=careers, jobs=jobs)

def extract_text_from_pdf(path):
    if not os.path.exists(path):
        print("File not found:", path)
        return ""
    
    try:
        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
        print(f"Extracted {len(text)} chars from {path}")
        return text.strip()
    except Exception as e:
        print(f"PDF extraction failed: {e}")
        return ""



@app.route("/dashboard")
@login_required
def dashboard():
    try:
        with get_db() as c:
            total = c.execute("SELECT COUNT(*) FROM profiles WHERE user_id=?", (current_user.id,)).fetchone()[0]
            if total == 0:
                return render_template("dashboard.html", total_submissions=0, courses=[], careers=[], jobs=[], skill_labels=[], skill_data=[], recent_activities=[], goals=[], skill_breakdown=[])

            latest = c.execute("SELECT id, cgpa, skills FROM profiles WHERE user_id=? ORDER BY id DESC LIMIT 1", (current_user.id,)).fetchone()
            skills = [s.strip() for s in (latest["skills"] or "").split(",") if s.strip()]

            recs = c.execute("SELECT type, data FROM recommendations WHERE profile_id=?", (latest["id"],)).fetchall()
            courses = [json.loads(r["data"])["name"] for r in recs if r["type"] == "course"]
            careers = [json.loads(r["data"])["name"] for r in recs if r["type"] == "career"]
            jobs = [json.loads(r["data"]) for r in recs if r["type"] == "job"]

            skill_labels = skills[:5] or ["Python", "ML", "SQL"]
            skill_data = [70, 80, 90][:len(skill_labels)]

            recent = c.execute("SELECT name, timestamp FROM profiles WHERE user_id=? ORDER BY timestamp DESC LIMIT 3", (current_user.id,)).fetchall()
            recent_activities = [{"title": r["name"], "time": r["timestamp"][:16].replace("T", " ")} for r in recent]

            goals = [{"title": "Apply Jobs", "progress": min(total*30, 100)}]
            skill_breakdown = [{"name": s, "level": 75} for s in skills[:6]]

        return render_template("dashboard.html", total_submissions=total, courses=courses, careers=careers, jobs=jobs,
                               skill_labels=skill_labels, skill_data=skill_data, recent_activities=recent_activities,
                               goals=goals, skill_breakdown=skill_breakdown)
    except:
        flash("Try again", "error")
        return redirect(url_for("index"))

@app.route("/history")
@login_required
def history():
    try:
        with get_db() as c:
            profiles = c.execute("SELECT id, name, cgpa, timestamp, summary FROM profiles WHERE user_id=? ORDER BY timestamp DESC", (current_user.id,)).fetchall()
            data = []
            for p in profiles:
                recs = c.execute("SELECT type, data FROM recommendations WHERE profile_id=?", (p["id"],)).fetchall()
                data.append({
                    "name": p["name"], "cgpa": p["cgpa"], "timestamp": p["timestamp"],
                    "summary": p["summary"], "recs": [(r["type"], json.loads(r["data"])) for r in recs]
                })
        return render_template("history.html", history=data)
    except:
        flash("History error", "error")
        return redirect(url_for("index"))


# Add to imports
from apify_client import ApifyClient

# In your code (after load_dotenv())
apify_client = ApifyClient(os.getenv("https://api.apify.com/v2/users/admirable_lunar"))

def fetch_real_linkedin_jobs(keywords, limit=5):
    try:
        run_input = {
            "keywords": keywords,
            "location": "India",
            "limit": limit
        }
        run = apify_client.actor("Vetal8/linkedin-jobs-scraper").call(run_input=run_input)
        jobs = []
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            jobs.append({
                "title": item.get("title", "Job Title"),
                "company": item.get("company", "Company"),
                "location": item.get("location", "India"),
                "link": item.get("jobUrl", "#")
            })
        return jobs
    except Exception as e:
        print(f"Apify error: {e}")
        return fallback_jobs(keywords)

def fallback_jobs(keywords):
    return [
        {"title": f"{keywords} Developer", "company": "TCS", "location": "Pune", "link": "https://naukri.com"},
        {"title": f"{keywords} Engineer", "company": "Google", "location": "Bangalore", "link": "https://linkedin.com/jobs"}
    ]

# === Run ===
if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    app.run(debug=True, threaded=True)