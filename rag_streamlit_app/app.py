import streamlit as st
from rag_utils import get_top_matches, generate_answer

st.title("🔍 Elden Ring Build Finder")

query = st.text_input("Ask your question:")

rerank_enabled = st.checkbox("🔄 Enable reranking of retrieved chunks", value=False)

matches = []
orig_scores = []
reranked_scores = []

if query:
    with st.spinner("Fetching answer..."):
        matches, orig_scores, reranked_scores = get_top_matches(query, rerank=rerank_enabled)
        answer = generate_answer(query, matches)

        st.subheader("📖 Answer")
        st.write(answer)

if st.checkbox("🧩 Show retrieved chunks"):
    st.subheader("Context Chunks")
    for i, (doc, o_score, r_score) in enumerate(zip(matches, orig_scores, reranked_scores), 1):
        st.markdown(f"**Chunk {i}**")
        st.markdown(f"• Original Score: `{o_score:.4f}`")
        st.markdown(f"• Reranked Score: `{r_score:.4f}`")
        st.write(doc)
        st.markdown("---")

