# 🛡️ Lands Between RAG

> _Not all models are the same._

This is a Retrieval-Augmented Generation (RAG) application that helps users explore up-to-date **Elden Ring character builds** by leveraging recent Reddit posts. The goal is to reduce hallucinations and increase relevance when asking questions about the game's constantly evolving meta.

---

## ⚙️ Process Overview

The RAG pipeline follows three main stages:

### 1. Ingest Reddit Posts into S3
- Scrape or export relevant Reddit posts from Elden Ring-related subreddits.
- Store raw post data (title, body, comments) in Amazon S3 as JSON files.

### 2. Transform and Embed Reddit Posts into Pinecone
- Clean the text: strip excessive markdown, remove signatures or boilerplate.
- Use the `all-mpnet-base-v2` model to create embeddings.
- Store the embeddings along with metadata (e.g., post ID, subreddit, weapon tags) in a Pinecone index.

### 3. Query and Augment Model Context
- When a user asks a question (e.g., "What’s a good poison build?"), the system:
  - Embeds the query.
  - Retrieves top-k relevant Reddit posts from Pinecone.
  - Adds the retrieved content to the context window of a language model (e.g., OpenAI API).
- This allows the model to generate answers grounded in real community discussions.

---

## 🤖 Models

| Component     | Model Used           | Notes                          |
|---------------|----------------------|--------------------------------|
| Embeddings    | `all-mpnet-base-v2`  | Best results so far            |
| LLM (good)    | `gpt-3.5` or `gpt-4` | Works well with retrieved docs |
| LLM (bad)     | `bert-uncased`       | Poor performance, baseline     |

---

## 💡 Observations

- Embedding the `full_text` (from both post body and top comments) improves answer relevance.
- Removing markdown formatting (e.g., `**bold**`, `>` quotes) using regex helps clean input for embedding.
- Without context, the OpenAI API may say:  
  > “I don’t have access to current Reddit discussions.”
- When using retrieved Pinecone documents (e.g., about *Venomous Fang*), the model gives accurate, viable recommendations.
- Embedding similarity scores are useful for debugging relevance.

---

## 🛠️ Setup Instructions

1. Set up a **SageMaker Studio Domain**.
2. Log into **Pinecone** using your GitHub account.
3. Create a **JupyterLab environment** inside SageMaker.
4. Install required libraries:
   ```bash
   pip install openai pinecone-client pandas
