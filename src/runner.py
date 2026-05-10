from .scraper import fetch_jobs
from .gmail_client import check_inbox, send_summary_email
from .drive_client import upload_results
import yaml

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def run_all():
    config = load_config()
    
    # 1. Fetch Jobs
    jobs = fetch_jobs(config["search"]["keywords"], config["search"]["location"])
    
    # 2. Check Inbox
    emails = check_inbox(config["email"]["query_filter"])
    
    # 3. Save to Drive
    upload_results({"jobs": jobs, "emails": emails}, config["drive"]["folder_id"])
    
    # 4. Send Email
    send_summary_email(config["email"]["address"], jobs, emails)
    print("Run complete.")
