"""④ review：以 block 为单位的 LLM 结构化审校（设计文档 §5.2④）。

流程：
1. 前置校验：文档存在且状态可审校（segmented / retrieved / pending_manual / manual_done，
   可重跑）；LLM 配置预检失败（LLMNotConfiguredError）在任何数据/状态变更之前抛出。
2. 清理旧 corrections：默认只清 decision=pending 的（已人工决定的保留，且对应句子跳过本次审校）；
   force=True 时全清重审。
3. 逐 block 送审（跳过 is_reference 块，除非 segment.review_references=true；
   跳过纯表格占位符 block，占位符句不参与编号）：
   - system = settings review.prompt（默认内置医学审校模板，见 user_settings.DEFAULT_REVIEW_PROMPT）
   - user = 块原文（句子编号 [S1][S2]…）+ 每句证据（编号 [E1][E2]…，含 向量/关键词 与来源标签；
     无证据逐句注明；全块无证据时附加"纯 LLM 审校"提示——兼容未 retrieve / 检索关闭两种前置状态）
   - chat_json 结构化输出 corrections：sentence_id / original / suggestion /
     error_type(事实错误|术语错误|语法错误|格式错误) / severity(high|medium|low) /
     evidence_ids[] / explanation
   - 校验：sentence_id 必须在块内编号范围、original 非空；非法条目丢弃并记 job_events 警告；
     error_type/severity 越界时按默认值收敛（不丢条目）；evidence_ids 映射回该句 evidence 行 id
   - 每 block 一条 progress 事件
4. corrections 入库（decision=pending）；状态 reviewing → pending_manual；
   若审校后无任何 pending 决定（如无 corrections 或重跑时全部已决定）→ manual_done。
   LLM 调用中途失败：状态置 failed 并抛出（API 层转 500）。
"""
from __future__ import annotations

import json
from typing import Any, Callable

from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.db import engine
from app.core.user_settings import llm_config, review_prompt, review_references
from app.llm.client import LLMNotConfiguredError, chat_json
from app.models import Block, Correction, Document, Evidence, Sentence
from app.pipeline.common import set_document_status
from app.rag.retrieve import PLACEHOLDER_RE

Emit = Callable[[str, dict], None]

REVIEWABLE_STATUSES = ("segmented", "retrieved", "pending_manual", "manual_done")
# failed 也允许重试审校（审校失败保留分句数据）；但解析阶段就失败的文档没有 blocks，需先重新解析
RETRYABLE_STATUSES = REVIEWABLE_STATUSES + ("failed",)

ERROR_TYPES = ("事实错误", "术语错误", "语法错误", "格式错误")
SEVERITIES = ("high", "medium", "low")
_DEFAULT_ERROR_TYPE = "格式错误"
_DEFAULT_SEVERITY = "medium"

_SOURCE_LABELS = {"vector": "向量", "keyword": "关键词"}

_SCHEMA_HINT = {
    "corrections": [
        {
            "sentence_id": 1,
            "original": "句中被修改的片段（逐字摘录）",
            "suggestion": "修改后的对应文本",
            "error_type": "事实错误|术语错误|语法错误|格式错误",
            "severity": "high|medium|low",
            "evidence_ids": [1],
            "explanation": "问题说明；事实性判断须引用证据编号，如 [E1]",
        }
    ]
}


def _noop_emit(_event: str, _data: dict) -> None:
    pass


def _check_llm_configured() -> None:
    """LLM 配置预检：在任何数据/状态变更前抛出 LLMNotConfiguredError（API 层转 400）。"""
    cfg = llm_config()
    if not cfg["api_key"]:
        raise LLMNotConfiguredError("未配置 LLM API Key，请到设置页填写 llm.api_key")
    if not cfg["base_url"]:
        raise LLMNotConfiguredError("未配置 LLM Base URL，请到设置页填写 llm.base_url")
    if not cfg["model"]:
        raise LLMNotConfiguredError("未配置 LLM 模型，请到设置页填写 llm.model")


def _sentence_evidence(session: Session, sentence_id: int) -> list[Evidence]:
    """单句证据，按 score 降序（同分按 id 升序）——与 prompt 中 [E] 编号顺序一致。"""
    return list(
        session.exec(
            select(Evidence)
            .where(Evidence.sentence_id == sentence_id)
            .order_by(Evidence.score.desc(), Evidence.id)
        ).all()
    )


def build_user_prompt(numbered: list[tuple[int, Sentence, list[Evidence]]]) -> str:
    """构造审校 user prompt：块原文（[S] 编号）+ 每句证据（[E] 编号，含来源标签）。

    numbered：[(句子编号, Sentence, 该句证据列表)]；全块无证据时附加纯 LLM 审校提示。
    """
    lines: list[str] = ["请审校以下文稿块：", "", "【正文】"]
    for num, sentence, _ in numbered:
        lines.append(f"[S{num}] {sentence.text}")
    lines += ["", "【检索证据】"]
    any_evidence = False
    for num, _, evidences in numbered:
        if not evidences:
            lines.append(f"[S{num}]：无检索证据。")
            continue
        any_evidence = True
        lines.append(f"[S{num}] 的证据：")
        for idx, e in enumerate(evidences, start=1):
            label = _SOURCE_LABELS.get(e.source, e.source)
            lines.append(f"[E{idx}]（{label} · 来源《{e.doc_name}》）{e.chunk_text}")
    if not any_evidence:
        lines.append(
            "（本次审校未启用检索或知识库无相关内容，请基于医学常识审慎判断；"
            "事实性结论请在 explanation 中注明无检索证据支持。）"
        )
    lines += ["", "请逐句检查并输出 corrections（无问题的块返回空数组）。"]
    return "\n".join(lines)


def parse_corrections(
    payload: Any,
    numbered: list[tuple[int, Sentence, list[Evidence]]],
    warn: Callable[[str], None],
) -> list[dict[str, Any]]:
    """解析并校验 LLM 输出的 corrections。

    校验规则：sentence_id 在块内编号范围、original/suggestion 非空——非法条目丢弃并 warn；
    error_type/severity 越界收敛为默认值（保留条目）；evidence_ids 按该句 [E] 编号映射回 evidence 行 id。
    """
    if isinstance(payload, dict):
        items = payload.get("corrections") or []
    elif isinstance(payload, list):
        items = payload
    else:
        warn(f"审校输出不是对象/数组：{type(payload).__name__}，已忽略")
        return []
    if not isinstance(items, list):
        warn("corrections 字段不是数组，已忽略")
        return []

    by_num = {num: (sentence, evidences) for num, sentence, evidences in numbered}
    parsed: list[dict[str, Any]] = []
    for pos, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            warn(f"第 {pos} 条 correction 不是对象，已丢弃")
            continue
        try:
            sentence_num = int(item.get("sentence_id"))
        except (TypeError, ValueError):
            warn(f"第 {pos} 条 sentence_id 非法（{item.get('sentence_id')!r}），已丢弃")
            continue
        match = by_num.get(sentence_num)
        if match is None:
            warn(f"第 {pos} 条 sentence_id={sentence_num} 不在本块编号范围，已丢弃")
            continue
        sentence, evidences = match
        original = str(item.get("original") or "").strip()
        suggestion = str(item.get("suggestion") or "").strip()
        if not original:
            warn(f"第 {pos} 条（[S{sentence_num}]）original 为空，已丢弃")
            continue
        if not suggestion:
            warn(f"第 {pos} 条（[S{sentence_num}]）suggestion 为空，已丢弃")
            continue
        error_type = str(item.get("error_type") or "").strip()
        if error_type not in ERROR_TYPES:
            error_type = _DEFAULT_ERROR_TYPE
        severity = str(item.get("severity") or "").strip().lower()
        if severity not in SEVERITIES:
            severity = _DEFAULT_SEVERITY
        evidence_db_ids: list[int] = []
        raw_ids = item.get("evidence_ids") or []
        if isinstance(raw_ids, (list, tuple)):
            for raw in raw_ids:
                try:
                    num = int(raw)
                except (TypeError, ValueError):
                    continue
                if 1 <= num <= len(evidences):
                    ev_id = evidences[num - 1].id
                    if ev_id is not None and ev_id not in evidence_db_ids:
                        evidence_db_ids.append(ev_id)
        parsed.append(
            {
                "sentence": sentence,
                "original": original,
                "suggestion": suggestion,
                "error_type": error_type,
                "severity": severity,
                "evidence_ids": evidence_db_ids,
                "explanation": str(item.get("explanation") or "").strip(),
            }
        )
    return parsed


def _doc_sentence_ids(session: Session, doc_id: str) -> list[int]:
    block_ids = [
        b.id for b in session.exec(select(Block).where(Block.document_id == doc_id)).all()
    ]
    if not block_ids:
        return []
    return list(session.exec(select(Sentence.id).where(Sentence.block_id.in_(block_ids))).all())


def pending_correction_count(session: Session, doc_id: str) -> int:
    sentence_ids = _doc_sentence_ids(session, doc_id)
    if not sentence_ids:
        return 0
    return len(
        session.exec(
            select(Correction.id).where(
                Correction.sentence_id.in_(sentence_ids), Correction.decision == "pending"
            )
        ).all()
    )


def refresh_document_review_status(doc_id: str) -> str:
    """决定流公共收口：无 pending corrections → manual_done，否则 → pending_manual。"""
    with Session(engine) as session:
        pending = pending_correction_count(session, doc_id)
        doc = session.get(Document, doc_id)
        if doc is None:
            raise KeyError(f"文档不存在: {doc_id}")
        doc.status = "manual_done" if pending == 0 else "pending_manual"
        doc.error = None
        session.add(doc)
        session.commit()
        return doc.status


def review_document(doc_id: str, emit: Emit = _noop_emit, force: bool = False) -> dict[str, Any]:
    """对文档执行 LLM 结构化审校，corrections 入库（decision=pending）。

    可重跑：默认清 pending、保留已人工决定（对应句子跳过）；force=True 全清重审。
    LLM 未配置 → 预检抛 LLMNotConfiguredError，数据与状态均不变。
    """
    with Session(engine) as session:
        doc = session.get(Document, doc_id)
        if doc is None:
            raise KeyError(f"文档不存在: {doc_id}")
        if doc.status not in RETRYABLE_STATUSES:
            raise ValueError(f"当前状态 {doc.status} 不能审校，请先完成解析分句")
        if doc.status == "failed":
            # 失败重试的前置：分句数据仍在（解析阶段失败的文档无 blocks，必须重新解析）
            has_blocks = (
                session.exec(select(Block.id).where(Block.document_id == doc_id).limit(1)).first()
                is not None
            )
            if not has_blocks:
                raise ValueError("文档尚未完成解析分句，请先重新运行「解析」")

    _check_llm_configured()  # 前置失败：不改数据、不动状态

    # 清理旧 corrections（默认只清 pending；force 全清）
    with Session(engine) as session:
        sentence_ids = _doc_sentence_ids(session, doc_id)
        if sentence_ids:
            if force:
                session.exec(delete(Correction).where(Correction.sentence_id.in_(sentence_ids)))
            else:
                session.exec(
                    delete(Correction).where(
                        Correction.sentence_id.in_(sentence_ids),
                        Correction.decision == "pending",
                    )
                )
            session.commit()
        # 已人工决定的句子本次跳过（force 时为空集）
        decided_sentence_ids: set[int] = set()
        if sentence_ids:
            decided_sentence_ids = set(
                session.exec(
                    select(Correction.sentence_id).where(
                        Correction.sentence_id.in_(sentence_ids),
                        Correction.decision != "pending",
                    )
                ).all()
            )

    set_document_status(doc_id, "reviewing")
    include_references = review_references()

    with Session(engine) as session:
        blocks = list(
            session.exec(
                select(Block).where(Block.document_id == doc_id).order_by(Block.idx)
            ).all()
        )
        # 取出快照（脱离 session 使用）
        block_rows = [(b.id, b.idx, b.chapter, b.is_reference, b.text) for b in blocks]

    try:
        total_new = 0
        reviewed_blocks = 0
        skipped_blocks = 0
        warnings = 0
        emit("start", {"blocks": len(block_rows), "force": force})

        for block_id, block_idx, chapter, is_reference, _text in block_rows:
            if is_reference and not include_references:
                skipped_blocks += 1
                emit(
                    "progress",
                    {"block_idx": block_idx, "blocks": len(block_rows), "skipped": "reference"},
                )
                continue
            with Session(engine) as session:
                sentences = list(
                    session.exec(
                        select(Sentence).where(Sentence.block_id == block_id).order_by(Sentence.idx)
                    ).all()
                )
                targets = [
                    s
                    for s in sentences
                    if PLACEHOLDER_RE.match(s.text) is None and s.id not in decided_sentence_ids
                ]
                numbered = [
                    (num, s, _sentence_evidence(session, s.id))
                    for num, s in enumerate(targets, start=1)
                ]
            if not numbered:
                skipped_blocks += 1
                emit(
                    "progress",
                    {"block_idx": block_idx, "blocks": len(block_rows), "skipped": "empty"},
                )
                continue

            user_prompt = build_user_prompt(numbered)
            block_warnings: list[str] = []
            payload = chat_json(
                review_prompt(), user_prompt, schema_hint=_SCHEMA_HINT
            )  # LLMNotConfiguredError / 调用异常：向外抛（finally 置 failed）
            entries = parse_corrections(payload, numbered, warn=block_warnings.append)
            for message in block_warnings:
                warnings += 1
                emit("warning", {"block_idx": block_idx, "message": message})

            with Session(engine) as session:
                for entry in entries:
                    session.add(
                        Correction(
                            sentence_id=entry["sentence"].id,
                            original=entry["original"],
                            suggestion=entry["suggestion"],
                            error_type=entry["error_type"],
                            severity=entry["severity"],
                            explanation=entry["explanation"],
                            evidence_ids=json.dumps(
                                entry["evidence_ids"], ensure_ascii=False
                            ),
                            decision="pending",
                        )
                    )
                session.commit()
            reviewed_blocks += 1
            total_new += len(entries)
            emit(
                "progress",
                {
                    "block_idx": block_idx,
                    "blocks": len(block_rows),
                    "chapter": chapter,
                    "sentences": len(numbered),
                    "corrections": len(entries),
                },
            )

        status = refresh_document_review_status(doc_id)
        emit(
            "done",
            {
                "status": status,
                "blocks_reviewed": reviewed_blocks,
                "blocks_skipped": skipped_blocks,
                "corrections": total_new,
                "warnings": warnings,
            },
        )
        return {
            "status": status,
            "blocks_reviewed": reviewed_blocks,
            "blocks_skipped": skipped_blocks,
            "corrections": total_new,
            "warnings": warnings,
        }
    except LLMNotConfiguredError:
        # 运行中配置被清空：回到可审校前置状态，便于配置后重试
        set_document_status(doc_id, "segmented")
        raise
    except Exception as exc:
        set_document_status(doc_id, "failed", str(exc))
        emit("error", {"message": str(exc)})
        raise
