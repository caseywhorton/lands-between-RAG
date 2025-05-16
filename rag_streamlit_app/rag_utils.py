import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from pinecone import Pinecone

# Load environment variables
load_dotenv()

# Setup clients
#s3_client = boto3.client('s3')  # (optional, not used in this code)
embedding_model = SentenceTransformer("all-mpnet-base-v2")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"), environment="us-east1-aws")
index = pc.Index("lands-between-eldenringbuilds")

def get_top_matches(query: str, top_k: int = 5):
    query_embedding = embedding_model.encode(query).tolist()
    results = index.query(vector=query_embedding, top_k=top_k, include_metadata=True)
    
    # Return both the text chunks and their scores
    documents = [match['metadata'].get('full_text', '') for match in results['matches']]
    scores = [match['score'] for match in results['matches']]
    
    return documents, scores


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
