import streamlit as st
from rag_utils import get_top_matches, generate_answer

st.title("🔍 Elden Ring Build Finder")

query = st.text_input("Ask your question:")

if query:
    with st.spinner("Fetching answer..."):
        matches, scores = get_top_matches(query)
        answer = generate_answer(query, matches)

    st.subheader("📖 Answer")
    st.write(answer)

show_chunks = st.checkbox("Show retrieved chunks and similarity scores")

if show_chunks:
    st.subheader("📚 Retrieved Context Chunks")
    for i, (chunk, score) in enumerate(zip(matches, scores), 1):
        st.markdown(f"**Chunk {i} (Score: {score:.3f})**")
        st.write(chunk)
        st.write("---")
