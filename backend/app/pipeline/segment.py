"""② segment：SaT 句子分割 + 章节分块入库。

- SentenceSplitter 单例懒加载 wtpsplit.SaT("sat-3l-sm")；加载失败回退中文标点正则分句
  （与调研笔记 §1 一致；模型下载支持 HF_ENDPOINT 环境变量，如 https://hf-mirror.com）。
  测试/离线场景可设 AI_REVIEW_SEGMENTER=rule 强制走正则。
- 短句碎片（< segment.min_sentence_length，默认 10）合并入前一句，不丢弃文本。
- 章节边界：Markdown 标题行（# 开头）与「一、」「（一）」正则模式。
- 连续 [N]: 开头的行识别为参考文献区，单独成 block 且 is_reference=True（默认不审校）。
- 单块超过 MAX_BLOCK_CHARS 时在句子边界拆分。
"""
from __future__ import annotations

import os
import re

from sqlalchemy import delete
from sqlmodel import Session, select

from app.core.db import engine
from app.core.user_settings import min_sentence_length
from app.models import Block, Correction, Evidence, Query, Sentence
from app.pipeline.common import project_dir, set_document_status

MAX_BLOCK_CHARS = 1000
_CHAPTER_TITLE_MAX_LEN = 60

_FALLBACK_RE = re.compile(r"([。!?;；\n]|(?<!\d)\.(?!\d))")
_MD_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
_CHAPTER_RE = re.compile(r"^\s*(?:[一二三四五六七八九十百]+、|（[一二三四五六七八九十]+）)")
_REF_LINE_RE = re.compile(r"^\s*\[\d+\]\s*[:：]")
_PLACEHOLDER_LINE_RE = re.compile(r"^\[\{表格不予审校_\d+\}\]$")


class SentenceSplitter:
    """SaT 单例；加载失败（含未下载模型）时回退正则分句。"""

    _instance: "SentenceSplitter | None" = None

    def __init__(self) -> None:
        self._sat = None
        self.backend = "rule"
        if os.environ.get("AI_REVIEW_SEGMENTER", "sat").lower() == "rule":
            return
        try:
            from wtpsplit import SaT

            from app.core.config import sat_model_dir, sat_tokenizer_dir

            model_path = sat_model_dir()
            if model_path is not None:
                # 本地预下载的模型目录（环境变量显式指定，或 <data_dir>/models/sat-3l-sm 自动探测）
                tokenizer = sat_tokenizer_dir()
                tokenizer_path = str(tokenizer) if tokenizer is not None else "facebookAI/xlm-roberta-base"
                self._sat = SaT(str(model_path), tokenizer_name_or_path=tokenizer_path)
            else:
                # 首次自动从 HF Hub 下载到 ~/.cache/huggingface（可用 HF_ENDPOINT 镜像）
                self._sat = SaT("sat-3l-sm")
            self.backend = "sat"
        except Exception:
            self._sat = None
            self.backend = "rule"

    @classmethod
    def get(cls) -> "SentenceSplitter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """测试用：清除单例缓存。"""
        cls._instance = None

    def split(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        if self._sat is not None:
            try:
                return [s for s in (s.strip() for s in self._sat.split(text)) if s]
            except Exception:
                pass  # 推理异常时落回正则，不中断流水线
        return self._rule_split(text)

    @staticmethod
    def _rule_split(text: str) -> list[str]:
        """中文标点正则分句：分隔符并回前一句结尾。"""
        parts = _FALLBACK_RE.split(text)
        sentences: list[str] = []
        for i, part in enumerate(parts):
            if i % 2 == 1:  # 捕获组（标点/换行）
                if sentences:
                    sentences[-1] += part
                elif part.strip():
                    sentences.append(part)
            elif part.strip():
                sentences.append(part.strip())
        return [s for s in sentences if s.strip()]


def merge_short_sentences(sentences: list[str], min_len: int) -> list[str]:
    """句长 < min_len 的碎片合并入前一句；开头的碎片向后并入下一句。不丢弃任何文本。"""
    merged: list[str] = []
    pending = ""
    for sentence in sentences:
        if pending:
            sentence = pending + sentence
            pending = ""
        if len(sentence) < min_len:
            if merged:
                merged[-1] += sentence
            else:
                pending = sentence
        else:
            merged.append(sentence)
    if pending:
        if merged:
            merged[-1] += pending
        else:
            merged.append(pending)
    return merged


def _save_blocks(doc_id: str, blocks: list[dict]) -> None:
    """重跑前清理旧 blocks/sentences（含下游 queries/evidence/corrections，防孤儿行）。"""
    with Session(engine) as session:
        old_block_ids = [
            b.id for b in session.exec(select(Block).where(Block.document_id == doc_id)).all()
        ]
        if old_block_ids:
            old_sentence_ids = session.exec(
                select(Sentence.id).where(Sentence.block_id.in_(old_block_ids))
            ).all()
            if old_sentence_ids:
                session.exec(delete(Query).where(Query.sentence_id.in_(old_sentence_ids)))
                session.exec(delete(Evidence).where(Evidence.sentence_id.in_(old_sentence_ids)))
                session.exec(delete(Correction).where(Correction.sentence_id.in_(old_sentence_ids)))
            session.exec(delete(Sentence).where(Sentence.block_id.in_(old_block_ids)))
        session.exec(delete(Block).where(Block.document_id == doc_id))
        session.commit()

        for block_idx, block_data in enumerate(blocks):
            block = Block(
                document_id=doc_id,
                idx=block_idx,
                chapter=block_data["chapter"],
                is_reference=block_data["is_reference"],
                text="\n".join(block_data["sentences"]),
            )
            session.add(block)
            session.flush()  # 取回自增主键
            for sent_idx, sent_text in enumerate(block_data["sentences"]):
                session.add(Sentence(block_id=block.id, idx=sent_idx, text=sent_text))
        session.commit()


def segment_document(doc_id: str) -> dict:
    """读 parsed.md → SaT 分句 → 章节/参考文献分块 → blocks/sentences 入库。

    成功：状态 parsed → segmented；失败：记 error 并置 failed 后重新抛出。
    """
    parsed_path = project_dir(doc_id) / "parsed.md"
    if not parsed_path.exists():
        raise FileNotFoundError("parsed.md 不存在，请先完成解析（ingest）")

    try:
        text = parsed_path.read_text(encoding="utf-8")
        splitter = SentenceSplitter.get()
        min_len = min_sentence_length()

        blocks: list[dict] = []
        current_chapter: str | None = None
        current_sentences: list[str] = []
        current_is_reference = False

        def flush() -> None:
            nonlocal current_sentences
            if current_sentences:
                blocks.append(
                    {
                        "chapter": current_chapter,
                        "is_reference": current_is_reference,
                        "sentences": current_sentences,
                    }
                )
            current_sentences = []

        def add_sentence(sentence: str, *, is_reference: bool = False) -> None:
            nonlocal current_is_reference
            if is_reference != current_is_reference:
                flush()
                current_is_reference = is_reference
            current_len = sum(len(s) for s in current_sentences)
            if current_sentences and current_len + len(sentence) > MAX_BLOCK_CHARS:
                flush()  # 单块超长时在句子边界拆分（chapter / is_reference 延续）
            current_sentences.append(sentence)

        def start_chapter(title: str) -> None:
            nonlocal current_chapter, current_is_reference
            flush()
            current_chapter = title
            current_is_reference = False
            current_sentences.append(title)  # 标题本身保留为块内首句，不丢文本

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            heading = _MD_HEADING_RE.match(line)
            if heading:
                start_chapter(heading.group(2))
                continue
            if _CHAPTER_RE.match(line) and len(line) <= _CHAPTER_TITLE_MAX_LEN:
                start_chapter(line)
                continue
            if _REF_LINE_RE.match(line):
                add_sentence(line, is_reference=True)
                continue
            if _PLACEHOLDER_LINE_RE.match(line):
                # 表格占位符独立成句，不参与分句与短句合并（导出时按占位符还原表格）
                add_sentence(line)
                continue
            for sentence in merge_short_sentences(splitter.split(line), min_len):
                add_sentence(sentence)
        flush()

        _save_blocks(doc_id, blocks)
        set_document_status(doc_id, "segmented")
        return {
            "blocks": len(blocks),
            "sentences": sum(len(b["sentences"]) for b in blocks),
            "segmenter": splitter.backend,
        }
    except Exception as exc:
        set_document_status(doc_id, "failed", str(exc))
        raise
