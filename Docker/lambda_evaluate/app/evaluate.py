import json
import nltk
import pandas as pd
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from rouge_score import rouge_scorer
from rag_utils import generate_answer, get_top_matches
import csv
from datetime import datetime, timezone
import os
import boto3

# Load environment variables
INDEX_NAME = os.environ.get("INDEX_NAME", "default-index")
S3_BUCKET_NAME = ''
MODEL_USED = 'gpt-4'
use_fallback = True
timestamp = datetime.now(timezone.utc)

def keyword_match_score(reference: str, generated: str) -> float:
    stop_words = set(stopwords.words("english"))
    ref_tokens = word_tokenize(reference.lower())
    gen_tokens = word_tokenize(generated.lower())

    ref_keywords = {w for w in ref_tokens if w.isalnum() and w not in stop_words}
    gen_keywords = {w for w in gen_tokens if w.isalnum()}

    if not ref_keywords:
        return 0.0

    match_count = len(ref_keywords.intersection(gen_keywords))
    return match_count / len(ref_keywords)

def evaluate(query, reference, use_fallback):
    matches, orig_scores, reranked_scores = get_top_matches(query, rerank=False)

    # If no context, fallback to model-only
    if use_fallback and (not matches or all(len(chunk.strip()) < 30 for chunk in matches)):
        chunks = []
        print("⚠️ Context too weak — using GPT fallback only")
    else:
        chunks = matches

    generated = generate_answer(query, chunks)

    print("Query:", query)
    print("Top Chunks:")
    for i, chunk in enumerate(matches):
        print(f"Chunk {i+1}:", chunk[:150], "...")
    print("-" * 40)

    # Compute chunk overlap
    overlap_score, overlap_label = compute_chunk_overlap_score_with_label(generated, chunks)

    # ROUGE
    rouge = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)
    rouge_scores = rouge.score(reference, generated)

    # BLEU
    smoothie = SmoothingFunction().method4
    bleu = sentence_bleu([reference.split()], generated.split(), smoothing_function=smoothie)

    # Keyword Match
    keyword_score = keyword_match_score(reference, generated)

    return {
        "query": query,
        "reference": reference,
        "generated": generated,
        "rouge1": round(rouge_scores['rouge1'].fmeasure, 4),
        "rougeL": round(rouge_scores['rougeL'].fmeasure, 4),
        "bleu": round(bleu, 4),
        "keyword_match": round(keyword_score, 4),
        "chunk_overlap_score": round(overlap_score, 4),
        "chunk_overlap_label": overlap_label,
        "fallback_used": len(chunks) == 0,
        "model": MODEL_USED,
        "index": INDEX_NAME,
        "timestamp": timestamp.isoformat()
    }

def compute_chunk_overlap_score_with_label(generated_answer: str, context_chunks: list) -> tuple:
    context_text = " ".join(context_chunks).lower()
    
    # Tokenize and clean answer
    answer_tokens = word_tokenize(generated_answer.lower())
    answer_tokens = [w for w in answer_tokens if w.isalnum()]
    answer_tokens = [w for w in answer_tokens if w not in stopwords.words("english")]

    if not answer_tokens:
        return 0.0, "no_meaningful_tokens"

    match_count = sum(1 for word in answer_tokens if word in context_text)
    overlap_score = match_count / len(answer_tokens)

    # Assign interpretation label
    if overlap_score > 0.7:
        label = "used_context_strongly"
    elif overlap_score > 0.4:
        label = "used_context_partially"
    elif overlap_score > 0.1:
        label = "used_context_weakly"
    else:
        label = "ignored_context_likely"

    return overlap_score, label

def main():
    # Load test queries (adjust path for regular container)
    test_queries_path = "/app/test_queries.json" if os.path.exists("/app/test_queries.json") else "test_queries.json"
    
    with open(test_queries_path, "r") as f:
        test_cases = json.load(f)

    results = []

    for test in test_cases:
        query = test["query"]
        reference = test["expected_answer"]
        result = evaluate(query, reference, use_fallback)
        results.append(result)

    df = pd.DataFrame(results)

    # Strip newlines from returned text for CSV formatting
    def flatten_text(text: str) -> str:
        return text.replace("\n", " ").replace("\r", " ").strip()

    # Apply flattening to relevant columns
    df["generated"] = df["generated"].apply(flatten_text)
    df["reference"] = df["reference"].apply(flatten_text)

    # Save locally first
    output_file = "rag_evaluation_results.csv"
    df.to_csv(output_file, index=False)

    # Create S3 bucket prefix with yyyy/mm/dd format
    yyyy = timestamp.year
    mm = f"{timestamp.month:02d}"  # Zero-pad month
    dd = f"{timestamp.day:02d}"    # Zero-pad day
    s3_prefix = f"{yyyy}/{mm}/{dd}/"
    
    # Generate unique filename with timestamp
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    s3_key = f"{s3_prefix}rag_evaluation_results_{timestamp_str}.csv"

    try:
        # Upload to S3
        s3_client = boto3.client("s3", region_name='us-east-1')
        s3_client.upload_file(output_file, S3_BUCKET_NAME, s3_key)
        print(f"✅ Evaluation complete. Results saved to s3://{S3_BUCKET_NAME}/{s3_key}")
        
        # Also save summary stats
        summary = {
            "total_queries": len(results),
            "avg_rouge1": df["rouge1"].mean(),
            "avg_rougeL": df["rougeL"].mean(),
            "avg_bleu": df["bleu"].mean(),
            "avg_keyword_match": df["keyword_match"].mean(),
            "avg_chunk_overlap": df["chunk_overlap_score"].mean(),
            "fallback_usage_rate": df["fallback_used"].mean(),
            "timestamp": timestamp.isoformat()
        }
        
        print("\n📊 Summary Statistics:")
        for key, value in summary.items():
            if key != "timestamp":
                print(f"  {key}: {value:.4f}" if isinstance(value, float) else f"  {key}: {value}")
                
    except Exception as e:
        print(f"❌ Error uploading to S3: {e}")
        print(f"📁 Results saved locally as: {output_file}")

if __name__ == "__main__":
    main()