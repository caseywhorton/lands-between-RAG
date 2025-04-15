# lands-between-RAG

Not all models are the same.

Good: all-mpnet-base-v2
Bad: Bert-uncased

Need some examples of output from the baseline retrieval and also being passed to the open AI API.

Had to embed the `full_text` from the comments and/or body of the Reddit post.

Had to remove excessive markdown formatting using regex.

In this example, I had a reddit post that was directly related to a single weapon.

When I tried the openAI API to ask about the Venemous Fang weapon it said something like 'i dont have access to new reddit stuff', but when I added the retrieved documents from my Pinecone index then it returned some viable results.

It would be good to look at the scores and embeddings.

## Setup

+ set up a sagemaker domain
+ log in to pinecone using github
+ create jupyterlab space
+ install openai
+ get an open ai yke