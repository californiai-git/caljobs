import logging
import os
from serpapi import GoogleSearch

logger = logging.getLogger(__name__)

def fetch_jobs(target_roles: list[str], location: dict) -> list[dict]:
    """
    Uses SerpApi to search Google Jobs for each target role in the specified location.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        logger.warning("SERPAPI_KEY not found. Skipping web scraping.")
        return []
        
    scraped_jobs = []
    
    city = location.get("city", "Remote")
    allowed_types = location.get("allowed_types", ["remote", "hybrid"])
    
    for role in target_roles:
        logger.info(f"Scraping Google Jobs for: {role} in {city}")
        
        # Build search query (e.g. "software engineer remote")
        q = f"{role}"
        if "remote" in allowed_types and "remote" not in q.lower():
             q += " remote"
        else:
             q += f" in {city}"
             
        params = {
            "engine": "google_jobs",
            "q": q,
            "hl": "en",
            "api_key": api_key,
        }
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            jobs_results = results.get("jobs_results", [])
            
            for job in jobs_results:
                scraped_jobs.append({
                    "title": job.get("title", ""),
                    "company": job.get("company_name", ""),
                    "description": job.get("description", ""),
                    "location": job.get("location", ""),
                    "is_remote": "remote" in job.get("location", "").lower(),
                    "source": "Google Jobs (SerpApi)"
                })
        except Exception as e:
            logger.error(f"Failed to scrape Google Jobs for {role}: {e}")
            
    return scraped_jobs
