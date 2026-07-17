"""人工决定接口：单条 decision（接受/保留原文/自定义/撤销）+ 批量处理（设计文档 §5.2⑤）。

- decision 语义沿用旧版：accepted=采纳修订(2) / rejected=保留原文(1) / custom=自定义(3)；
  pending = 撤销回待决定。每条决定即写库（decided_at），可随时关闭续作。
- 全部决定完成（无 pending）时文档状态 → manual_done；撤销回 pending 时 → pending_manual。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.db import engine
from app.models import Block, Correction, Document, Sentence
from app.pipeline.review import refresh_document_review_status

router = APIRouter(tags=["corrections"])

DECISIONS = ("accepted", "rejected", "custom", "pending")


def _correction_json(c: Correction) -> dict:
    try:
        evidence_ids = json.loads(c.evidence_ids or "[]")
    except json.JSONDecodeError:
        evidence_ids = []
    return {
        "id": c.id,
        "sentence_id": c.sentence_id,
        "original": c.original,
        "suggestion": c.suggestion,
        "error_type": c.error_type,
        "severity": c.severity,
        "explanation": c.explanation,
        "evidence_ids": evidence_ids,
        "decision": c.decision,
        "custom_text": c.custom_text,
        "decided_at": c.decided_at.isoformat() if c.decided_at else None,
    }


class DecisionPayload(BaseModel):
    decision: Literal["accepted", "rejected", "custom", "pending"]
    custom_text: Optional[str] = None


@router.post("/corrections/{correction_id}/decision")
def decide_correction(correction_id: int, payload: DecisionPayload) -> dict:
    """单条决定：accepted(2 采纳) / rejected(1 保留原文) / custom(3 自定义) / pending(撤销)。"""
    if payload.decision == "custom" and not (payload.custom_text or "").strip():
        raise HTTPException(status_code=400, detail="自定义决定必须提供 custom_text")
    with Session(engine) as session:
        correction = session.get(Correction, correction_id)
        if correction is None:
            raise HTTPException(status_code=404, detail="correction 不存在")
        sentence = session.get(Sentence, correction.sentence_id)
        block = session.get(Block, sentence.block_id) if sentence is not None else None
        doc = session.get(Document, block.document_id) if block is not None else None
        if doc is None:
            raise HTTPException(status_code=404, detail="correction 关联文档不存在")
        doc_id = doc.id

        correction.decision = payload.decision
        if payload.decision == "pending":  # 撤销
            correction.decided_at = None
            correction.custom_text = None
        else:
            correction.decided_at = datetime.utcnow()
            correction.custom_text = (
                payload.custom_text.strip() if payload.decision == "custom" else None
            )
        session.add(correction)
        session.commit()
        session.refresh(correction)
        result = _correction_json(correction)

    return {"correction": result, "document_status": refresh_document_review_status(doc_id)}


class BatchFilter(BaseModel):
    severity: Optional[str] = None
    error_type: Optional[str] = None
    decision: str = "pending"  # 默认只处理待决定项


class BatchPayload(BaseModel):
    filter: BatchFilter = BatchFilter()
    action: Literal["accept", "reject"]


@router.post("/documents/{document_id}/decisions/batch")
def batch_decide(document_id: str, payload: BatchPayload) -> dict:
    """批量决定：按 severity / error_type / decision 过滤后统一 accept / reject，返回影响数。"""
    with Session(engine) as session:
        doc = session.get(Document, document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="文档不存在")
        block_ids = [
            b.id
            for b in session.exec(select(Block).where(Block.document_id == document_id)).all()
        ]
        if not block_ids:
            return {"affected": 0, "document_status": doc.status}
        sentence_ids = list(
            session.exec(select(Sentence.id).where(Sentence.block_id.in_(block_ids))).all()
        )
        stmt = select(Correction).where(
            Correction.sentence_id.in_(sentence_ids),
            Correction.decision == payload.filter.decision,
        )
        if payload.filter.severity:
            stmt = stmt.where(Correction.severity == payload.filter.severity)
        if payload.filter.error_type:
            stmt = stmt.where(Correction.error_type == payload.filter.error_type)
        rows = list(session.exec(stmt).all())
        now = datetime.utcnow()
        decision = "accepted" if payload.action == "accept" else "rejected"
        for row in rows:
            row.decision = decision
            row.custom_text = None
            row.decided_at = now
            session.add(row)
        session.commit()
        affected = len(rows)
    return {"affected": affected, "document_status": refresh_document_review_status(document_id)}
