"""EmbeddingProvider：统一的文本向量提供方（单例）。

三种 provider（settings 键 embedding.provider）：
- local  ：本地 sentence-transformers 加载 BGE-M3（默认 BAAI/bge-m3，normalize_embeddings=True）。
           支持环境变量 AI_REVIEW_EMBEDDING_MODEL_PATH 指向本地模型目录
           （与 M2 SaT 的 AI_REVIEW_SAT_MODEL_PATH 同模式，规避 HF Hub 直连失败的环境）。
- openai ：走 llm.base_url 的 /embeddings 接口（OpenAI 兼容），模型名取 settings embedding.model。
- stub   ：测试专用隐藏档——sha256 派生的确定性假向量（dim=32），不加载任何模型。

provider 按 settings 每次 encode 时动态读取，local 模型进程内只加载一次。
"""
from __future__ import annotations

import hashlib

import numpy as np

from app.core.user_settings import embedding_model, embedding_provider, llm_config

STUB_DIM = 32
BGE_M3_DIM = 1024


def _stub_embed(texts: list[str]) -> list[list[float]]:
    """确定性假向量：每个维度取 sha256(text#i) 的字节映射到 [-1,1]，最后 L2 归一化。"""
    vectors: list[list[float]] = []
    for text in texts:
        vec = np.empty(STUB_DIM, dtype=np.float32)
        for i in range(STUB_DIM):
            digest = hashlib.sha256(f"{text}#{i}".encode("utf-8")).digest()
            vec[i] = (digest[0] / 127.5) - 1.0
        norm = float(np.linalg.norm(vec)) or 1.0
        vectors.append((vec / norm).tolist())
    return vectors


class EmbeddingProvider:
    """embedding 单例；local 模式懒加载 sentence-transformers 模型。"""

    _instance: "EmbeddingProvider | None" = None

    def __init__(self) -> None:
        self._st_model = None  # sentence_transformers.SentenceTransformer
        self._st_model_key: str | None = None  # 已加载模型的标识（路径或 HF 名）

    @classmethod
    def get(cls) -> "EmbeddingProvider":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """测试用：清除单例与已加载模型。"""
        cls._instance = None

    @property
    def provider(self) -> str:
        return embedding_provider()

    def dim(self) -> int:
        """当前 provider 的向量维度（建 LanceDB 表用）。"""
        provider = self.provider
        if provider == "stub":
            return STUB_DIM
        if provider == "local":
            self._ensure_local_model()
            # sentence-transformers ≥5.6 改名 get_embedding_dimension；旧名回退兼容
            get_dim = getattr(self._st_model, "get_embedding_dimension", None)
            if get_dim is None:
                get_dim = self._st_model.get_sentence_embedding_dimension
            return int(get_dim())
        # openai 模式维度由远端模型决定；无法预知，按首次真实 encode 的返回建表
        return 0

    def _ensure_local_model(self):
        from app.core.config import embedding_model_dir

        model_dir = embedding_model_dir()
        # 本地目录（环境变量显式指定，或 <data_dir>/models/bge-m3 自动探测）优先；
        # 否则按 HF 名自动下载（可用 HF_ENDPOINT 镜像）
        key = str(model_dir) if model_dir is not None else embedding_model()
        if self._st_model is not None and self._st_model_key == key:
            return self._st_model
        from sentence_transformers import SentenceTransformer

        # 本地目录（hf-mirror curl 预下载）优先；否则按 HF 名自动下载（可用 HF_ENDPOINT 镜像）
        self._st_model = SentenceTransformer(key, device="cpu")
        self._st_model_key = key
        return self._st_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量编码文本为 L2 归一化向量。"""
        if not texts:
            return []
        provider = self.provider
        if provider == "stub":
            return _stub_embed(texts)
        if provider == "openai":
            return self._openai_embed(texts)
        model = self._ensure_local_model()
        result = model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=16,
            show_progress_bar=False,
        )
        return np.asarray(result, dtype=np.float32).tolist()

    def _openai_embed(self, texts: list[str]) -> list[list[float]]:
        cfg = llm_config()
        if not cfg["api_key"] or not cfg["base_url"]:
            raise RuntimeError("embedding.provider=openai 需要配置 llm.base_url / llm.api_key")
        from openai import OpenAI

        client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"], timeout=60.0)
        resp = client.embeddings.create(model=embedding_model(), input=texts)
        vectors = [item.embedding for item in sorted(resp.data, key=lambda d: d.index)]
        # 与 local 保持一致：L2 归一化（cosine 检索）
        arr = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (arr / norms).tolist()
