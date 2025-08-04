import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from pinecone import Pinecone
from sklearn.metrics.pairwise import cosine_similarity
import httpx

# Load environment variables
load_dotenv()

# Setup clients
embedding_model = SentenceTransformer("all-mpnet-base-v2")
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
# Create httpx client without proxies parameter
http_client = httpx.Client()
client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    http_client=http_client
)

# Get index name from environment or use default
INDEX_NAME = os.environ.get("INDEX_NAME", "")
index = pc.Index(INDEX_NAME)

def rerank_documents(query: str, documents: list):
    """Rerank documents using GPT-4 relevance scoring"""
    reranked = []
    
    for doc in documents:
        # Simple prompt for reranking
        prompt = f"Query: {query}\n\nPassage: {doc}\n\nHow relevant is this passage to the query? Respond with a score from 0 (not relevant) to 10 (highly relevant)."
        
        try:
            
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
                
        except Exception as e:
            print(f"Error in reranking: {e}")
            score = 0.0
            
        reranked.append((doc, score))
    
    # Sort by score descending
    reranked.sort(key=lambda x: x[1], reverse=True)
    
    if reranked:
        reranked_docs, reranked_scores = zip(*reranked)
        return list(reranked_docs), list(reranked_scores)
    else:
        return [], []

def get_top_matches(query: str, top_k: int = 5, rerank: bool = False):
    """Retrieve top matching documents from Pinecone index"""
    try:
        query_embedding = embedding_model.encode(query).tolist()
        results = index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
        
        docs = []
        original_scores = []
        
        for match in results.get('matches', []):
            # Try different metadata keys for text content
            text_content = (match['metadata'].get('full_text', '') or 
                          match['metadata'].get('text', '') or 
                          match['metadata'].get('content', ''))
            
            if text_content:  # Only add non-empty documents
                docs.append(text_content)
                original_scores.append(match['score'])
        
        if rerank and docs:
            doc_embeddings = [embedding_model.encode(doc) for doc in docs]
            reranked_scores = [cosine_similarity([query_embedding], [emb])[0][0] for emb in doc_embeddings]
            reranked = sorted(zip(docs, original_scores, reranked_scores), key=lambda x: x[2], reverse=True)
            
            if reranked:
                docs, original_scores, reranked_scores = zip(*reranked)
                return list(docs), list(original_scores), list(reranked_scores)
            else:
                return [], [], []
        else:
            reranked_scores = original_scores
        
        print(f"Retrieved {len(docs)} documents")
        return list(docs), list(original_scores), list(reranked_scores)
        
    except Exception as e:
        print(f"Error retrieving matches: {e}")
        return [], [], []

def generate_answer(query: str, context_chunks: list):
    """Generate answer using GPT-4 with provided context"""
    try:
        if context_chunks:
            context = "\n\n".join(context_chunks)
            prompt = f"Question: {query}\n\nContext:\n{context}\n\nAnswer:"
        else:
            # Fallback when no context is available
            prompt = f"Question: {query}\n\nPlease provide a helpful answer based on your knowledge."
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Use the provided context when available to answer questions accurately."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error generating answer: {e}")
        return f"Error generating answer: {str(e)}"