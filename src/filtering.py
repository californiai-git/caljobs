import logging
import json
import os
from google import genai
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class JobEvaluation(BaseModel):
    is_real_job: bool = Field(description="True if this is a legitimate job posting, False if it looks like a scam, MLM, or fake.")
    matches_role: bool = Field(description="True if the job aligns with any of the user's target roles.")
    matched_role_name: str = Field(description="The exact name of the target role this matches (e.g. 'hr', 'ux_design', 'administrative_assistant'). Empty if no match.")
    reason: str = Field(description="A brief sentence explaining the reasoning.")

class JobFilterEngine:
    def __init__(self, config):
        self.config = config
        self.target_roles = [r.lower() for r in config.get("search", {}).get("roles", [])]
        self.target_location = config.get("search", {}).get("location", {})
        
        # Initialize Gemini Client
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found in environment. Filtering will fail.")
        self.client = genai.Client(api_key=api_key)
        
    def evaluate_job_with_ai(self, job_posting: dict) -> dict:
        """
        Uses Gemini 1.5 Pro to intelligently evaluate the job posting.
        """
        title = job_posting.get("title", "")
        description = job_posting.get("description", "")
        company = job_posting.get("company", "")
        
        prompt = f"""
        You are an expert technical recruiter and security analyst. Evaluate the following job posting.
        
        Target Roles: {self.target_roles}
        
        Job Title: {title}
        Company: {company}
        Description: {description}
        
        Evaluate:
        1. Is this a legitimate job? Look out for MLM schemes, "be your own boss", pay-to-work scams, or extreme lack of detail.
        2. Does this job match any of the Target Roles listed above? 
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': JobEvaluation,
                },
            )
            # Parse the JSON response
            evaluation = json.loads(response.text)
            return evaluation
        except Exception as e:
            logger.error(f"Gemini API evaluation failed: {e}")
            # Fallback
            return {"is_real_job": False, "matches_role": False, "matched_role_name": "", "reason": "API Error"}

    def matches_location(self, job_posting: dict) -> bool:
        """
        Validates location constraints (e.g., Remote or within 10 miles of Fremont, CA).
        Bypasses strict location filtering for jobs coming directly from Gmail.
        """
        if "gmail" in job_posting.get("source", "").lower() or "email" in job_posting.get("source", "").lower():
            return True
            
        title = job_posting.get("title", "").lower()
        location_str = job_posting.get("location", "").lower()
        is_remote = job_posting.get("is_remote", False) or "remote" in title or "remote" in location_str or "anywhere" in location_str
        
        allowed_types = [t.lower() for t in self.target_location.get("allowed_types", ["remote", "hybrid", "in-person"])]
        
        if is_remote and "remote" in allowed_types:
            return True
            
        target_city = self.target_location.get("city", "fremont").lower()
        
        if target_city in location_str or target_city in title:
             if "hybrid" in location_str and "hybrid" in allowed_types:
                 return True
             if "in-person" in allowed_types:
                 return True
             # If target city matches, and no specific type is required, or it's implicitly in-person
             return True
                 
        return False

    def filter_jobs(self, jobs: list[dict]) -> list[dict]:
        """
        Runs all filters over a list of job postings.
        """
        valid_jobs = []
        for job in jobs:
            # 1. First check location (fast and cheap)
            if not self.matches_location(job):
                logger.info(f"Filtered out job due to location: {job.get('title')}")
                continue
                
            # 2. Use AI to evaluate if it's real and matches roles
            logger.info(f"Using AI to evaluate: {job.get('title')}...")
            evaluation = self.evaluate_job_with_ai(job)
            
            if not evaluation.get("is_real_job"):
                logger.info(f"AI Filtered out fake job: {job.get('title')}. Reason: {evaluation.get('reason')}")
                continue
            
            if not evaluation.get("matches_role"):
                logger.info(f"AI Filtered out due to role mismatch: {job.get('title')}. Reason: {evaluation.get('reason')}")
                continue
                
            # Attach the specific matched role so the CV Generator knows which Base CV to grab!
            job["matched_role"] = evaluation.get("matched_role_name", "")
            valid_jobs.append(job)
            
        return valid_jobs
