import logging
import os
import json
from serpapi import GoogleSearch
from google import genai
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class SearchQueries(BaseModel):
    queries: list[str]

def generate_search_queries(role: str, location: dict, custom_instructions: str) -> list[str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return [f"{role} {location.get('city', '')}"]
    try:
        client = genai.Client(api_key=api_key)
        prompt = f"Generate exactly 2 highly optimized Google Jobs search queries for a '{role}' role in '{location.get('city', '')}'. Allowed work types: {location.get('allowed_types')}. Extra Preferences: {custom_instructions}. Make the queries concise."
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': SearchQueries,
            }
        )
        data = json.loads(response.text)
        return data.get("queries", [role])
    except Exception as e:
        logger.error(f"Failed to generate queries with Gemini: {e}")
        return [role]

def fetch_jobs(target_roles: list[str], location: dict, custom_instructions: str = "") -> list[dict]:
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
        logger.info(f"Generating AI search queries for: {role}")
        queries = generate_search_queries(role, location, custom_instructions)
        
        for q in queries:
            logger.info(f"Scraping Google Jobs for query: '{q}'")
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
