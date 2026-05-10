import argparse

def main():
    parser = argparse.ArgumentParser(description="CalJobs Autonomous Job Search Agent")
    parser.add_argument("--setup", action="store_true", help="Set up Google API credentials")
    parser.add_argument("--run", action="store_true", help="Run the job search and email check")
    
    args = parser.parse_args()
    
    if args.setup:
        print("Credentials setup is handled via the auth_utils module automatically when missing.")
    elif args.run:
        print("Running agent...")
        from src.runner import run_all
        run_all()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
