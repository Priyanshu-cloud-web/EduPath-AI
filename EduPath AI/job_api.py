# job_api.py - Now returns static hardcoded jobs
def fetch_linkedin_jobs(keywords, rows=10):
    # Hardcoded dummy jobs
    jobs = []
    for i in range(min(rows, 5)):  # Limit to 5 for simplicity
        jobs.append({
            "title": f"Software Engineer {i+1}",
            "companyName": f"Tech Company {i+1}",
            "location": "Remote",
            "link": f"https://linkedin.com/jobs/dummy{i+1}"
        })
    return jobs

def fetch_naukri_jobs(keywords, rows=10):
    # Hardcoded dummy jobs
    jobs = []
    for i in range(min(rows, 5)):
        jobs.append({
            "title": f"Developer {i+1}",
            "companyName": f"India Tech {i+1}",
            "location": "Bangalore",
            "url": f"https://naukri.com/jobs/dummy{i+1}"
        })
    return jobs