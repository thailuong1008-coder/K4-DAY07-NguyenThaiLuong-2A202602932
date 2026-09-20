#!/usr/bin/env python3
"""Benchmark retrieval performance on ecommerce policy dataset."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.chunking import FixedSizeChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore


def parse_markdown_doc(path: Path) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter and markdown body."""
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return {"doc_id": path.stem}, raw

    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {"doc_id": path.stem}, raw

    fm_raw = parts[1]
    body = parts[2].strip()

    metadata: dict[str, str] = {"doc_id": path.stem}
    for line in fm_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if "#" in val:
                val = val.split("#", 1)[0].strip().strip('"').strip("'")
            metadata[key] = val

    return metadata, body


BENCHMARK_QUERIES = [
    {
        "id": "Q1",
        "query": "Thời hạn tối đa để gửi yêu cầu Trả hàng / Hoàn tiền đối với đơn hàng thực phẩm tươi sống trên Shopee là bao lâu?",
        "filter": None,
        "gold_doc": "shopee-quy-dinh-tra-hang-hoan-tien",
        "gold_answer": "Trong vòng 24 giờ kể từ khi đơn hàng cập nhật trạng thái 'Giao hàng thành công' (trừ trường hợp lý do là 'Chưa nhận được hàng').",
        "keywords": ["24 giờ", "thực phẩm tươi sống", "Giao hàng thành công"],
    },
    {
        "id": "Q2",
        "query": "Theo chính sách của Thế Giới Di Động, nếu vi phạm cam kết bảo hành 15 ngày thì khách hàng được quyền lợi gì?",
        "filter": None,
        "gold_doc": "thegioididong-chinh-sach-bao-hanh-doi-tra",
        "gold_answer": "Khách hàng được áp dụng phương thức 'Hư gì đổi nấy ngay và luôn' hoặc 'Hoàn tiền với mức phí giảm 50%'.",
        "keywords": ["Hư gì đổi nấy", "50%", "Hoàn tiền"],
    },
    {
        "id": "Q3",
        "query": "Thời hạn bảo hành tiêu chuẩn cho thân máy điện thoại thông minh Xiaomi tại Việt Nam là bao nhiêu tháng?",
        "filter": None,
        "gold_doc": "xiaomi-chinh-sach-bao-hanh",
        "gold_answer": "18 tháng kể từ ngày mua hàng đối với thân máy lỗi phần cứng do nhà sản xuất trong điều kiện sử dụng bình thường.",
        "keywords": ["18 tháng", "Điện thoại", "phần cứng"],
    },
    {
        "id": "Q4",
        "query": "Nếu ngày mua sản phẩm Apple trên hệ thống kiểm tra trực tuyến không chính xác thì khách hàng cần xuất trình giấy tờ gì để cập nhật?",
        "filter": None,
        "gold_doc": "apple-pham-vi-bao-hanh-thiet-bi",
        "gold_answer": "Khách hàng cần cung cấp biên lai bán hàng gốc hoặc hóa đơn tài chính hợp lệ từ đại lý ủy quyền của Apple để cập nhật lại ngày mua chính xác.",
        "keywords": ["biên lai", "hóa đơn", "ngày mua"],
    },
    {
        "id": "Q5_unfiltered",
        "query": "Thời hạn phản hồi yêu cầu khiếu nại trả hàng hoàn tiền là bao lâu?",
        "filter": None,
        "gold_doc": "shopee-quy-dinh-nguoi-ban-xu-ly-khieu-nai",
        "gold_answer": "Người bán phải phản hồi trong vòng 02 ngày (48 giờ làm việc) kể từ khi tiếp nhận khiếu nại. (Chưa lọc audience)",
        "keywords": ["48 giờ", "02 ngày"],
    },
    {
        "id": "Q5_filtered",
        "query": "Thời hạn phản hồi yêu cầu khiếu nại trả hàng hoàn tiền là bao lâu?",
        "filter": {"audience": "seller"},
        "gold_doc": "shopee-quy-dinh-nguoi-ban-xu-ly-khieu-nai",
        "gold_answer": "Người bán phải phản hồi trong vòng 02 ngày (48 giờ làm việc) kể từ khi tiếp nhận khiếu nại. Quá hạn hệ thống Shopee sẽ tự động hoàn tiền cho Người mua.",
        "keywords": ["48 giờ", "02 ngày", "Người bán"],
    },
]


def choose_embedder():
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            return LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        except Exception:
            return _mock_embed
    elif provider == "openai":
        try:
            return OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        except Exception:
            return _mock_embed
    elif provider == "gemini":
        try:
            return GeminiEmbedder(model_name=os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL))
        except Exception:
            return _mock_embed
    return _mock_embed


def main() -> int:
    data_dir = Path("data/ecommerce")
    if not data_dir.exists():
        print(f"Directory not found: {data_dir}")
        return 1

    md_files = sorted(data_dir.glob("*.md"))
    md_files = [f for f in md_files if f.stem not in {"return-refund-policy", "seller-warranty-policy"}]
    print("=== BẮT ĐẦU BENCHMARK TRUY XUẤT (K4-L3B) ===")
    print(f"Thư mục dữ liệu: {data_dir}")
    print(f"Số lượng file chính sách: {len(md_files)}")

    chunker = FixedSizeChunker(chunk_size=500, overlap=50)
    print("Chiến lược chia nhỏ: FixedSizeChunker(chunk_size=500, overlap=50)")

    chunked_documents: list[Document] = []
    file_chunk_stats = {}

    for path in md_files:
        metadata, body = parse_markdown_doc(path)
        chunks = chunker.chunk(body)
        file_chunk_stats[path.stem] = len(chunks)
        for idx, c in enumerate(chunks):
            chunk_id = f"{path.stem}#{idx}"
            chunk_metadata = {**metadata, "chunk_index": idx, "chunk_id": chunk_id}
            chunked_documents.append(Document(id=chunk_id, content=c, metadata=chunk_metadata))

    print(f"Tổng số chunks tạo thành: {len(chunked_documents)}")
    for name, cnt in file_chunk_stats.items():
        print(f"  - {name}: {cnt} chunks")

    embedder_raw = choose_embedder()
    backend_name = getattr(embedder_raw, '_backend_name', embedder_raw.__class__.__name__)
    print(f"Embedding backend: {backend_name}")

    import hashlib, json
    cache_file = Path("data/.embeddings_cache.json")
    cache: dict[str, list[float]] = {}
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    def cached_embedder(text: str) -> list[float]:
        key = f"{backend_name}:{hashlib.md5(text.encode('utf-8')).hexdigest()}"
        if key in cache:
            return cache[key]
        vec = embedder_raw(text)
        cache[key] = vec
        return vec

    print(f"Đang tiến hành nhúng {len(chunked_documents)} chunks (sử dụng cache nếu có)...")
    store = EmbeddingStore(collection_name="ecommerce_benchmark", embedding_fn=cached_embedder)
    for i, doc in enumerate(chunked_documents, 1):
        store.add_documents([doc])
        if i % 10 == 0 or i == len(chunked_documents):
            print(f"  Đã nhúng {i}/{len(chunked_documents)} chunks...")

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache), encoding="utf-8")

    log_lines = []
    log_lines.append("================================================================================")
    log_lines.append("KẾT QUẢ BENCHMARK TRUY XUẤT (K4-L3B) — CHIẾN LƯỢC: FixedSizeChunker")
    log_lines.append(f"Tổng số tài liệu: {len(md_files)} | Tổng số chunks: {len(chunked_documents)}")
    log_lines.append(f"Embedding Backend: {backend_name}")
    log_lines.append("================================================================================\n")

    top3_relevant_count = 0
    top1_relevant_count = 0

    for item in BENCHMARK_QUERIES:
        qid = item["id"]
        query = item["query"]
        qfilter = item["filter"]
        gold_doc = item["gold_doc"]
        gold_answer = item["gold_answer"]
        keywords = item["keywords"]

        print("--------------------------------------------------------------------------------")
        print(f"[{qid}] Query: {query}")
        if qfilter:
            print(f"Metadata Filter: {qfilter}")
            results = store.search_with_filter(query, top_k=3, metadata_filter=qfilter)
        else:
            print("Metadata Filter: Không")
            results = store.search(query, top_k=3)

        log_lines.append(f"[{qid}] Query: {query}")
        log_lines.append(f"Filter: {qfilter if qfilter else 'None'}")
        log_lines.append(f"Gold Doc: {gold_doc}")
        log_lines.append(f"Gold Answer: {gold_answer}")
        log_lines.append("Top-3 Kết quả truy xuất:")

        has_relevant_in_top3 = False
        top1_is_relevant = False

        for rank, res in enumerate(results, start=1):
            doc_id = res["metadata"].get("doc_id", "")
            score = res["score"]
            content = res["content"]
            snippet = content[:150].replace("\n", " ")

            is_gold_doc = (doc_id == gold_doc)
            contains_keywords = any(kw.lower() in content.lower() for kw in keywords)
            is_relevant = is_gold_doc and contains_keywords

            if is_relevant:
                has_relevant_in_top3 = True
                if rank == 1:
                    top1_is_relevant = True

            mark = "[ĐÚNG NGỮ CẢNH]" if is_relevant else ("[ĐÚNG DOC NHƯNG THIẾU KEYWORD]" if is_gold_doc else "[SAI DOC]")
            print(f"  Top-{rank} (Score: {score:.4f}) [{doc_id}] {mark}")
            print(f"    Snippet: {snippet}...")

            log_lines.append(f"  Top-{rank}: doc_id={doc_id} | score={score:.4f} | status={mark}")
            log_lines.append(f"    Nội dung: {snippet}...")

        if has_relevant_in_top3:
            top3_relevant_count += 1
        if top1_is_relevant:
            top1_relevant_count += 1

        eval_summary = "ĐẠT (Top-1 chuẩn)" if top1_is_relevant else ("ĐẠT (Nằm trong Top-3)" if has_relevant_in_top3 else "KHÔNG ĐẠT")
        print(f"Đánh giá: {eval_summary}\n")
        log_lines.append(f"Đánh giá: {eval_summary}\n")

    summary_text = (
        f"Tổng kết đánh giá 5 queries (bao gồm A/B test):\n"
        f"- Top-1 chính xác tuyệt đối: {top1_relevant_count}/6\n"
        f"- Top-3 có chứa thông tin trả lời: {top3_relevant_count}/6\n"
    )
    print(summary_text)
    log_lines.append(summary_text)

    output_path = Path("ket_qua_benchmark.txt")
    output_path.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"Đã lưu chi tiết kết quả benchmark vào: {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
