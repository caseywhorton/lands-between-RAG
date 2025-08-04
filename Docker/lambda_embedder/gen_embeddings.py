import os
import json
import re
import argparse
from datetime import datetime, timezone

import boto3
from sentence_transformers import SentenceTransformer
from pinecone import (
    Pinecone,
    ServerlessSpec,
    CloudProvider,
    AwsRegion
)

# Load environment variables
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_ENV = os.environ.get("PINECONE_ENV", "us-east1-aws")
INDEX_NAME = os.environ["INDEX_NAME"]
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-mpnet-base-v2")
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "768"))
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
S3_PREFIX = os.environ["S3_PREFIX"]
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Initialize clients
s3_client = boto3.client("s3", region_name=AWS_REGION)
model = None
pc = None
index = None

def get_model():
    global model
    if model is None:
        try:
            model = SentenceTransformer(
                EMBEDDING_MODEL,
                cache_folder="/app/cache"
            )
        except Exception as e:
            print(f"[ERROR] Failed to load embedding model: {e}")
            raise
    return model


def get_index():
    global pc, index
    if index is None:
        try:
            pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
            if not any(i["name"] == INDEX_NAME for i in pc.list_indexes()):
                pc.create_index(
                    name=INDEX_NAME,
                    dimension=EMBEDDING_DIM,
                    spec=ServerlessSpec(
                        cloud=CloudProvider.AWS,
                        region=AwsRegion.US_EAST_1
                    )
                )
                print(f"[INFO] Created index: {INDEX_NAME}")
            else:
                print(f"[INFO] Index {INDEX_NAME} already exists")
            index = pc.Index(INDEX_NAME)
        except Exception as e:
            print(f"[ERROR] Pinecone index setup failed: {e}")
            raise
    return index


def retrieve_s3_files(bucket_name, prefix, latest_only=False):
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        all_files = []
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".json"):
                    all_files.append({"Key": key, "LastModified": obj["LastModified"]})

        if not all_files:
            print("[WARN] No JSON files found.")
            return []

        if latest_only:
            latest_file = max(all_files, key=lambda x: x["LastModified"])
            return [latest_file["Key"]]

        return [f["Key"] for f in all_files]
    except Exception as e:
        print(f"[ERROR] Failed to retrieve S3 files: {e}")
        return []


def read_s3_file(bucket_name, file_key):
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        return response["Body"].read().decode("utf-8")
    except Exception as e:
        print(f"[ERROR] Failed to read S3 file {file_key}: {e}")
        raise


def clean_text(text):
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Remove markdown links
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def generate_embeddings(text):
    try:
        return get_model().encode(text).tolist()
    except Exception as e:
        print(f"[ERROR] Failed to generate embeddings: {e}")
        raise


def insert_into_pinecone(vectors):
    batch_size = 100
    try:
        index = get_index()
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            try:
                index.upsert(vectors=batch)
            except Exception as e:
                print(f"[ERROR] Pinecone upsert failed for batch starting at {i}: {e}")
    except Exception as e:
        print(f"[ERROR] Failed during Pinecone insertion: {e}")
        raise
    else:
        print(f"[INFO] Inserted {len(vectors)} vectors into Pinecone.")


def process_s3_files(bucket_name, prefix, latest_only=True):
    file_keys = retrieve_s3_files(bucket_name, prefix, latest_only=latest_only)
    print(f"[DEBUG] Files to process: {file_keys}")

    for file_key in file_keys:
        try:
            data = read_s3_file(bucket_name, file_key)
            reddit_posts = json.loads(data)
        except Exception as e:
            print(f"[ERROR] Failed to load or parse JSON from {file_key}: {e}")
            continue

        vectors = []
        for post in reddit_posts:
            post_id = post.get("id", "unknown-id")
            meta = post.get("metadata", {})
            subreddit = meta.get("subreddit", "")
            url = meta.get("url", "")
            author = meta.get("author", "")
            timestamp = meta.get("timestamp", "")

            if post.get("body"):
                try:
                    body_text = clean_text(post["body"])
                    body_vec = generate_embeddings(body_text)
                    vectors.append({
                        "id": f"{post_id}-body",
                        "values": body_vec,
                        "metadata": {
                            "type": "body",
                            "subreddit": subreddit,
                            "url": url,
                            "author": author,
                            "timestamp": timestamp,
                            "full_text": body_text,
                            "embedding_model": EMBEDDING_MODEL
                        }
                    })
                except Exception as e:
                    print(f"[ERROR] Failed to process post body {post_id}: {e}")

            for idx, comment in enumerate(post.get("comments", [])):
                try:
                    comment_text = clean_text(comment)
                    comment_vec = generate_embeddings(comment_text)
                    vectors.append({
                        "id": f"{post_id}-comment-{idx}",
                        "values": comment_vec,
                        "metadata": {
                            "type": "comment",
                            "subreddit": subreddit,
                            "url": url,
                            "author": author,
                            "timestamp": timestamp,
                            "full_text": comment_text,
                            "embedding_model": EMBEDDING_MODEL
                        }
                    })
                except Exception as e:
                    print(f"[ERROR] Failed to process comment {idx} for post {post_id}: {e}")

        try:
            insert_into_pinecone(vectors)
        except Exception as e:
            print(f"[ERROR] Failed to insert vectors into Pinecone for file {file_key}: {e}")


# ---------------------- MAIN ENTRY ----------------------

import sys
import logging
import gc

if __name__ == "__main__":
    print("[INFO] Starting embedding generation...")
    try:
        process_s3_files(S3_BUCKET_NAME, S3_PREFIX)
        print("[INFO] ✅ All done.")
    except Exception as e:
        print(f"[FATAL] Uncaught exception during embedding generation: {e}")
    finally:
        print("[INFO] Cleaning up before exit...")
        sys.stdout.flush()
        sys.stderr.flush()
        gc.collect()
        sys.exit(0)