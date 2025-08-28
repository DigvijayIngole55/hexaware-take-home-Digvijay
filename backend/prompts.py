def get_answer_prompt(context: str, query: str) -> str:
    return f"""Answer the question using ONLY the information from the provided documents. If the answer is not found in the documents, respond with "No answer found in provided documents."

Format your response as:
Answer: [your answer here]
Citation: [document name(s)]

Documents:
{context}

Question: {query}

Examples:
Question: What is Docker used for?
Answer: Docker is used for containerization, allowing applications to run in isolated environments.
Citation: Docker.pdf

Question: What programming language is best for web development?
Answer: No answer found in provided documents.
Citation: None

Answer:"""