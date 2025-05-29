import json
import nltk
import pandas as pd
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from rouge_score import rouge_scorer
from rag_utils import generate_answer, get_top_matches

nltk.download("punkt")
nltk.download("stopwords")

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

def evaluate(query, reference):
    matches, orig_scores, reranked_scores = get_top_matches(query, rerank=False)
    generated = generate_answer(query, matches)

    print("Query:", query)
    print("Top Chunks:")
    for i, chunk in enumerate(matches):
        print(f"Chunk {i+1}:", chunk[:150], "...")  # Print first 150 chars of each
    print("-" * 40)

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
        "keyword_match": round(keyword_score, 4)
    }

def main():
    with open("test_queries.json", "r") as f:
        test_cases = json.load(f)

    results = []

    for test in test_cases:
        query = test["query"]
        reference = test["expected_answer"]
        result = evaluate(query, reference)
        results.append(result)

    df = pd.DataFrame(results)
    df.to_csv("rag_evaluation_results.csv", index=False)
    print("✅ Evaluation complete. Results saved to rag_evaluation_results.csv")
    
if __name__ == "__main__":
    main()
