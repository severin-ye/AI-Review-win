"""③ retrieve：每句查询重写 + 向量/关键词两路并行检索 + RRF 融合 + 3+3 证据入库。

流程（设计文档 §5.2③，对每个待审校句子）：
1. 查询重写：一次 LLM 调用生成 N 个问题（N=retrieve.query_count，默认 8，范围 5-10；
   第 1 条保留原句 + 医学实体提取 + 不同角度核查问题，JSON 数组返回）。
   LLM 未配置/调用失败 → 降级为只用原句检索（不中断流水线）。
2. 每个问题并行打两路：向量路（BGE-M3 → LanceDB top-k）+ BM25 路（jieba 分词 → BM25 top-k）。
   融合前每问每路取 k*3 候选（k=各路 topk，默认 3 → 9 候选/问/路）。
3. 跨问题 RRF 融合（每路内部，k=retrieve.rrf_k 默认 60）→ 各路取 top-3。
4. 两路合并按 chunk_id 去重（同 chunk 取 RRF 分高的一路定 source 标签）→ ≤6 条证据入库。

跳过：参考文献块（blocks.is_reference，除非 segment.review_references=true）、
表格占位符句（[{表格不予审校_N}]，M2 已知问题 3）。
重写的问题同时落 queries 表（溯源），证据落 evidence 表。
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.db import engine
from app.core.user_settings import (
    retrieve_bm25_topk,
    retrieve_query_count,
    retrieve_rrf_k,
    retrieve_vector_topk,
    review_references,
)
from app.llm.client import LLMNotConfiguredError, chat_json
from app.models import Block, Evidence, Query, Sentence
from app.rag import store
from app.rag.embeddings import EmbeddingProvider

PLACEHOLDER_RE = re.compile(r"^\[\{表格不予审校_\d+\}\]$")

Emit = Callable[[str, dict], None]

_REWRITE_SYSTEM = (
    "你是医学文献检索助手。你的任务是把医学文稿中的句子改写成一组检索问题，"
    "用于在权威医学知识库（指南、药品说明书、教科书）中核查该句的事实准确性。"
)
_REWRITE_USER_TMPL = """原句：{sentence}

请生成 {n} 个用于检索核查的问题，要求：
1. 第 1 条必须原样保留原句；
2. 提取句中的医学实体（疾病、症状、药物、检查、指标、剂量等），围绕关键实体生成核查问题；
3. 从不同角度出题：定义/诊断标准、正常值范围、治疗方案与剂量、指南推荐、鉴别要点；
4. 问题要短、可直接用于搜索引擎或文献库检索；
5. 共 {n} 条，以 JSON 数组返回。"""


def _noop_emit(_event: str, _data: dict) -> None:
    pass


def rewrite_queries(sentence: str, n: int) -> tuple[list[str], bool]:
    """LLM 查询重写。返回 (问题列表, 是否 LLM 重写成功)；失败降级为 [原句]。"""
    try:
        result = chat_json(
            _REWRITE_SYSTEM,
            _REWRITE_USER_TMPL.format(sentence=sentence, n=n),
            schema_hint={"questions": [sentence, "问题2", "……"]},
        )
    except LLMNotConfiguredError:
        return [sentence], False  # 未配置 LLM：降级原句检索
    except Exception:
        return [sentence], False  # 重写失败（超时/解析失败）：不中断流水线
    if isinstance(result, dict):
        questions = result.get("questions") or result.get("queries") or []
    elif isinstance(result, list):
        questions = result
    else:
        questions = []
    cleaned: list[str] = []
    for q in questions:
        if isinstance(q, str) and q.strip() and q.strip() not in cleaned:
            cleaned.append(q.strip())
    if sentence not in cleaned:
        cleaned.insert(0, sentence)  # 强制原句为第 1 条（DMQR-RAG：保留原始查询入池）
    cleaned = cleaned[:n]
    return (cleaned, True) if len(cleaned) > 1 else ([sentence], False)


def rrf_fuse(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """跨查询 RRF 融合（Reciprocal Rank Fusion，与 LangChain EnsembleRetriever 同算法）：
    score(d) = Σ_q 1/(k + rank_q(d))，rank 从 1 起；k=60 为业界默认常数
    （Cormack et al., SIGIR 2009；调研笔记 §2）。LangChain 无跨查询独立融合组件，按公式实现。
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return scores


def _search_question(query: str, vector: list[float], v_limit: int, b_limit: int):
    """单问两路检索：向量路（LanceDB cosine）+ 关键词路（BM25）。供线程池并行调用。"""
    v_hits = store.vector_search(vector, limit=v_limit)
    b_hits = store.bm25_search(query, limit=b_limit)
    return v_hits, b_hits


def retrieve_for_sentence(sentence: str) -> tuple[list[str], list[dict[str, Any]], bool]:
    """对单句执行完整混合检索。返回 (问题列表, 证据列表, 是否 LLM 重写)。

    证据：{chunk_id, text, source_name, source(vector|keyword), rank, score(RRF 融合分)}。
    """
    n = retrieve_query_count()
    v_topk = retrieve_vector_topk()
    b_topk = retrieve_bm25_topk()
    rrf_k = retrieve_rrf_k()

    questions, rewritten = rewrite_queries(sentence, n)
    if store.count_chunks() == 0:
        return questions, [], rewritten

    # 全部问题一次性批量编码（BGE-M3 本地推理 batch 更快），随后逐问并行打两路
    q_vectors = EmbeddingProvider.get().embed(questions)
    v_limit, b_limit = v_topk * 3, b_topk * 3  # 融合前每问每路取 k*3 候选
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(
                lambda args: _search_question(*args),
                [(q, v, v_limit, b_limit) for q, v in zip(questions, q_vectors)],
            )
        )

    candidate_meta: dict[str, dict[str, Any]] = {}
    v_rankings: list[list[str]] = []
    b_rankings: list[list[str]] = []
    for v_hits, b_hits in results:
        v_rankings.append([h["chunk_id"] for h in v_hits])
        for h in v_hits:
            candidate_meta[h["chunk_id"]] = h
        b_rankings.append([d.metadata["chunk_id"] for d in b_hits])
        for d in b_hits:
            candidate_meta[d.metadata["chunk_id"]] = {
                "chunk_id": d.metadata["chunk_id"],
                "text": d.page_content,
                "source_name": d.metadata.get("source_name", ""),
            }

    # 每路内部跨问题 RRF 融合 → 各路 top-k
    v_scores = rrf_fuse(v_rankings, k=rrf_k)
    b_scores = rrf_fuse(b_rankings, k=rrf_k)
    v_top = sorted(v_scores, key=v_scores.get, reverse=True)[:v_topk]
    b_top = sorted(b_scores, key=b_scores.get, reverse=True)[:b_topk]

    # 两路合并去重（chunk_id）：同 chunk 取 RRF 分高的一路定 source 标签
    merged: dict[str, dict[str, Any]] = {}
    for rank, cid in enumerate(v_top, start=1):
        merged[cid] = {"source": "vector", "rank": rank, "score": v_scores[cid]}
    for rank, cid in enumerate(b_top, start=1):
        if cid not in merged or b_scores[cid] > merged[cid]["score"]:
            merged[cid] = {"source": "keyword", "rank": rank, "score": b_scores[cid]}

    evidences = [
        {
            "chunk_id": cid,
            "text": candidate_meta[cid]["text"],
            "source_name": candidate_meta[cid].get("source_name", ""),
            **entry,
        }
        for cid, entry in merged.items()
    ]
    evidences.sort(key=lambda e: e["score"], reverse=True)
    return questions, evidences, rewritten


def _target_sentences(document_id: str) -> list[tuple[Sentence, bool]]:
    """文档全部句子及其是否跳过标记。跳过：参考文献块（可配置）+ 表格占位符句。"""
    include_references = review_references()
    with Session(engine) as session:
        blocks = session.exec(
            select(Block).where(Block.document_id == document_id).order_by(Block.idx)
        ).all()
        result: list[tuple[Sentence, bool]] = []
        for block in blocks:
            block_skipped = block.is_reference and not include_references
            sentences = session.exec(
                select(Sentence).where(Sentence.block_id == block.id).order_by(Sentence.idx)
            ).all()
            for sentence in sentences:
                skipped = block_skipped or PLACEHOLDER_RE.match(sentence.text) is not None
                result.append((Sentence(id=sentence.id, idx=sentence.idx, block_id=sentence.block_id, text=sentence.text), skipped))
        return result


def retrieve_document(document_id: str, emit: Emit = _noop_emit) -> dict[str, Any]:
    """对文档全部待审校句子执行混合检索，queries/evidence 入库（重跑先清旧结果）。"""
    targets = _target_sentences(document_id)
    sentence_ids = [s.id for s, _ in targets]
    with Session(engine) as session:
        if sentence_ids:
            session.exec(delete(Query).where(Query.sentence_id.in_(sentence_ids)))
            session.exec(delete(Evidence).where(Evidence.sentence_id.in_(sentence_ids)))
            session.commit()

    total = sum(1 for _, skipped in targets if not skipped)
    emit("start", {"sentences": total, "skipped": len(targets) - total})
    done = 0
    evidence_count = 0
    rewritten_count = 0
    for sentence, skipped in targets:
        if skipped:
            continue
        questions, evidences, rewritten = retrieve_for_sentence(sentence.text)
        rewritten_count += 1 if rewritten else 0
        with Session(engine) as session:
            for idx, q in enumerate(questions):
                session.add(Query(sentence_id=sentence.id, idx=idx, text=q))
            for e in evidences:
                session.add(
                    Evidence(
                        sentence_id=sentence.id,
                        source=e["source"],
                        chunk_text=e["text"],
                        doc_name=e["source_name"],
                        score=round(float(e["score"]), 6),
                        rank=e["rank"],
                    )
                )
            session.commit()
        done += 1
        evidence_count += len(evidences)
        emit(
            "progress",
            {
                "current": done,
                "total": total,
                "sentence": sentence.text[:40],
                "queries": len(questions),
                "evidence": len(evidences),
                "rewritten": rewritten,
            },
        )
    emit(
        "done",
        {"sentences": done, "evidence": evidence_count, "rewritten": rewritten_count},
    )
    return {"sentences": done, "evidence": evidence_count, "rewritten": rewritten_count}
