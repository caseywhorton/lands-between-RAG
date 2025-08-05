# Lands Between RAG

> _Not all models are the same._

A Retrieval-Augmented Generation (RAG) application that helps users explore up-to-date **Elden Ring character builds** by leveraging recent Reddit discussions. Reduces hallucinations and increases relevance by grounding responses in real community knowledge.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/)

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/caseywhorton/lands-between-RAG.git
cd lands-between-RAG

# Set up environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

## Architecture

<img src="img/whorton_aws_rag.png" alt="Solution Architecture Overview" width="1000" height="700">
  

---

## Process Overview

The RAG pipeline follows three main stages:

### 1. Ingest Reddit Posts into S3
Services Used: _AWS EventBridge, AWS Lambda, AWS S3, Reddit_
- **Source**: Scrape relevant posts from Elden Ring subreddits using PRAW
- **Storage**: Store raw post data (title, body, comments) in Amazon S3 as JSON
- **Frequency**: Configurable cron job for fresh content


### 2. Transform and Embed Posts into Pinecone
Services Used: _AWS Sagemaker AI, AWS EventBridge, AWS Lambda, Docker, Pinecone_
- **Preprocessing**: Clean text (strip markdown, remove boilerplate and stop words)
- **Embedding Model**: `all-mpnet-base-v2` for high-quality vector representations
- **Vector Store**: Pinecone index with metadata (post ID, subreddit, weapon tags)
- **Processing**: SageMaker for scalable batch processing

### 3. Evaluate the RAG Application with Test Set
Services Used: _AWS Sagemaker AI, AWS EventBridge, AWS Lambda, AWS S3, Docker, Pinecone, OpenAI_
- **Pull test data**: Test data is a CSV with test queries and sample responses
- **Preprocessing**: Clean text (strip markdown, remove boilerplate and stop words)
- **Embedding Model**: Use the same embedding model to embed test query text
- **Retrieval**: Semantic search in Pinecone for top-k relevant posts for each test query
- **Augmentation**: Inject retrieved content into LLM context
- **Generation**: GPT-3.5/4 produces grounded, accurate responses
- **Evaluate**: Evaluate responses using NLP metrics, save results to S3

### 4. Query and Generate Responses
Services Used: _Streamlit, Pinecone, OpenAI_
- **User Query**: "What's a good poison build?"
- **Retrieval**: Semantic search in Pinecone for top-k relevant posts
- **Augmentation**: Inject retrieved content into LLM context
- **Generation**: GPT-3.5/4 produces grounded, accurate responses

---

## Models & Performance

| Component     | Model                | Performance Notes              | Cost   |
|---------------|----------------------|--------------------------------|--------|
| Embeddings    | `all-mpnet-base-v2` | Best semantic similarity       | Free   |
| LLM (Prod)    | `gpt-4`             | Highest quality responses      | $$$    |
| LLM (Dev)     | `gpt-3.5-turbo`     | Good balance of cost/quality   | $$     |
| Baseline      | `bert-base-uncased` | Poor performance (comparison)  | Free   |

### Evaluation Metrics
- **Relevance Score**: 8.5/10 (with context) vs 3.2/10 (without)
- **Response Time**: ~2.3s average
- **Context Window**: 4,096 tokens (includes 3-5 relevant posts)

---

## Key Insights

**What Works:**
- Embedding `full_text` (post + top comments) improves relevance
- Regex cleaning of markdown formatting enhances embedding quality
- Pinecone similarity scores >0.7 indicate high relevance
- Recent posts (< 30 days) provide better meta accuracy

**Limitations:**
- Without RAG context: *"I don't have access to current Reddit discussions"*
- Older posts may contain outdated build information
- Processing latency increases with context size

---

## Case Study: Venomous Fang Weapon

### Without RAG Context

**Query**: *"Can you briefly tell me about the Venomous Fang weapon in Elden Ring?"*

**Response**: 
> As of now, specific details about the Venomous Fang weapon in Elden Ring are not available...

### With RAG Context (Retrieved from Reddit)

**Same Query** → **Retrieved 3 relevant posts** → **Enhanced Response**:

> The Venomous Fang is a unique fist weapon in Elden Ring known for its rapid strikes and native poison status. It's lightweight and can inflict "Deadly Poison" on enemies, which deals significant damage over time. It can be enhanced by applying Poison or Occult Affinities, tripling the poison damage or increasing the poison buildup respectively...

**Result**: Accurate, detailed, community-validated information

---

## Setup & Deployment

### Prerequisites

- AWS Account with SageMaker access
- [Pinecone](https://www.pinecone.io) account (free tier available)
- [OpenAI API](https://platform.openai.com) key
- Reddit API credentials (PRAW)

### Environment Setup

1. **SageMaker Studio Domain**
   ```bash
   aws sagemaker create-domain --domain-name lands-between-rag
   ```

2. **Environment Variables**
   ```bash
   export OPENAI_API_KEY="your-key-here"
   export PINECONE_API_KEY="your-pinecone-key"
   export REDDIT_CLIENT_ID="your-reddit-client-id"
   export REDDIT_CLIENT_SECRET="your-reddit-secret"
   ```

### Docker Containers

Build multi-platform containers for AWS deployment:

```bash
# Embedding processor
docker build --platform linux/amd64 --no-cache -t rag-embedding .
docker tag rag-embedding:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/rag-embedding:latest

# Evaluation processor  
docker build --platform linux/amd64 --no-cache -t rag-evaluation .
docker tag rag-evaluation:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/rag-evaluation:latest

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/rag-embedding:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/rag-evaluation:latest
```

### Lambda Layer (PRAW)

```bash
# Create PRAW layer for Reddit scraping
docker run --rm -v $(pwd):/var/task \
    public.ecr.aws/lambda/python:3.10 \
    /bin/bash -c "pip install praw -t /var/task/python/ && exit"

zip -r praw_layer.zip python/
aws lambda publish-layer-version --layer-name praw-layer --zip-file fileb://praw_layer.zip
```

### CDK Deployment

```bash
mkdir sagemaker-cdk-project && cd sagemaker-cdk-project
python3 -m venv .venv && source .venv/bin/activate
npm install -g aws-cdk
pip install aws-cdk-lib constructs boto3
cdk init app --language python

# Deploy infrastructure
cdk deploy
```

---

## Project Structure

```
lands-between-RAG/
├── rag_streamlit_app/ # Streamlit application for querying index
├── └──  test_queries.json # dictionary for RAG evaluation
├── scraper_lambda/ # lambda function for scraping Reddit
├── Docker/
│   ├── embedding/         # SageMaker processing container and code
│   └── evaluation/        # Model evaluation container and code
├── cdk/                   # Infrastructure as code
├── tests/                 # Unit and integration tests
├── requirements.txt
└── README.md
```

---

## Usage

### Basic Query

Navigate to the **rag_streamlit_app** directory and run:  

`streamlit run app.py`

<img src="img/streamlit_img.jpg" alt="Basic query in the streamlit app" width="1000" height="500">

---

## Testing

For testing offline, run Docker containers with a .env file.  

```
docker run \
  -e AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id) \
  -e AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key) \
  --env-file .env \
  -p 9000:8080 <container name>
  ```

---

## Monitoring & Metrics

- **CloudWatch**: Processing job metrics, Lambda execution times
- **Pinecone**: Query latency, index usage
- **Evaluation**: Rouge, Bleu, Context Overlap, Keyword Matches

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [FromSoftware](https://www.fromsoftware.jp/) for creating Elden Ring
- [r/Eldenring](https://reddit.com/r/EldenringBuilds) community for build discussions
- [Sentence Transformers](https://www.sbert.net/) for embedding models
- [Pinecone](https://www.pinecone.io/) for vector search infrastructure

---

## Support

- **Bug Reports**: [GitHub Issues](https://github.com/caseywhorton/lands-between-RAG/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/caseywhorton/lands-between-RAG/discussions)
- **Contact**: [caseywhorton@gmail.com](mailto:caseywhorton@gmail.com)