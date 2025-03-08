import os
import subprocess
import datetime
import random
import time

print("running...")

# GitHub repo details
GITHUB_USERNAME = "caseywhorton"
GITHUB_REPO = "lands-between-RAG"

# Get the current date
today = datetime.datetime.today().strftime("%Y-%m-%d")

# Generate a random commit message
commit_messages = [
    "Daily commit ✅",
    "Automating my GitHub streak! 📅",
    "Another day, another commit! 🚀",
    "Keeping the streak alive! 🔥",
    "Automated push at " + today,
]
commit_message = random.choice(commit_messages)
print('commit_message', commit_message)

# File to update (create if not exists)
file_name = "daily_commit.txt"
file_path = os.path.join(os.getcwd(), file_name)

# Write current timestamp to the file
with open(file_path, "a") as file:
    file.write(f"Commit on {today}\n")

# Get GitHub token from environment
GITHUB_PAT = os.getenv("GITHUB_PAT")

if not GITHUB_PAT:
    print("Error: GITHUB_PAT environment variable not set.")
    exit(1)

# Set the Git remote URL with the PAT
remote_url = f"https://{GITHUB_USERNAME}:{GITHUB_PAT}@github.com/{GITHUB_USERNAME}/{GITHUB_REPO}.git"
subprocess.run(f"git remote set-url origin {remote_url}", shell=True, check=True)

# Git commands
commands = [
    "git add .",
    f'git commit -m "{commit_message}"',
    "git push origin main"
]

# Execute Git commands
for command in commands:
    process = subprocess.run(command, shell=True, capture_output=True, text=True)
    if process.returncode != 0:
        print(f"Error: {process.stderr}")
        break

print("✅ Daily commit pushed to GitHub!")
