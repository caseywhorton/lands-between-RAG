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

## Case Study: Venomous Fang Weapon

Using the latest Reddit posts on the game within a RAG (Retrieval-Augmented Generation) application allows the language model to return up-to-date results that are typically outside the scope of a pre-trained model. This showcases the core value of RAG systems — grounding responses in real-time, community-sourced knowledge.

### Prompt (No Context Provided)

> _"Can you briefly tell me about the Venomous Fang weapon in Elden Ring?"_

**Response:**

> As of now, specific details about the Venomous Fang weapon in Elden Ring are not available. Elden Ring is an upcoming action role-playing game developed by FromSoftware and published by Bandai Namco Entertainment. The game's information is still being released, and specifics about individual weapons like the Venomous Fang have not been fully disclosed yet. Please stay tuned to the official updates for the most accurate information.

### Prompt (With Reddit Context Injected via Pinecone Retrieval)

> _"Can you briefly tell me about the Venomous Fang weapon in Elden Ring?"_

**Response:**

> The Venomous Fang is a unique fist weapon in Elden Ring known for its rapid strikes and native poison status. It's lightweight and can inflict "Deadly Poison" on enemies, which deals significant damage over time. It can be enhanced by applying Poison or Occult Affinities, tripling the poison damage or increasing the poison buildup respectively. By acquiring two Venomous Fangs, you can apply different affinities to each, allowing you to build up multiple status effects simultaneously. It pairs well with the Poison Flower Blooms Twice Ash of War, which delivers a powerful attack when an enemy is poisoned. The Venomous Fang's effectiveness can be further boosted with specific equipment and talismans, like the Mushroom Crown, which raises attack power after poisoning an enemy.

### Takeaway

Including a Reddit post that discusses the **Venomous Fang** weapon provides the necessary context for GPT to generate a more accurate and helpful answer. This demonstrates the strength of RAG systems: by pairing relevant, up-to-date information with GPT’s natural language generation, we get responses that are both **informed** and **fluent**.

## 🛠️ Setup Instructions

1. Set up a **SageMaker Studio Domain**.
2. Log into **Pinecone** using your GitHub account.
3. Create a **JupyterLab environment** inside SageMaker.
4. Install required libraries:
   ```bash
   pip install openai pinecone-client pandas
