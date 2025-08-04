import json
import boto3
import praw
import os
from datetime import datetime

# Load Reddit API credentials from environment variables
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

# AWS S3 client
s3 = boto3.client("s3")

# S3 bucket name (set in Lambda environment variables)
S3_BUCKET = "webscrape-lands-between"

def fetch_subreddit_threads(subreddit_name, limit=10, comment_limit=5):
    """Fetches posts from a subreddit and formats them for storage in S3."""
    
    subreddit = reddit.subreddit(subreddit_name)
    formatted_threads = []
    
    for submission in subreddit.hot(limit=limit):  # Fetch top posts
        thread = {
            "id": submission.id,  # Unique post ID
            "title": submission.title,
            "body": submission.selftext,  # Post content
            "comments": [],
            "metadata": {
                "subreddit": subreddit_name,
                "url": submission.url,
                "author": submission.author.name if submission.author else "Unknown",
                "timestamp": int(submission.created_utc),
            }
        }
        
        # Fetch top-level comments
        submission.comment_sort = "top"
        submission.comments.replace_more(limit=0)
        
        for comment in submission.comments[:comment_limit]:  # Limit comments
            thread["comments"].append(comment.body)
        
        formatted_threads.append(thread)
    
    return formatted_threads

def save_to_s3(data, subreddit_name):
    """Saves formatted subreddit data to an S3 bucket as JSON."""
    
    # Generate a timestamped filename
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    file_key = f"reddit_data/{subreddit_name}/{subreddit_name}_{timestamp}.json"

    # Convert data to JSON
    json_data = json.dumps(data, indent=2)

    # Upload JSON data to S3
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=file_key,
        Body=json_data,
        ContentType="application/json"
    )

    return file_key

def lambda_handler(event, context):
    """AWS Lambda entry point."""
    
    subreddit_name = "EldenringBuilds"
    posts = fetch_subreddit_threads(subreddit_name, limit=10, comment_limit=5)
    
    if not posts:
        return {"statusCode": 404, "body": "No data fetched"}
    
    file_key = save_to_s3(posts, subreddit_name)
    
    return {
        "statusCode": 200,
        "body": f"Data saved to S3: {file_key}"
    }
