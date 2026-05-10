import os
import logging
import json
from docxtpl import DocxTemplate
from google import genai
from pydantic import BaseModel, Field
from .drive_client import download_base_cv

logger = logging.getLogger(__name__)

class TailoredContext(BaseModel):
    tailored_objective: str = Field(description="A professional, 2-sentence objective summary tailored to this exact company and role.")
    dynamic_skills: str = Field(description="A comma-separated list of 5-7 core skills explicitly mentioned in the job description that the candidate likely possesses.")
    tailored_bullet_1: str = Field(description="A highly relevant, achievement-oriented bullet point for the most recent job experience.")
    tailored_bullet_2: str = Field(description="A second highly relevant, achievement-oriented bullet point for the most recent job experience.")

class CVGenerator:
    def __init__(self, config):
        self.config = config
        self.profile_name = config.get("workflow", {}).get("profile_name", "sreelatade")
        self.output_dir = "generated_cvs"
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None

    def _generate_tailored_context_with_ai(self, job_posting: dict) -> dict:
        """
        Uses Gemini to read the job posting and generate tailored content for the CV.
        """
        if not self.client:
            return {
                "tailored_objective": "Experienced professional seeking a new opportunity.",
                "dynamic_skills": "Communication, Teamwork, Problem Solving",
                "tailored_bullet_1": "Managed daily operations and projects.",
                "tailored_bullet_2": "Collaborated with team members to achieve goals."
            }

        prompt = f"""
        You are an expert resume writer. Generate highly tailored content for a CV.
        
        Job Title: {job_posting.get('title')}
        Company: {job_posting.get('company')}
        Description: {job_posting.get('description')}
        
        Based ONLY on the job description, generate an objective, core skills, and two achievement bullet points that make the candidate look like a perfect fit.
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-1.5-pro',
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': TailoredContext,
                },
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Failed to generate tailored context: {e}")
            return {
                "tailored_objective": "Experienced professional seeking a new opportunity.",
                "dynamic_skills": "Communication, Teamwork, Problem Solving",
                "tailored_bullet_1": "Managed daily operations and projects.",
                "tailored_bullet_2": "Collaborated with team members to achieve goals."
            }

    def generate_for_job(self, job_posting: dict) -> str | None:
        """
        Downloads the role-specific Base CV, uses AI to generate tailored content,
        and saves a new Word document. Returns the path to the generated CV.
        """
        matched_role = job_posting.get("matched_role")
        if not matched_role:
            logger.warning(f"No matched role for {job_posting.get('title')}. Skipping CV generation.")
            return None

        # 1. Look up the exact template name from the dynamically fetched map
        role_map = self.config.get("workflow", {}).get("role_map", {})
        template_name = role_map.get(matched_role)
        
        if not template_name:
            # Fallback if map isn't populated
            matched_role_safe = matched_role.lower().replace(" ", "-")
            template_name = f"{self.profile_name}_{matched_role_safe}"
        
        # 2. Download that specific template from Google Drive
        base_cv_path = download_base_cv(template_name)
        
        if not base_cv_path or not os.path.exists(base_cv_path):
            logger.warning(f"Role-specific template '{template_name}.docx' not found in Drive. Skipping CV generation.")
            return None

        try:
            doc = DocxTemplate(base_cv_path)
            
            # 3. Use AI to generate tailored bullet points
            ai_context = self._generate_tailored_context_with_ai(job_posting)
            
            # 4. Merge standard data with AI data
            context = {
                "job_title": job_posting.get("title", "Candidate"),
                "company_name": job_posting.get("company", "the company"),
                **ai_context
            }
            
            doc.render(context)
            
            # 5. Save the final file
            company = job_posting.get("company", "Unknown").replace(" ", "_")
            role = job_posting.get("title", "Role").replace(" ", "_").replace("/", "-")
            output_filename = f"{self.profile_name}_{company}_{role}.docx"
            output_path = os.path.join(self.output_dir, output_filename)
            
            doc.save(output_path)
            logger.info(f"Successfully generated AI-tailored CV for {company} at {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate CV: {e}")
            return None
