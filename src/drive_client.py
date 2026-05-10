import os
from datetime import datetime
import json
import logging
import io
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from .auth_utils import get_service

logger = logging.getLogger(__name__)

def get_caljobs_folder_id(service) -> str:
    """Gets the ID of the 'caljobs' folder in Drive, creating it if it doesn't exist."""
    query = "name='caljobs' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id)", spaces='drive').execute()
    items = results.get('files', [])
    if items:
        return items[0]['id']
        
    logger.info("Creating 'caljobs' root folder in Google Drive...")
    folder_metadata = {
        'name': 'caljobs',
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')

def get_available_personas(profile_name: str) -> dict[str, str]:
    """
    Scans Google Drive for files matching '{profile_name}_*.docx'.
    Parses the filename (e.g., sreelata_de_java-developer_cloud-architect.docx)
    Returns a dict mapping role -> base filename.
    e.g. {"java developer": "sreelata_de_java-developer_cloud-architect", "cloud architect": "sreelata_de..."}
    """
    try:
        service = get_service('drive', 'v3')
        folder_id = get_caljobs_folder_id(service)
        # Fetch all docx files and filter in Python to avoid case-sensitivity issues
        query = f"'{folder_id}' in parents and name contains '.docx' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)", spaces='drive').execute()
        items = results.get('files', [])
        
        role_map = {}
        for item in items:
            name = item.get('name', '')
            name_lower = name.lower()
            profile_lower = profile_name.lower()
            if name_lower.startswith(f"{profile_lower}_") and name_lower.endswith(".docx"):
                base_name = name.replace(".docx", "")
                roles_str = name_lower.replace(f"{profile_lower}_", "").replace(".docx", "")
                # roles_str: "java-developer_cloud-architect_security"
                file_roles = roles_str.split("_")
                for r in file_roles:
                    human_role = r.replace("-", " ")
                    role_map[human_role] = base_name
        
        if role_map:
            logger.info(f"Dynamically discovered personas: {list(role_map.keys())}")
        else:
            logger.warning(f"No personas found for profile '{profile_name}' in Google Drive.")
        return role_map
    except Exception as e:
        logger.error(f"Failed to fetch personas from Drive: {e}")
        return []

def download_base_cv(template_name: str) -> str | None:
    """
    Searches Google Drive for '{profile_name}.docx' and downloads it locally.
    Returns the local path if successful, None otherwise.
    """
    try:
        service = get_service('drive', 'v3')
        folder_id = get_caljobs_folder_id(service)
        file_name = f"{template_name}.docx"
        query = f"'{folder_id}' in parents and name='{file_name}' and trashed=false"
        
        results = service.files().list(q=query, fields="files(id, name)", spaces='drive').execute()
        items = results.get('files', [])
        
        if not items:
            logger.warning(f"Could not find {file_name} in Google Drive.")
            return None
            
        file_id = items[0]['id']
        request = service.files().get_media(fileId=file_id)
        
        local_path = file_name
        with io.FileIO(local_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                
        logger.info(f"Successfully downloaded {file_name} from Google Drive.")
        return local_path
        
    except Exception as e:
        logger.error(f"Failed to download Base CV from Drive: {e}")
        return None

def create_daily_folder(service) -> str:
    """
    Creates a new folder with today's date inside the 'caljobs' folder in Google Drive.
    """
    parent_id = get_caljobs_folder_id(service)
    today_str = datetime.now().strftime("%Y-%m-%d")
    folder_metadata = {
        'name': f"Job_Applications_{today_str}",
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    folder_id = folder.get('id')
    logger.info(f"Created daily Drive folder: {folder_metadata['name']} (ID: {folder_id})")
    return folder_id

def upload_results(results: dict):
    """
    Creates a daily folder and uploads all generated CVs and a summary JSON.
    """
    logger.info("Uploading results to Google Drive...")
    
    try:
        service = get_service('drive', 'v3')
        
        # 1. Create the daily folder inside 'caljobs'
        daily_folder_id = create_daily_folder(service)
        
        # 2. Save a summary JSON file locally
        summary_path = "daily_summary.json"
        with open(summary_path, "w") as f:
            json.dump(results, f, indent=2)
            
        # 3. Upload the summary JSON
        file_metadata = {
            'name': 'daily_summary.json',
            'parents': [daily_folder_id]
        }
        media = MediaFileUpload(summary_path, mimetype='application/json')
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        # 4. Upload all generated CVs and convert to PDF
        jobs = results.get("daily_jobs", [])
        for job_data in jobs:
            cv_path = job_data.get("generated_cv")
            if cv_path and os.path.exists(cv_path):
                file_name = os.path.basename(cv_path)
                
                # Upload as a Google Doc for easy conversion
                doc_metadata = {
                    'name': file_name.replace('.docx', ''),
                    'parents': [daily_folder_id],
                    'mimeType': 'application/vnd.google-apps.document'
                }
                media = MediaFileUpload(cv_path, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                uploaded_doc = service.files().create(body=doc_metadata, media_body=media, fields='id').execute()
                doc_id = uploaded_doc.get('id')
                logger.info(f"Uploaded {file_name} as Google Doc.")
                
                # Export the Google Doc as a PDF
                request = service.files().export_media(fileId=doc_id, mimeType='application/pdf')
                pdf_path = cv_path.replace('.docx', '.pdf')
                
                with io.FileIO(pdf_path, 'wb') as fh:
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                
                # Upload the PDF to the same folder
                pdf_metadata = {
                    'name': file_name.replace('.docx', '.pdf'),
                    'parents': [daily_folder_id]
                }
                pdf_media = MediaFileUpload(pdf_path, mimetype='application/pdf')
                service.files().create(body=pdf_metadata, media_body=pdf_media, fields='id').execute()
                logger.info(f"Generated and uploaded PDF version.")
                
        logger.info("Finished uploading all files and PDFs to Drive.")
        
    except Exception as e:
        logger.error(f"Failed to upload to Drive: {e}")
