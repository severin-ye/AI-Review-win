"""M4 审校测试：prompt 构建 / corrections 解析校验 / review API（mock LLM）/ 决定流 / 批量 / 重跑。

- LLM 一律 mock（monkeypatch app.pipeline.review.chat_json），不发起真实请求；
  review API 为后台线程执行，测试用 GET /api/jobs/{id} 轮询等待完成。
- 文档不经 docx 上传，直接 DB 落种 Document/Block/Sentence/Evidence，速度快且无文件依赖。
- 环境隔离同 M2/M3：导入 app 前设置 AI_REVIEW_DATA_DIR / AI_REVIEW_SEGMENTER=rule；
  与其他测试模块同跑时引擎绑定首个导入模块的数据目录。
"""
import json
import os
import tempfile
import time

_tmp = tempfile.mkdtemp(prefix="ai-review-test-review-")
os.environ.setdefault("AI_REVIEW_DATA_DIR", _tmp)
os.environ.setdefault("AI_REVIEW_SEGMENTER", "rule")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from app.core.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Block, Correction, Document, Evidence, Sentence  # noqa: E402
from app.pipeline import review as review_mod  # noqa: E402

DUMMY_LLM_SETTINGS = {
    "llm.base_url": "http://127.0.0.1:9/v1",  # 永不可达，但 chat_json 已被 mock
    "llm.api_key": "sk-test",
    "llm.model": "test-model",
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        assert c.put("/api/settings", json=DUMMY_LLM_SETTINGS).status_code == 200
        yield c


def seed_document(
    status: str = "segmented",
    blocks: list[dict] | None = None,
    evidence: dict[int, list[dict]] | None = None,
) -> str:
    """直接 DB 落种文档。blocks: [{sentences: [...], is_reference: bool}]；
    evidence: {(block_idx, sentence_idx): [ {source, chunk_text, doc_name, score, rank} ]}"""
    blocks = blocks or [{"sentences": ["患者血压控制良好。", "建议每日服用阿司匹林200mg。"]}]
    with Session(engine) as session:
        doc = Document(filename="review-test.docx", status=status)
        session.add(doc)
        session.commit()
        session.refresh(doc)
        for b_idx, spec in enumerate(blocks):
            block = Block(
                document_id=doc.id,
                idx=b_idx,
                chapter=spec.get("chapter"),
                is_reference=spec.get("is_reference", False),
                text="\n".join(spec["sentences"]),
            )
            session.add(block)
            session.flush()
            for s_idx, text in enumerate(spec["sentences"]):
                sentence = Sentence(block_id=block.id, idx=s_idx, text=text)
                session.add(sentence)
                session.flush()
                for e_idx, ev in enumerate((evidence or {}).get((b_idx, s_idx), [])):
                    session.add(
                        Evidence(
                            sentence_id=sentence.id,
                            source=ev.get("source", "vector"),
                            chunk_text=ev["chunk_text"],
                            doc_name=ev.get("doc_name", "指南.pdf"),
                            score=ev.get("score", 0.5 - e_idx * 0.01),
                            rank=ev.get("rank", e_idx + 1),
                        )
                    )
        session.commit()
        return doc.id


def doc_status(doc_id: str) -> str:
    with Session(engine) as session:
        return session.get(Document, doc_id).status


def doc_corrections(doc_id: str) -> list[Correction]:
    with Session(engine) as session:
        block_ids = [
            b.id for b in session.exec(select(Block).where(Block.document_id == doc_id)).all()
        ]
        sentence_ids = session.exec(
            select(Sentence.id).where(Sentence.block_id.in_(block_ids))
        ).all()
        return list(
            session.exec(
                select(Correction)
                .where(Correction.sentence_id.in_(sentence_ids))
                .order_by(Correction.id)
            ).all()
        )


def wait_job(client: TestClient, job_id: str, timeout: float = 15.0) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = client.get(f"/api/jobs/{job_id}").json()["status"]
        if status in ("done", "error"):
            return status
        time.sleep(0.1)
    raise AssertionError(f"job {job_id} 超时未完成")


def run_review(client: TestClient, monkeypatch, doc_id: str, payload, force: bool = False) -> dict:
    """mock chat_json 并触发 POST /review，等待后台线程完成，返回 (job 终态, done 事件数据)。"""
    monkeypatch.setattr(review_mod, "chat_json", lambda *a, **kw: payload)
    resp = client.post(f"/api/documents/{doc_id}/review", params={"force": str(force).lower()})
    assert resp.status_code == 200, resp.text
    job_id = resp.json()["job_id"]
    final = wait_job(client, job_id)
    return {"job_id": job_id, "job_status": final}


# ---------- prompt 构建 ----------


def _numbered(sentences: list[str], evidence_map: dict[int, list[Evidence]] | None = None):
    """构造 build_user_prompt 入参：[(编号, Sentence, [Evidence])]"""
    rows = []
    for i, text in enumerate(sentences, start=1):
        rows.append((i, Sentence(id=i, block_id=1, idx=i - 1, text=text), (evidence_map or {}).get(i, [])))
    return rows


def _ev(ev_id: int, source: str = "vector", doc_name: str = "高血压指南.pdf", text: str = "证据文本") -> Evidence:
    return Evidence(
        id=ev_id, sentence_id=1, source=source, chunk_text=text, doc_name=doc_name, score=0.5, rank=1
    )


def test_prompt_with_evidence_numbering():
    numbered = _numbered(
        ["第一句。", "第二句。"],
        {
            1: [
                _ev(11, "vector", "高血压指南.pdf", "收缩压≥140mmHg可诊断高血压。"),
                _ev(12, "keyword", "说明书.pdf", "阿司匹林常用剂量75-100mg。"),
            ]
        },
    )
    prompt = review_mod.build_user_prompt(numbered)
    assert "[S1] 第一句。" in prompt
    assert "[S2] 第二句。" in prompt
    assert "[E1]（向量 · 来源《高血压指南.pdf》）收缩压≥140mmHg可诊断高血压。" in prompt
    assert "[E2]（关键词 · 来源《说明书.pdf》）" in prompt
    assert "[S2]：无检索证据。" in prompt  # 单句无证据分支
    assert "未启用检索" not in prompt  # 有证据时不出现纯 LLM 提示


def test_prompt_no_evidence_branch():
    prompt = review_mod.build_user_prompt(_numbered(["第一句。", "第二句。"]))
    assert "[S1]：无检索证据。" in prompt
    assert "[S2]：无检索证据。" in prompt
    assert "未启用检索或知识库无相关内容" in prompt  # 全块无证据提示


# ---------- corrections 解析与校验 ----------


def test_parse_corrections_validation():
    numbered = _numbered(["第一句。", "第二句。"], {2: [_ev(7), _ev(8)]})
    warnings: list[str] = []
    payload = {
        "corrections": [
            {  # 合法条目（含类型/严重度/证据映射）
                "sentence_id": 2,
                "original": "第二",
                "suggestion": "第三",
                "error_type": "事实错误",
                "severity": "high",
                "evidence_ids": [1, 2, 99, "x"],  # 99/非法 丢弃，1/2 映射 DB id
                "explanation": "依据 [E1]",
            },
            {"sentence_id": 99, "original": "x", "suggestion": "y"},  # 编号越界 → 丢弃
            {"sentence_id": 1, "original": "  ", "suggestion": "y"},  # original 空 → 丢弃
            {"sentence_id": 1, "original": "x", "suggestion": ""},  # suggestion 空 → 丢弃
            {"sentence_id": "abc", "original": "x", "suggestion": "y"},  # 编号非法 → 丢弃
            "not-a-dict",  # 非对象 → 丢弃
            {  # 类型/严重度越界 → 收敛默认值，保留条目
                "sentence_id": 1,
                "original": "第一",
                "suggestion": "第零",
                "error_type": "瞎编类型",
                "severity": "critical",
            },
        ]
    }
    entries = review_mod.parse_corrections(payload, numbered, warn=warnings.append)
    assert len(entries) == 2
    assert entries[0]["sentence"].text == "第二句。"
    assert entries[0]["error_type"] == "事实错误"
    assert entries[0]["severity"] == "high"
    assert entries[0]["evidence_ids"] == [7, 8]
    assert entries[1]["error_type"] == "格式错误"
    assert entries[1]["severity"] == "medium"
    assert len(warnings) == 5  # 5 条非法丢弃


def test_parse_corrections_bare_list_and_bad_payload():
    numbered = _numbered(["第一句。"])
    entries = review_mod.parse_corrections(
        [{"sentence_id": 1, "original": "第一", "suggestion": "第零"}], numbered, warn=lambda m: None
    )
    assert len(entries) == 1  # 兼容裸数组输出
    warnings: list[str] = []
    assert review_mod.parse_corrections("garbage", numbered, warn=warnings.append) == []
    assert warnings  # 非对象/数组 → 警告


# ---------- review API（mock LLM） ----------


def test_review_api_mock_llm(client: TestClient, monkeypatch):
    doc_id = seed_document(
        status="segmented",
        blocks=[
            {"chapter": "一、病例", "sentences": ["患者血压控制良好。", "建议每日服用阿司匹林200mg。"]},
            {"sentences": ["[1]: 张三. 中华医学杂志, 2020."], "is_reference": True},
            {"sentences": ["[{表格不予审校_1}]"]},
        ],
        evidence={
            (0, 1): [
                {"source": "vector", "chunk_text": "阿司匹林常用剂量每日75至100mg。", "doc_name": "说明书.pdf", "score": 0.9, "rank": 1},
                {"source": "keyword", "chunk_text": "长期服用阿司匹林需注意出血风险。", "doc_name": "指南.pdf", "score": 0.8, "rank": 1},
            ]
        },
    )
    captured: dict = {}

    def fake_chat_json(system, user, schema_hint=None):
        captured["system"] = system
        captured["user"] = user
        return {
            "corrections": [
                {
                    "sentence_id": 2,
                    "original": "阿司匹林200mg",
                    "suggestion": "阿司匹林100mg",
                    "error_type": "事实错误",
                    "severity": "high",
                    "evidence_ids": [1],
                    "explanation": "剂量超出说明书常规范围，见 [E1]",
                }
            ]
        }

    monkeypatch.setattr(review_mod, "chat_json", fake_chat_json)
    resp = client.post(f"/api/documents/{doc_id}/review")
    assert resp.status_code == 200, resp.text
    job_id = resp.json()["job_id"]
    assert wait_job(client, job_id) == "done"

    assert doc_status(doc_id) == "pending_manual"
    corrections = doc_corrections(doc_id)
    assert len(corrections) == 1
    c = corrections[0]
    assert c.decision == "pending"
    assert c.error_type == "事实错误" and c.severity == "high"
    assert json.loads(c.evidence_ids) != []

    # prompt 只含正文块的 2 句（参考文献块与占位符块被跳过），证据带编号与来源标签
    assert "[S1] 患者血压控制良好。" in captured["user"]
    assert "[S2] 建议每日服用阿司匹林200mg。" in captured["user"]
    assert "[E1]（向量 · 来源《说明书.pdf》）" in captured["user"]
    assert "参考文献" not in captured["user"] and "表格不予审校" not in captured["user"]
    assert "审校" in captured["system"]  # 默认医学审校模板

    # SSE 事件：start / 每 block progress / done 已落 job_events
    events = []
    with Session(engine) as session:
        from app.models import JobEvent

        for row in session.exec(select(JobEvent).where(JobEvent.job_id == job_id)).all():
            events.append(row.event)
    assert "start" in events and "progress" in events and "done" in events

    # detail 扩展：sentences 携带 corrections 与 evidence
    detail = client.get(f"/api/documents/{doc_id}/detail").json()
    s2 = detail["blocks"][0]["sentences"][1]
    assert s2["corrections"][0]["suggestion"] == "阿司匹林100mg"
    assert s2["corrections"][0]["decision"] == "pending"
    assert len(s2["evidence"]) == 2


def test_review_llm_not_configured(client: TestClient):
    doc_id = seed_document(status="retrieved")
    # 清空 LLM 配置（settings 实时读库）
    assert client.put(
        "/api/settings", json={"llm.base_url": "", "llm.api_key": "", "llm.model": ""}
    ).status_code == 200
    try:
        resp = client.post(f"/api/documents/{doc_id}/review")
        assert resp.status_code == 400
        assert "llm" in resp.json()["detail"]
        assert doc_status(doc_id) == "retrieved"  # 状态回退不变
        assert doc_corrections(doc_id) == []  # 无数据变更
    finally:
        assert client.put("/api/settings", json=DUMMY_LLM_SETTINGS).status_code == 200


def test_review_bad_status_rejected(client: TestClient):
    doc_id = seed_document(status="uploaded")
    resp = client.post(f"/api/documents/{doc_id}/review")
    assert resp.status_code == 400


# ---------- 决定流 ----------


def _reviewed_doc(client: TestClient, monkeypatch, n_corrections: int = 2) -> str:
    """落种 + mock 审校出 n 条 pending corrections 的文档。"""
    doc_id = seed_document(
        status="retrieved",
        blocks=[{"sentences": ["第一句内容足够长。", "第二句内容足够长。", "第三句内容足够长。"]}],
    )
    payload = {
        "corrections": [
            {
                "sentence_id": i + 1,
                "original": f"第{'一二三'[i]}句",
                "suggestion": f"修改{i + 1}",
                "error_type": "语法错误",
                "severity": ["high", "low", "low"][i],
                "explanation": "",
            }
            for i in range(n_corrections)
        ]
    }
    run_review(client, monkeypatch, doc_id, payload)
    return doc_id


def test_decision_flow_accept_reject_custom_undo(client: TestClient, monkeypatch):
    doc_id = _reviewed_doc(client, monkeypatch, n_corrections=2)
    corrections = doc_corrections(doc_id)
    assert len(corrections) == 2 and doc_status(doc_id) == "pending_manual"

    # accept
    resp = client.post(
        f"/api/corrections/{corrections[0].id}/decision", json={"decision": "accepted"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["correction"]["decision"] == "accepted"
    assert body["correction"]["decided_at"] is not None
    assert body["document_status"] == "pending_manual"  # 还剩 1 条 pending

    # custom（缺 custom_text → 400）
    resp = client.post(
        f"/api/corrections/{corrections[1].id}/decision", json={"decision": "custom"}
    )
    assert resp.status_code == 400
    # custom 正常
    resp = client.post(
        f"/api/corrections/{corrections[1].id}/decision",
        json={"decision": "custom", "custom_text": "人工改写文本"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["correction"]["custom_text"] == "人工改写文本"
    assert body["document_status"] == "manual_done"  # 全部决定完成

    # 撤销 → 回 pending，文档回 pending_manual
    resp = client.post(
        f"/api/corrections/{corrections[0].id}/decision", json={"decision": "pending"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["correction"]["decision"] == "pending"
    assert body["correction"]["decided_at"] is None
    assert body["document_status"] == "pending_manual"

    # reject
    resp = client.post(
        f"/api/corrections/{corrections[0].id}/decision", json={"decision": "rejected"}
    )
    assert resp.json()["document_status"] == "manual_done"


def test_batch_decisions_filter_and_count(client: TestClient, monkeypatch):
    doc_id = _reviewed_doc(client, monkeypatch, n_corrections=3)

    # 只接受 low（2 条）
    resp = client.post(
        f"/api/documents/{doc_id}/decisions/batch",
        json={"filter": {"severity": "low"}, "action": "accept"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["affected"] == 2
    assert body["document_status"] == "pending_manual"  # high 仍 pending

    # 剩余 pending 全部拒绝
    resp = client.post(
        f"/api/documents/{doc_id}/decisions/batch",
        json={"filter": {}, "action": "reject"},
    )
    body = resp.json()
    assert body["affected"] == 1
    assert body["document_status"] == "manual_done"

    decisions = {c.severity: c.decision for c in doc_corrections(doc_id)}
    assert decisions == {"high": "rejected", "low": "accepted"}

    # 空过滤 + 无匹配 → 0
    resp = client.post(
        f"/api/documents/{doc_id}/decisions/batch",
        json={"filter": {"error_type": "术语错误"}, "action": "accept"},
    )
    assert resp.json()["affected"] == 0


# ---------- 重跑 ----------


def test_rerun_keeps_decided_and_skips_sentences(client: TestClient, monkeypatch):
    doc_id = _reviewed_doc(client, monkeypatch, n_corrections=2)
    corrections = doc_corrections(doc_id)
    decided_id = corrections[0].id
    client.post(f"/api/corrections/{decided_id}/decision", json={"decision": "accepted"})

    # 重跑：mock 返回新 correction（落在第 3 句）；已决定句应不出现在 prompt
    captured: dict = {}

    def fake_chat_json(system, user, schema_hint=None):
        captured["user"] = user
        return {
            "corrections": [
                {
                    "sentence_id": 2,  # 编号基于跳过已决定句后的剩余句：原第3句 → S2
                    "original": "第三句",
                    "suggestion": "改三",
                    "error_type": "格式错误",
                    "severity": "low",
                }
            ]
        }

    monkeypatch.setattr(review_mod, "chat_json", fake_chat_json)
    resp = client.post(f"/api/documents/{doc_id}/review")
    assert wait_job(client, resp.json()["job_id"]) == "done"

    assert "第一句内容足够长。" not in captured["user"]  # 已决定句跳过
    assert "第三句内容足够长。" in captured["user"]
    after = doc_corrections(doc_id)
    assert len(after) == 2  # 已决定 1 + 新 pending 1（旧 pending 被清）
    kept = [c for c in after if c.id == decided_id]
    assert kept and kept[0].decision == "accepted"
    assert {c.decision for c in after} == {"accepted", "pending"}


def test_rerun_force_clears_decided(client: TestClient, monkeypatch):
    doc_id = _reviewed_doc(client, monkeypatch, n_corrections=2)
    decided_id = doc_corrections(doc_id)[0].id
    client.post(f"/api/corrections/{decided_id}/decision", json={"decision": "accepted"})

    run_review(client, monkeypatch, doc_id, {"corrections": []}, force=True)
    remaining = doc_corrections(doc_id)
    assert all(c.id != decided_id for c in remaining)  # force 全清
    assert doc_status(doc_id) == "manual_done"  # 无 pending → manual_done
