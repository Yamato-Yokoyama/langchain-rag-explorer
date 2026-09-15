"""
src/load_resume.py

レジュメ JSON(data/resume/*.json)を Document のリストに変換する Loader。
load_receipts.py / load_linkedin.py と同じインターフェース(list[Document])で、
rag_pipeline に統合しやすくする。セクション(contact/education/experience/projects/skills)
ごとに1 Document に分け、metadata に resume_version と section を付与して
「BCG版ではどのプロジェクト経験を書いたか」のような絞り込みができるようにする。
"""
import json

from pathlib import Path
from langchain_core.documents import Document


def load_resume_from_json(filepath: str) -> list[Document]:
    """レジュメ JSON を、セクションごとの Document のリストに変換する。"""
    data = json.loads(Path(filepath).read_text(encoding="utf-8"))
    resume_version = data.get("resume_version", "unknown")

    docs: list[Document] = [_contact_document(data, filepath, resume_version)]
    docs.extend(_education_documents(data, filepath, resume_version))
    docs.extend(_experience_documents(data, filepath, resume_version))
    docs.extend(_project_documents(data, filepath, resume_version))
    docs.append(_skills_document(data, filepath, resume_version))
    return docs


def _contact_document(data: dict, filepath: str, resume_version: str) -> Document:
    contact = data.get("contact", {})
    text = (
        f"{data.get('name', '')} の連絡先。"
        f"所在地: {contact.get('location', '')}。"
        f"LinkedIn: {contact.get('linkedin', '')}。GitHub: {contact.get('github', '')}。"
    )
    return Document(
        page_content=text,
        metadata={"source": filepath, "resume_version": resume_version, "section": "contact"},
    )


def _education_documents(data: dict, filepath: str, resume_version: str) -> list[Document]:
    docs = []
    for edu in data.get("education", []):
        text = (
            f"{edu.get('institution', '')}({edu.get('period', '')})で"
            f"{edu.get('degree', '')}。関連コースワーク: {', '.join(edu.get('coursework', []))}。"
        )
        docs.append(Document(
            page_content=text,
            metadata={
                "source": filepath,
                "resume_version": resume_version,
                "section": "education",
                "institution": edu.get("institution"),
            },
        ))
    return docs


def _experience_documents(data: dict, filepath: str, resume_version: str) -> list[Document]:
    docs = []
    for exp in data.get("experience", []):
        bullets = "\n".join(f"- {b}" for b in exp.get("bullets", []))
        text = f"{exp.get('title', '')} — {exp.get('org', '')}({exp.get('period', '')})\n{bullets}"
        docs.append(Document(
            page_content=text,
            metadata={
                "source": filepath,
                "resume_version": resume_version,
                "section": "experience",
                "org": exp.get("org"),
            },
        ))
    return docs


def _project_documents(data: dict, filepath: str, resume_version: str) -> list[Document]:
    docs = []
    for proj in data.get("projects", []):
        bullets = "\n".join(f"- {b}" for b in proj.get("bullets", []))
        text = f"{proj.get('name', '')}({proj.get('status', '')})\n{bullets}"
        docs.append(Document(
            page_content=text,
            metadata={
                "source": filepath,
                "resume_version": resume_version,
                "section": "projects",
                "name": proj.get("name"),
            },
        ))
    return docs


def _skills_document(data: dict, filepath: str, resume_version: str) -> Document:
    skills = data.get("skills", {})
    lines = [f"{category}: {', '.join(items)}" for category, items in skills.items()]
    lines.append("Languages: " + ", ".join(data.get("languages", [])))
    if data.get("work_authorization"):
        lines.append("Work Authorization: " + data["work_authorization"])

    return Document(
        page_content="\n".join(lines),
        metadata={"source": filepath, "resume_version": resume_version, "section": "skills"},
    )
