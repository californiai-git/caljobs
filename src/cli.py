import argparse

def main():
    parser = argparse.ArgumentParser(description="CalJobs Autonomous Job Search Agent")
    parser.add_argument("--setup", action="store_true", help="Set up Google API credentials")
    parser.add_argument("--run", action="store_true", help="Run the job search and email check")
    
    args = parser.parse_args()
    
    if args.setup:
        print("Setting up credentials...")
        # TODO: call gmail_client.authenticate() and drive_client.authenticate()
    elif args.run:
        print("Running agent...")
        # TODO: call runner.run_all()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
