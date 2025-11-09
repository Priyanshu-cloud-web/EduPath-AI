# EduPath-AI
EduPath AI is an intelligent Flask-based web application that helps students explore personalized learning and career paths using AI-powered recommendations. It analyzes a student’s academic profile, interests, skills, and resume to generate a profile summary, identify skill gaps, and build a 6-month action roadmap for growth.

🚀 Features

🔐 User Authentication — Secure registration and login with Flask-Login and password hashing

🧠 AI-Generated Insights — Uses OpenAI GPT models to:

Summarize student profiles

Identify missing skills

Generate actionable 6-month career roadmaps

📄 Resume Analysis — Extracts and interprets text from uploaded PDFs using PyMuPDF (fitz)

📊 Personal Dashboard — Tracks progress, skills, and recommendations visually

💾 SQLite Database — Stores users, profiles, and AI recommendations

🌱 Skill-Based Recommendations — Suggests relevant courses, careers, and job roles

🛠️ Tech Stack

Backend: Flask (Python)

Frontend: HTML, CSS, Jinja2 templates

Database: SQLite

AI Engine: OpenAI GPT (via openai library)

Env Management: python-dotenv

Authentication: Flask-Login + Werkzeug

⚙️ Setup Instructions

Clone the repository

git clone https://github.com/yourusername/edupath-ai.git
cd edupath-ai


Install dependencies

pip install -r requirements.txt


Create a .env file in the root directory:

OPENAI_API_KEY=sk-your-api-key-here


Run the Flask app

python app.py


Visit http://localhost:5000
 in your browser.


🧑‍💻 Author

Developed by Priyanshu
