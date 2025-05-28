import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from pinecone import Pinecone
from sklearn.metrics.pairwise import cosine_similarity

# Load environment variables
load_dotenv()

# Setup clients
#s3_client = boto3.client('s3')  # (optional, not used in this code)
embedding_model = SentenceTransformer("all-mpnet-base-v2")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"), environment="us-east1-aws")
index = pc.Index("lands-between-eldenringbuilds")


def rerank_documents(query: str, documents: list, client):
    reranked = []
    for doc in documents:
        # Simple prompt for reranking
        prompt = f"Query: {query}\n\nPassage: {doc}\n\nHow relevant is this passage to the query? Respond with a score from 0 (not relevant) to 10 (highly relevant)."
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        score_text = response.choices[0].message.content.strip()
        try:
            score = float(score_text)
        except ValueError:
            score = 0.0
        reranked.append((doc, score))
    
    # Sort by score descending
    reranked.sort(key=lambda x: x[1], reverse=True)
    reranked_docs, reranked_scores = zip(*reranked)
    return list(reranked_docs), list(reranked_scores)


def get_top_matches(query: str, top_k: int = 5, rerank: bool = False):
    query_embedding = embedding_model.encode(query).tolist()
    results = index.query(vector=query_embedding, top_k=top_k, include_metadata=True)

    docs = []
    original_scores = []
    
    for match in results['matches']:
        docs.append(match['metadata'].get('text', ''))
        original_scores.append(match['score'])

    if rerank:
        # Simple rerank: cosine similarity between query and doc embedding
        doc_embeddings = [embedding_model.encode(doc) for doc in docs]
        reranked_scores = [cosine_similarity([query_embedding], [emb])[0][0] for emb in doc_embeddings]

        # Sort by reranked scores (descending)
        reranked = sorted(zip(docs, original_scores, reranked_scores), key=lambda x: x[2], reverse=True)
        docs, original_scores, reranked_scores = zip(*reranked)
    else:
        reranked_scores = original_scores  # fallback: same as original

    return list(docs), list(original_scores), list(reranked_scores)



def generate_answer(query: str, context_chunks: list):
    context = "\n\n".join(context_chunks)
    prompt = f"Question: {query}\n\nContext:\n{context}\n\nAnswer:"
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content
