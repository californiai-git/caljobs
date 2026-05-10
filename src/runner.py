from .scraper import fetch_jobs
from .gmail_client import check_inbox, send_summary_email
from .drive_client import upload_results, download_base_cv
from .filtering import JobFilterEngine
from .cv_generator import CVGenerator
import yaml
import os
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def load_candidates():
    if not os.path.exists("candidates.yaml"):
        logger.warning("candidates.yaml not found. Falling back to candidates.example.yaml")
        with open("candidates.example.yaml", "r") as f:
            return yaml.safe_load(f).get("clients", [])
    with open("candidates.yaml", "r") as f:
        return yaml.safe_load(f).get("clients", [])

def process_profile(config, profile_data):
    profile_name = profile_data.get("id")
    logger.info(f"--- Processing profile: {profile_name} ---")
    
    # Configure for this specific profile
    config["search"] = {"location": profile_data.get("location", {})}
    
    # Fetch dynamic roles from Google Drive filenames
    from .drive_client import get_available_personas
    dynamic_roles_map = get_available_personas(profile_name)
    if dynamic_roles_map:
        config["search"]["roles"] = list(dynamic_roles_map.keys())
        config.setdefault("workflow", {})["role_map"] = dynamic_roles_map
    else:
        logger.warning(f"No roles found for {profile_name}. Skipping.")
        return []
        
    filter_engine = JobFilterEngine(config)
    
    jobs_to_process = []
    
    # 1. Fetch Jobs from Web Scraper
    # We always use the scraper now.
    logger.info(f"Scraping jobs via SerpApi...")
    custom_instructions = profile_data.get("custom_instructions", "")
    scraped_jobs = fetch_jobs(config["search"].get("roles", []), profile_data.get("location"), custom_instructions)
    jobs_to_process.extend(scraped_jobs)
    
    # 2. Check Emails if enabled
    if profile_data.get("check_gmail_inbox"):
        logger.info("Checking Gmail inbox for jobs...")
        email_jobs = check_inbox(config.get("email", {}).get("query_filter", ""))
        jobs_to_process.extend(email_jobs)
        
    # 3. Filter Jobs
    valid_jobs = filter_engine.filter_jobs(jobs_to_process)
    
    # 4. Generate CVs
    generator = CVGenerator(config)
    generator.profile_name = profile_name  # Ensure generator uses current profile
    for job in valid_jobs:
        if config.get("workflow", {}).get("generate_cv", True):
            cv_path = generator.generate_for_job(job)
            job["generated_cv"] = cv_path
            
    return valid_jobs

def run_all():
    load_dotenv()
    config = load_config()
    profiles = load_candidates()
    
    all_valid_jobs = []
    for profile in profiles:
        jobs = process_profile(config, profile)
        all_valid_jobs.extend(jobs)
    
    # Upload everything to Drive
    if config.get("workflow", {}).get("upload_to_drive", True):
        logger.info("Uploading results to Google Drive...")
        upload_results({"daily_jobs": all_valid_jobs})
    
    # 6. Send Email Summary
    if all_valid_jobs:
        send_summary_email(config["email"]["address"], all_valid_jobs, [])
        
    logger.info("Daily job search workflow complete.")
