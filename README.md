# CalJobs Agent

This is an autonomous job-search agent that:
1. Searches for California-based job postings.
2. Checks the `sreelatade@gmail.com` inbox for job-related emails.
3. Compiles a summary and saves it to Google Drive.
4. Emails a report to you.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up Google API credentials:
   - Go to Google Cloud Console.
   - Enable Gmail API and Google Drive API.
   - Download OAuth 2.0 Client IDs as `credentials.json` and place it in the root directory.
3. Run the setup to authenticate:
   ```bash
   python -m src.cli --setup
   ```
4. Run the agent:
   ```bash
   python -m src.cli --run
   ```
