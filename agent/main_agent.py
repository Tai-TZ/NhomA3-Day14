import asyncio
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data.knowledge_base import DOC_CATALOG

# Synonym map cho V2 retrieval cải tiến
SYNONYMS = {
    "password": "mật khẩu",
    "mật khẩu": "password",
    "2fa": "xác thực",
    "otp": "xác thực",
    "invoice": "hóa đơn",
    "api": "endpoint",
    "gdpr": "privacy",
    "downtime": "sự cố",
    "outage": "sự cố",
}


class MainAgent:
    """Agent V1 — mock RAG với keyword matching cơ bản."""

    def __init__(self, version: str = "v1"):
        self.name = f"SupportAgent-{version}"
        self.version = version

    def _expand_query(self, question: str) -> str:
        q = question.lower()
        for src, dst in SYNONYMS.items():
            if src in q:
                q += f" {dst}"
        return q

    def _mock_retrieve(self, question: str, boost_exact: bool = False) -> List[str]:
        q = self._expand_query(question) if self.version == "v2" else question.lower()
        scored = []

        for doc_id, doc in DOC_CATALOG.items():
            score = sum(1 for kw in doc["keywords"] if kw in q)
            if boost_exact and doc["content"].lower()[:30] in q:
                score += 2
            scored.append((score, doc_id))

        scored.sort(key=lambda x: x[0], reverse=True)
        ranked = [doc_id for score, doc_id in scored if score > 0]
        ranked += [doc_id for score, doc_id in scored if score == 0]
        return ranked[:5]

    async def query(self, question: str) -> Dict:
        sleep_time = 0.03 if self.version == "v2" else 0.05
        await asyncio.sleep(sleep_time)

        boost = self.version == "v2"
        retrieved_ids = self._mock_retrieve(question, boost_exact=boost)
        tokens_used = 100 + len(question.split()) * (6 if self.version == "v2" else 8)

        top_doc = DOC_CATALOG.get(retrieved_ids[0], {})
        content_snippet = top_doc.get("content", "")[:120]

        return {
            "answer": (
                f"Dựa trên tài liệu [{retrieved_ids[0]}], "
                f"tôi xin trả lời: {content_snippet}"
            ),
            "retrieved_ids": retrieved_ids,
            "contexts": [
                DOC_CATALOG.get(rid, {}).get("content", "") for rid in retrieved_ids[:2]
            ],
            "metadata": {
                "model": "gpt-4o-mini",
                "tokens_used": tokens_used,
                "agent_version": self.version,
                "sources": [f"{doc_id}.pdf" for doc_id in retrieved_ids[:2]],
            },
        }


class MainAgentV2(MainAgent):
    """Agent V2 — cải tiến retrieval (synonym expansion + exact boost)."""

    def __init__(self):
        super().__init__(version="v2")


if __name__ == "__main__":
    agent = MainAgent()

    async def test():
        resp = await agent.query("Làm thế nào để đổi mật khẩu?")
        print(resp)

    asyncio.run(test())
