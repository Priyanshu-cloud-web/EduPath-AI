from flask import Flask, render_template, request, flash, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, json, os, time
from dotenv import load_dotenv
from openai import OpenAI
import fitz

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


# load_dotenv() 
# client = OpenAI(
#     api_key=os.getenv("OPENAI_API_KEY")
# )

# def ai_call(prompt, tokens=200):
#     if not client:
#         return "AI not configured. Add OPENAI_API_KEY to .env"
#     try:
#         resp = client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[{"role": "user", "content": prompt}],
#             max_tokens=tokens
#         )
#         return resp.choices[0].message.content.strip()
#     except Exception as e:
#         return f"AI Error: {e}"


from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key="OPENAI_API_KEY") if "OPENAI_API_KEY" else None

def ai_call(prompt, tokens=200):
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=tokens
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"AI Error: {e}"



# def ai_call(prompt, tokens=300):
#     global client
#     if client is None:
#         return "⚠️ AI not available: Please add your OpenAI API key to the .env file."

#     try:
#         resp = client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[{"role": "user", "content": prompt}],
#             max_tokens=tokens,
#             temperature=0.7,
#             timeout=30
#         )
#         return resp.choices[0].message.content.strip()
#     except Exception as e:
#        if "401" in str(e) or "invalid_api_key" in str(e):
#           return "Invalid OpenAI API key. Please get a new one from platform.openai.com and update .env"
#        return f"AI Error: {str(e)}"

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

from flask import render_template, redirect, url_for, flash, session
from flask_login import login_required, current_user
import sqlite3


@app.route("/resume-builder")
@login_required
def resume_builder():
    template = request.args.get('template', 'classic')  # Default: classic

    try:
        with get_db() as conn:
            profile = conn.execute("""
                SELECT name, cgpa, skills, interests, resume_text 
                FROM profiles WHERE user_id = ? ORDER BY id DESC LIMIT 1
            """, (current_user.id,)).fetchone()
        
        if not profile:
            flash("Submit a profile first", "error")
            return redirect(url_for("index"))

        data = f"Name: {profile['name']}\nCGPA: {profile['cgpa']}\nSkills: {profile['skills']}\nInterests: {profile['interests']}\nResume: {profile['resume_text']}"

        # Base prompt
        base_prompt = """
Create a professional, ATS-friendly resume in clean text format.
Include:
- Full Name
- Contact (placeholder)
- Education with CGPA
- Skills
- Projects/Experience
Keep it concise.
        """

        # Template-specific prompts
        templates = {
            "classic": base_prompt + " Use traditional, formal language and structure.",
            "modern": base_prompt + " Use modern, clean language with strong action verbs.",
            "compact": base_prompt + " Make it very concise, one-page style, focus on impact.",
            "creative": base_prompt + " Use engaging language with storytelling elements, suitable for design/tech roles."
        }

        ai_resume = ai_call(templates.get(template, templates["classic"]) + "\n\n" + data, 600)

        # Fallback
        if "AI Error" in ai_resume or not ai_resume.strip():
            ai_resume = f"""
**{profile["name"]}**

email@example.com | +91-9876543210 | linkedin.com/in/yourprofile

**EDUCATION**
B.Tech - CGPA: {profile["cgpa"]}

**SKILLS**
• {profile["skills"] or "Python, ML, AWS"}

**EXPERIENCE**
• Add your projects and achievements
            """

        return render_template("resume.html", resume=ai_resume, template=template)

    except Exception as e:
        print(f"Resume error: {e}")
        flash("Resume generation failed", "error")
        return redirect(url_for("index"))


@app.route("/resume-form", methods=["GET", "POST"])
@login_required
def resume_form():
    # Default empty data
    form_data = {
        "name": "", "email": "", "phone": "", "linkedin": "",
        "education": "", "cgpa": "", "skills": "", "projects": "",
        "experience": "", "certifications": "", "summary": ""
    }

    if request.method == "POST":
        # Collect submitted data
        form_data = {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "linkedin": request.form.get("linkedin", "").strip(),
            "education": request.form.get("education", "").strip(),
            "cgpa": request.form.get("cgpa", "").strip(),
            "skills": request.form.get("skills", "").strip(),
            "projects": request.form.get("projects", "").strip(),
            "experience": request.form.get("experience", "").strip(),
            "certifications": request.form.get("certifications", "").strip(),
            "summary": request.form.get("summary", "").strip()
        }

        # Save to resumes table (optional)
        try:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO resumes 
                    (user_id, name, email, phone, linkedin, education, cgpa, skills, projects, experience, certifications, summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    current_user.id,
                    form_data["name"], form_data["email"], form_data["phone"], form_data["linkedin"],
                    form_data["education"], form_data["cgpa"], form_data["skills"],
                    form_data["projects"], form_data["experience"], form_data["certifications"], form_data["summary"]
                ))
        except Exception as e:
            print(f"Save error: {e}")

        # === PROFESSIONAL RESUME PROMPT ===
        prompt = f"""
Create a highly professional, ATS-friendly resume in clean text format for a Computer Science fresher in India.

Use ONLY bold uppercase letters for ALL headings (no asterisks, no italics, no markdown).
Use standard bullets (•) for lists.
Keep everything plain text — no tables, no graphics.

Exact structure:

**{form_data['name'].upper()}**

Email: {form_data['email']} | Phone: {form_data['phone']} | LinkedIn/GitHub: {form_data['linkedin']}

**PROFESSIONAL SUMMARY**
3-4 lines highlighting skills, passion, and career goal. Sound natural and confident.

**TECHNICAL SKILLS**
Group into categories:
• Languages: Python, Java, etc.
• Frameworks/Libraries: React, Django, etc.
• Tools & Technologies: Git, AWS, Docker, etc.

**EDUCATION**
{form_data['education']}
CGPA: {form_data['cgpa']}/10

**PROJECTS**
• Project Title
  Description with tech stack and impact (use numbers like "improved performance by 40%")

• Project Title
  ...

**EXPERIENCE / INTERNSHIPS** (if any)
Company Name - Role (Duration)
• Achievement 1
• Achievement 2

**CERTIFICATIONS**
• Certification Name - Issuer

**ACHIEVEMENTS**
• Hackathon wins, LeetCode ranking, etc.

Make it concise (1 page), use strong action verbs (Developed, Built, Optimized), quantify achievements.
Sound human-written — vary sentence structure, avoid generic phrases.

Data:
Name: {form_data['name']}
Email: {form_data['email']}
Phone: {form_data['phone']}
LinkedIn: {form_data['linkedin']}
Education: {form_data['education']} (CGPA: {form_data['cgpa']})
Skills: {form_data['skills']}
Projects: {form_data['projects']}
Experience: {form_data['experience']}
Certifications: {form_data['certifications']}
Summary hint: {form_data['summary']}
"""

        ai_resume = ai_call(prompt, 700)

        # Fallback if AI fails
        if "AI Error" in ai_resume or not ai_resume.strip():
            ai_resume = f"""**{form_data['name'].upper()}**

Email: {form_data['email']} | Phone: {form_data['phone']} | LinkedIn: {form_data['linkedin']}

**PROFESSIONAL SUMMARY**
Aspiring software engineer with strong foundation in programming and problem-solving.

**TECHNICAL SKILLS**
• Languages: {form_data['skills'] or 'Python, Java'}
• Tools: Git, VS Code

**EDUCATION**
{form_data['education']}
CGPA: {form_data['cgpa']}/10

**PROJECTS**
{form_data['projects'] or '• Add your projects here'}

**EXPERIENCE / INTERNSHIPS**
{form_data['experience'] or 'None'}

**CERTIFICATIONS**
{form_data['certifications'] or 'None'}

**ACHIEVEMENTS**
• Strong academic performance
"""

        # Save to session for download
        session["latest_resume"] = ai_resume

        return render_template("resume.html", resume=ai_resume, name=form_data["name"])

    # GET request - Auto-fill from latest profile
    try:
        with get_db() as conn:
            profile = conn.execute("""
                SELECT name, cgpa, skills, interests, resume_text 
                FROM profiles WHERE user_id = ? ORDER BY id DESC LIMIT 1
            """, (current_user.id,)).fetchone()

            if profile:
                form_data.update({
                    "name": profile["name"] or "",
                    "cgpa": profile["cgpa"] or "",
                    "skills": profile["skills"] or "",
                    "projects": profile["resume_text"] or "",
                    "experience": profile["resume_text"] or "",
                    "education": "B.Tech in Computer Science\nYour College Name\n2022 - 2026"
                })
    except Exception as e:
        print(f"Auto-fill error: {e}")

    return render_template("resume_form.html", data=form_data)



from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io
@app.route("/download-resume")
@login_required
def download_resume():
    resume_text = session.get("latest_resume")

    if not resume_text:
        flash("No resume available to download.", "error")
        return redirect(url_for("index"))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    story = []
    for line in resume_text.split("\n"):
        story.append(Paragraph(line.replace("&", "&amp;"), styles["Normal"]))

    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="resume.pdf",
        mimetype="application/pdf"
    )


@app.route("/skill-quiz", methods=["GET", "POST"])
@login_required
def skill_quiz():
    if request.method == "POST":
        user_skills = request.form.get("user_skills", "").strip()
        if not user_skills:
            flash("Please enter at least one skill", "error")
            return redirect(url_for("skill_quiz"))

        skills_list = [s.strip() for s in user_skills.split(",") if s.strip()]

        # Generate questions
        questions = []
        for skill in skills_list:
            questions.append({
                "skill": skill,
                "question": f"How confident are you with {skill.capitalize()}?"
            })

        # Save for result
        session["quiz_skills"] = skills_list
        session["quiz_questions"] = questions

        return render_template("skill_quiz_dynamic.html", questions=questions)

    return render_template("skill_quiz_input.html")

# @app.route("/skill-quiz-result", methods=["POST"])
# @login_required
# def skill_quiz_result():
#     skills = session.get("quiz_skills", [])
#     if not skills:
#         flash("No skills found", "error")
#         return redirect(url_for("skill_quiz"))

#     scores = {}
#     for skill in skills:
#         score = int(request.form.get(skill, 1))
#         scores[skill] = score

#     gaps = [skill for skill, score in scores.items() if score <= 3]
#     strong = [skill for skill, score in scores.items() if score >= 4]

#     gaps_text = ai_call(f"Suggest 3 ways to improve these skills in 3 months: {', '.join(gaps)}", 300) if gaps else "No major skill gaps — great job!"
#     strong_text = ai_call(f"Highlight how to leverage these strengths: {', '.join(strong)}", 200) if strong else "Keep building your skills!"

#     return render_template("quiz_result.html", gaps=gaps_text, strong=strong_text, scores=scores, skills=skills)

@app.route("/skill-quiz-result", methods=["POST"])
@login_required
def skill_quiz_result():
    skills = session.get("quiz_skills", [])
    if not skills:
        flash("No skills found", "error")
        return redirect(url_for("skill_quiz"))

    scores = {}
    for skill in skills:
        score = int(request.form.get(skill, 3))  # default intermediate
        scores[skill] = score

    # Advanced thresholds
    strong = [s for s, sc in scores.items() if sc >= 4]
    gaps = [s for s, sc in scores.items() if sc <= 2]

    # AI feedback
    strong_text = ai_call(f"Leverage these strengths for career growth: {', '.join(strong)}", 250) if strong else ""
    gaps_text = ai_call(f"3-month improvement plan with courses/projects for gaps: {', '.join(gaps)}", 400) if gaps else ""
    recommendations = ai_call(f"Suggest 3 free/paid courses + projects for overall skills: {', '.join(skills)}", 300)

    return render_template("quiz_result.html",
                           strong_text=strong_text or "Balanced profile — focus on specialization",
                           gaps_text=gaps_text or "Strong foundation — maintain with advanced challenges",
                           recommendations=recommendations,
                           scores=scores,
                           skills=skills)

# === Run ===
if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)


    app.run(debug=True, threaded=True)
