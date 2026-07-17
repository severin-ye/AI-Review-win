"""模型管理接口（设计文档 §7、§9）：本地模型状态查询 + hf-mirror 预下载。

- GET /api/models/status：SaT（sat-3l-sm + xlm-roberta-base tokenizer）与
  BGE-M3 的本地存在状态、目录大小、是否已加载（只读探测，不触发模型加载）。
- POST /api/models/download：后台线程用 curl 从 hf-mirror 逐文件下载缺失模型
  （-C - 断点续传，与 M2/M3 文档的手工下载命令一致），进度经 jobs/SSE 推送。
  下载完成后 SentenceSplitter / EmbeddingProvider 单例自动生效
  （core.config 的 <data_dir>/models/ 自动探测；已加载的旧实例不强制卸载，
  需重启后端或下次进程启动时切换——测试/隔离场景不受影响）。
"""
from __future__ import annotations

import shutil
import subprocess
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import (
    EMBEDDING_MODEL_DIRNAME,
    SAT_MODEL_DIRNAME,
    SAT_TOKENIZER_DIRNAME,
    embedding_model_dir,
    models_dir,
    sat_model_dir,
    sat_tokenizer_dir,
)
from app.core.joblog import create_job, finish_job, make_emit, record_event

router = APIRouter(prefix="/models", tags=["models"])

HF_MIRROR = "https://hf-mirror.com"

# 下载清单：模型键 → (目标子目录, HF 仓库, 文件列表)
MODEL_MANIFESTS: dict[str, tuple[str, str, list[str]]] = {
    "sat": (
        SAT_MODEL_DIRNAME,
        "segment-any-text/sat-3l-sm",
        ["config.json", "model.safetensors"],
    ),
    "sat-tokenizer": (
        SAT_TOKENIZER_DIRNAME,
        "FacebookAI/xlm-roberta-base",
        ["tokenizer.json", "tokenizer_config.json", "sentencepiece.bpe.model"],
    ),
    "bge-m3": (
        EMBEDDING_MODEL_DIRNAME,
        "BAAI/bge-m3",
        [
            "config.json",
            "pytorch_model.bin",
            "tokenizer.json",
            "tokenizer_config.json",
            "sentencepiece.bpe.model",
            "special_tokens_map.json",
            "modules.json",
            "config_sentence_transformers.json",
            "sentence_bert_config.json",
            "1_Pooling/config.json",
        ],
    ),
}

_DOWNLOAD_LOCK = threading.Lock()


def _dir_size(path: Path) -> tuple[int, int]:
    """(总字节数, 文件数)；目录不存在返回 (0, 0)。"""
    if not path.exists():
        return 0, 0
    total = 0
    count = 0
    for item in path.rglob("*"):
        if item.is_file():
            count += 1
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total, count


def _sat_loaded() -> bool:
    from app.pipeline.segment import SentenceSplitter

    inst = SentenceSplitter._instance
    return bool(inst is not None and inst.backend == "sat")


def _bge_loaded() -> bool:
    from app.rag.embeddings import EmbeddingProvider

    inst = EmbeddingProvider._instance
    return bool(inst is not None and inst._st_model is not None)


@router.get("/status")
def models_status() -> dict:
    """模型状态：是否存在（目录）、大小、必需文件齐不齐、是否已加载。"""
    sat_dir = sat_model_dir() or (models_dir() / SAT_MODEL_DIRNAME)
    tok_dir = sat_tokenizer_dir() or (models_dir() / SAT_TOKENIZER_DIRNAME)
    bge_dir = embedding_model_dir() or (models_dir() / EMBEDDING_MODEL_DIRNAME)

    def entry(path: Path, required: list[str], loaded: bool) -> dict:
        size, files = _dir_size(path)
        missing = [f for f in required if not (path / f).exists()]
        return {
            "path": str(path),
            "exists": path.exists(),
            "size_bytes": size,
            "file_count": files,
            "missing_files": missing,
            "ready": path.exists() and not missing,
            "loaded": loaded,
        }

    return {
        "models_dir": str(models_dir()),
        "sat": entry(sat_dir, MODEL_MANIFESTS["sat"][2], _sat_loaded()),
        "sat_tokenizer": entry(tok_dir, MODEL_MANIFESTS["sat-tokenizer"][2], _sat_loaded()),
        "bge_m3": entry(bge_dir, MODEL_MANIFESTS["bge-m3"][2], _bge_loaded()),
    }


class DownloadPayload(BaseModel):
    models: list[str] = ["sat", "sat-tokenizer", "bge-m3"]


def _curl_file(url: str, dest: Path) -> tuple[bool, str]:
    """curl -L --retry 3 -C - 断点续传单文件；返回 (成功, stderr 摘要)。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    curl = shutil.which("curl") or "curl"
    proc = subprocess.run(
        [curl, "-L", "--retry", "3", "-C", "-", "-f", "-sS", "-o", str(dest), url],
        capture_output=True,
        text=True,
        timeout=7200,
    )
    if proc.returncode != 0:
        return False, (proc.stderr or f"exit {proc.returncode}").strip()[-300:]
    return True, ""


def _download_worker(job_id: str, keys: list[str]) -> None:
    emit = make_emit(job_id)
    try:
        total = sum(len(MODEL_MANIFESTS[k][2]) for k in keys)
        emit("start", {"models": keys, "files": total})
        done_files = 0
        failures: list[dict] = []
        for key in keys:
            dirname, repo, files = MODEL_MANIFESTS[key]
            dest_dir = models_dir() / dirname
            for filename in files:
                dest = dest_dir / filename
                url = f"{HF_MIRROR}/{repo}/resolve/main/{filename}"
                if dest.exists() and dest.stat().st_size > 0:
                    done_files += 1
                    emit(
                        "progress",
                        {"model": key, "file": filename, "status": "exists",
                         "done": done_files, "total": total},
                    )
                    continue
                emit(
                    "progress",
                    {"model": key, "file": filename, "status": "downloading",
                     "done": done_files, "total": total},
                )
                ok, err = _curl_file(url, dest)
                if not ok:
                    dest.unlink(missing_ok=True)  # 清掉失败残留，避免误判为已存在
                    failures.append({"model": key, "file": filename, "error": err})
                    record_event(job_id, "warning", {"message": f"{key}/{filename} 下载失败: {err}"})
                    continue
                done_files += 1
                emit(
                    "progress",
                    {"model": key, "file": filename, "status": "done",
                     "bytes": dest.stat().st_size, "done": done_files, "total": total},
                )
        if failures:
            emit("error", {"message": f"{len(failures)} 个文件下载失败", "failures": failures})
            finish_job(job_id, "error")
        else:
            emit("done", {"models": keys, "files": done_files})
            finish_job(job_id, "done")
    except Exception as exc:  # noqa: BLE001 - 后台线程兜底，事件留痕
        record_event(job_id, "error", {"message": str(exc)})
        finish_job(job_id, "error")
    finally:
        _DOWNLOAD_LOCK.release()


@router.post("/download")
def download_models(payload: DownloadPayload) -> dict:
    """后台下载缺失模型文件（幂等：已存在且非空的文件跳过；同时间只允许一个下载任务）。"""
    keys = [k for k in payload.models if k in MODEL_MANIFESTS]
    if not keys:
        raise HTTPException(
            status_code=400,
            detail=f"未知模型：{payload.models}，可选 {sorted(MODEL_MANIFESTS)}",
        )
    if not _DOWNLOAD_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="已有模型下载任务进行中")
    try:
        job_id = create_job("model_download")
        threading.Thread(target=_download_worker, args=(job_id, keys), daemon=True).start()
    except Exception:
        _DOWNLOAD_LOCK.release()
        raise
    return {"job_id": job_id, "models": keys}
