import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from pinecone import Pinecone
from datetime import datetime

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
    """Retrieve top matching documents from Pinecone index"""
    try:
        query_embedding = embedding_model.encode(query).tolist()
        results = index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
        
        docs = []
        metadata = []
        original_scores = []
        
        for match in results.get('matches', []):
            text_content = (
                match['metadata'].get('full_text', '') or 
                match['metadata'].get('text', '') or 
                match['metadata'].get('content', '')
            )
            
            if text_content:
                docs.append(text_content)
                metadata.append({
                    "timestamp": match['metadata'].get('timestamp'),
                    "author": match['metadata'].get('author'),
                    "url": match['metadata'].get('url')
                })
                original_scores.append(match['score'])
        
        # optional reranking
        reranked_scores = original_scores
        if rerank and docs:
            doc_embeddings = [embedding_model.encode(doc) for doc in docs]
            reranked_scores = [cosine_similarity([query_embedding], [emb])[0][0] for emb in doc_embeddings]
            reranked = sorted(zip(docs, metadata, original_scores, reranked_scores), key=lambda x: x[3], reverse=True)
            
            if reranked:
                docs, metadata, original_scores, reranked_scores = zip(*reranked)
                return list(docs), list(metadata), list(original_scores), list(reranked_scores)
            else:
                return [], [], [], []
        
        print(f"Retrieved {len(docs)} documents")
        return docs, metadata, original_scores, reranked_scores
        
    except Exception as e:
        print(f"Error retrieving matches: {e}")
        return [], [], [], []



def format_context(docs, metadata):
    """Format docs + metadata (like timestamp) for the model"""
    formatted_chunks = []
    for doc, meta in zip(docs, metadata):
        timestamp = meta.get("timestamp")
        if timestamp:
            # Convert UNIX epoch → readable date
            ts_str = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
        else:
            ts_str = "Unknown date"
        
        author = meta.get("author", "unknown author")
        url = meta.get("url", "")
        
        chunk = f"[Posted on {ts_str} by {author}] {doc}\nSource: {url}"
        formatted_chunks.append(chunk)
    return formatted_chunks

def generate_answer(query: str, docs: list, metadata: list):
    """Generate answer using GPT-4 with provided context"""
    try:
        if docs:
            formatted_chunks = format_context(docs, metadata)
            context = "\n\n".join(formatted_chunks)
            prompt = f"Question: {query}\n\nContext:\n{context}\n\nAnswer:"
        else:
            prompt = f"Question: {query}\n\nPlease provide a helpful answer based on your knowledge."
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Use the provided context (including timestamps) to answer questions accurately and reflect recency."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error generating answer: {e}")
        return f"Error generating answer: {str(e)}"

