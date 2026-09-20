from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)
        if not results:
            return "Không tìm thấy thông tin phù hợp trong cơ sở dữ liệu."

        context_blocks = []
        for index, item in enumerate(results, start=1):
            source = item.get("metadata", {}).get("source_url") or item.get("id", f"chunk_{index}")
            context_blocks.append(f"[{index}] Nguồn: {source}\n{item['content']}")
        context_str = "\n\n".join(context_blocks)

        prompt = (
            f"Hãy trả lời câu hỏi dựa trên ngữ cảnh được cung cấp dưới đây. "
            f"Nếu thông tin không có trong ngữ cảnh, hãy nói rõ là không tìm thấy.\n\n"
            f"Ngữ cảnh:\n{context_str}\n\n"
            f"Câu hỏi: {question}\n\n"
            f"Câu trả lời:"
        )
        return self.llm_fn(prompt)
