from __future__ import annotations

import hashlib
import html
import io
from html.parser import HTMLParser
import json
import mimetypes
import re
from pathlib import Path
from typing import Any
from uuid import uuid4
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .auth import decode_token, issue_token, verify_password
from .cache import ResponseCache
from .config import get_settings
from .database import Database, create_user, get_database, normalize_email, utc_now

settings = get_settings()
db = get_database()
response_cache = ResponseCache()

app = FastAPI(title=settings.app_name)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
class LoginPayload(BaseModel):
    email: str
    password: str
    role: str


class RegisterPayload(BaseModel):
    email: str
    password: str
    full_name: str
    grade_label: str | None = None


class SubmissionPayload(BaseModel):
    answer: str


class HintPayload(BaseModel):
    level: int = 1
    current_answer: str | None = None


VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class HtmlNode:
    def __init__(
        self,
        tag: str | None = None,
        attrs: list[tuple[str, str | None]] | None = None,
        text: str = "",
    ) -> None:
        self.tag = tag
        self.attrs = attrs or []
        self.text = text
        self.children: list[HtmlNode] = []

    def class_names(self) -> set[str]:
        class_attr = next((value for key, value in self.attrs if key == "class" and value), "")
        return set(class_attr.split())


class CardHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.root = HtmlNode("document")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = HtmlNode(tag, attrs)
        self.stack[-1].children.append(node)
        if tag.lower() not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack[-1].children.append(HtmlNode(tag, attrs))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(HtmlNode(text=data))

    def handle_entityref(self, name: str) -> None:
        self.handle_data(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.handle_data(f"&#{name};")


def serialize_node(node: HtmlNode) -> str:
    if node.tag is None:
        return node.text
    if node.tag == "document":
        return "".join(serialize_node(child) for child in node.children)
    attrs = "".join(
        f" {key}" if value is None else f' {key}="{html.escape(value, quote=True)}"'
        for key, value in node.attrs
    )
    if node.tag.lower() in VOID_TAGS:
        return f"<{node.tag}{attrs}>"
    return f"<{node.tag}{attrs}>{''.join(serialize_node(child) for child in node.children)}</{node.tag}>"


def text_content(node: HtmlNode) -> str:
    if node.tag in {"script", "style"}:
        return ""
    if node.tag is None:
        return html.unescape(node.text)
    return " ".join(part for child in node.children if (part := text_content(child).strip()))


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def has_class(node: HtmlNode, class_name: str) -> bool:
    return class_name in node.class_names()


def find_nodes(node: HtmlNode, predicate) -> list[HtmlNode]:
    matches = [node] if predicate(node) else []
    for child in node.children:
        matches.extend(find_nodes(child, predicate))
    return matches


def first_text(node: HtmlNode, class_names: tuple[str, ...]) -> str:
    for class_name in class_names:
        matches = find_nodes(node, lambda item: has_class(item, class_name))
        if matches:
            return normalize_space(text_content(matches[0]))
    return ""


def truncate_text(value: str, limit: int) -> str:
    cleaned = normalize_space(value)
    return cleaned if len(cleaned) <= limit else f"{cleaned[: limit - 1].rstrip()}…"


def minutes_from_text(value: str, default: int = 30) -> int:
    match = re.search(r"(\d+)", value)
    return int(match.group(1)) if match else default


def standalone_card_html(styles: str, card_html: str) -> str:
    return f"""<!doctype html>
<html lang="kk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
{styles}
body {{ margin: 0; padding: 18px; background: transparent; }}
.problem-card, .card {{ margin-left: auto !important; margin-right: auto !important; }}
</style>
</head>
<body>
{card_html}
<script>
function tog(id) {{
  var el = document.getElementById(id);
  if (!el) return;
  el.classList.toggle("visible");
  el.classList.toggle("open");
}}
</script>
</body>
</html>"""


def infer_grade_level(page_grade: str, card_grade: str) -> str:
    grade = card_grade or page_grade
    return grade.replace("сынып", "сынып").strip() or "Логикалық есептер"


def infer_difficulty(grade_level: str) -> str:
    if any(value in grade_level for value in ("10", "11")):
        return "Күрделі"
    if any(value in grade_level for value in ("8", "9")):
        return "Орташа"
    return "Бастапқы"


WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_docx_paragraphs(content: bytes, source_name: str) -> list[str]:
    try:
        with ZipFile(io.BytesIO(content)) as archive:
            raw_xml = archive.read("word/document.xml")
    except (BadZipFile, KeyError) as exc:
        raise HTTPException(status_code=422, detail=f"{source_name} дұрыс DOCX файлы емес") from exc
    root = ET.fromstring(raw_xml)
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{WORD_NS}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{WORD_NS}t"))
        cleaned = normalize_space(text)
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def parse_html_tasks(raw_html: str, source_name: str) -> list[dict[str, Any]]:
    parser = CardHtmlParser()
    parser.feed(raw_html)
    style_nodes = find_nodes(parser.root, lambda item: item.tag == "style")
    styles = "\n".join("".join(child.text for child in node.children if child.tag is None) for node in style_nodes)
    page_grade = first_text(parser.root, ("grade-tag", "main-sub"))
    cards = find_nodes(
        parser.root,
        lambda item: has_class(item, "problem-card") or (
            has_class(item, "card") and bool(first_text(item, ("card-title",)))
        ),
    )
    tasks: list[dict[str, Any]] = []
    for index, card in enumerate(cards, start=1):
        title = first_text(card, ("task-title", "card-title")) or f"{Path(source_name).stem} #{index}"
        grade = infer_grade_level(page_grade, first_text(card, ("grade-label", "tag-grade")))
        category = first_text(card, ("type-label", "tag-type")) or "Логика"
        condition = first_text(card, ("condition-text", "cond-text"))
        question = first_text(card, ("question-text", "q-text"))
        answer = first_text(card, ("answer-text", "ans-text")) or "Шешімі HTML карточкасының ішінде берілген"
        time_text = first_text(card, ("meta-row",))
        prompt = question or condition or title
        description = truncate_text(" ".join(part for part in (condition, question) if part), 360)
        tasks.append(
            {
                "title": title,
                "description": description or title,
                "prompt": truncate_text(prompt, 500),
                "answer": truncate_text(answer, 1000),
                "grade_level": grade,
                "category": category,
                "difficulty": infer_difficulty(grade),
                "status": "active",
                "estimated_minutes": minutes_from_text(time_text),
                "badge": "HTML",
                "badge_tone": "tertiary",
                "kind": "html",
                "question_type": "numeric",
                "content_html": standalone_card_html(styles, serialize_node(card)),
            }
        )
    if not tasks:
        raise HTTPException(status_code=422, detail=f"{source_name} ішінен тапсырма карточкалары табылмады")
    return tasks


def value_after_label(paragraphs: list[str], label: str) -> str:
    lowered = label.lower()
    for index, paragraph in enumerate(paragraphs):
        if paragraph.lower().startswith(lowered):
            inline = paragraph.split(":", 1)[1].strip() if ":" in paragraph else ""
            if inline:
                return inline
            for candidate in paragraphs[index + 1 : index + 4]:
                if candidate and not candidate.endswith(":"):
                    return candidate
    return ""


def infer_docx_grade(paragraphs: list[str], source_name: str) -> str:
    joined = " ".join([source_name, *paragraphs[:20]])
    match = re.search(r"(\d{1,2})\s*[-–]?\s*сынып", joined, re.IGNORECASE)
    if match:
        return f"{match.group(1)}-сынып"
    direct = value_after_label(paragraphs, "Сынып")
    if direct:
        return f"{direct.strip()}-сынып" if direct.strip().isdigit() else direct.strip()
    return "Логикалық есептер"


def infer_docx_topic(paragraphs: list[str], source_name: str) -> str:
    return value_after_label(paragraphs, "Тақырып") or Path(source_name).stem


def split_solution(text: str) -> tuple[str, str]:
    parts = re.split(r"(?:Шешімі|Жауабы)\s*[:：-]?", text, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return text.strip(), "Жауапты мұғалім тексереді. Шешу жолын толық жазыңыз."


def parse_docx_tasks(content: bytes, source_name: str, document_url: str) -> list[dict[str, Any]]:
    paragraphs = extract_docx_paragraphs(content, source_name)
    grade = infer_docx_grade(paragraphs, source_name)
    topic = infer_docx_topic(paragraphs, source_name)
    starts = [
        index
        for index, paragraph in enumerate(paragraphs)
        if re.match(r"^\d+\s*[-–]?\s*есеп\.?", paragraph, re.IGNORECASE)
    ]
    tasks: list[dict[str, Any]] = []
    if starts:
        for order, start in enumerate(starts):
            end = starts[order + 1] if order + 1 < len(starts) else min(len(paragraphs), start + 8)
            title = paragraphs[start]
            body = " ".join(paragraphs[start + 1 : end])
            prompt, answer = split_solution(body)
            tasks.append(
                {
                    "title": f"{grade}: {title}",
                    "description": truncate_text(prompt or topic, 360),
                    "prompt": truncate_text(prompt or title, 1000),
                    "answer": truncate_text(answer, 1400),
                    "grade_level": grade,
                    "category": topic,
                    "difficulty": infer_difficulty(grade),
                    "status": "active",
                    "image_url": None,
                    "document_url": document_url,
                    "document_name": source_name,
                    "estimated_minutes": 12,
                    "badge": "DOCX",
                    "badge_tone": "secondary",
                    "kind": "docx",
                    "question_type": "numeric",
                    "choices_json": None,
                    "content_html": None,
                }
            )
    else:
        prompt = next(
            (paragraph for paragraph in paragraphs if "?" in paragraph),
            "Құжаттағы материалды оқып, негізгі ойды қысқаша жазыңыз.",
        )
        tasks.append(
            {
                "title": f"{grade}: {topic}",
                "description": truncate_text(" ".join(paragraphs[:12]), 360),
                "prompt": truncate_text(prompt, 1000),
                "answer": "Жауапты мұғалім тексереді. Негізгі ой мен шешу жолы толық жазылуы керек.",
                "grade_level": grade,
                "category": topic,
                "difficulty": infer_difficulty(grade),
                "status": "active",
                "image_url": None,
                "document_url": document_url,
                "document_name": source_name,
                "estimated_minutes": 15,
                "badge": "DOCX",
                "badge_tone": "secondary",
                "kind": "docx",
                "question_type": "numeric",
                "choices_json": None,
                "content_html": None,
            }
        )
    if not tasks:
        raise HTTPException(status_code=422, detail=f"{source_name} ішінен тапсырма табылмады")
    return tasks


def make_etag(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()  # noqa: S324


def cached_payload(request: Request, key: str) -> Response | None:
    cached = response_cache.get(key)
    if cached is None:
        return None
    headers = {
        "ETag": cached.etag,
        "Cache-Control": "private, max-age=10, stale-while-revalidate=30",
    }
    if request.headers.get("if-none-match") == cached.etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    return JSONResponse(cached.payload, headers=headers)


def cache_response(key: str, payload: Any) -> JSONResponse:
    etag = make_etag(payload)
    response_cache.set(key, payload, settings.cache_ttl_seconds, etag)
    return JSONResponse(
        payload,
        headers={
            "ETag": etag,
            "Cache-Control": "private, max-age=10, stale-while-revalidate=30",
        },
    )


def normalize_task(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "prompt": row["prompt"],
        "answer": row["answer"],
        "gradeLevel": row["grade_level"],
        "category": row["category"],
        "difficulty": row["difficulty"],
        "status": row["status"],
        "imageUrl": row["image_url"],
        "documentUrl": row.get("document_url"),
        "documentName": row.get("document_name"),
        "estimatedMinutes": row["estimated_minutes"],
        "badge": row["badge"],
        "badgeTone": row["badge_tone"] or "primary",
        "questionType": row["question_type"],
        "choices": json.loads(row["choices_json"]) if row["choices_json"] else [],
        "contentHtml": row.get("content_html"),
        "updatedAt": row["updated_at"],
    }


def normalize_task_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "gradeLevel": row["grade_level"],
        "category": row["category"],
        "status": row["status"],
        "updatedAt": row["updated_at"],
    }


def serialize_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "email": row["email"],
        "role": row["role"],
        "fullName": row["full_name"],
        "gradeLabel": row["grade_label"],
        "initials": row["initials"],
        "avatarUrl": row["avatar_url"],
    }


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    user = db.fetchone("SELECT * FROM users WHERE id = ? LIMIT 1;", (int(payload["sub"]),))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return user


def require_role(required_role: str):
    def dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if user["role"] != required_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return user

    return dependency


def choose_value(
    payload: dict[str, Any],
    keys: tuple[str, ...],
    default: Any = None,
) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            value = payload[key]
            if not isinstance(value, str) or value.strip():
                return value
    return default


def ensure_text(value: Any, field_name: str, default: str | None = None) -> str:
    raw = default if value is None else value
    text = str(raw).strip() if raw is not None else ""
    if not text:
        raise HTTPException(status_code=422, detail=f"{field_name} is required")
    return text


def parse_int(value: Any, field_name: str, default: int) -> int:
    raw = default if value in (None, "") else value
    try:
        parsed = int(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} must be a number") from exc
    if parsed <= 0:
        raise HTTPException(status_code=422, detail=f"{field_name} must be greater than 0")
    return parsed


def parse_choices(value: Any) -> list[str]:
    if value in (None, "", []):
        return []
    if isinstance(value, list):
        parsed = [str(item).strip() for item in value if str(item).strip()]
        return parsed
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=422, detail="Жауап нұсқалары дұрыс JSON емес") from exc
            if not isinstance(data, list):
                raise HTTPException(status_code=422, detail="Жауап нұсқалары тізім болуы керек")
            return [str(item).strip() for item in data if str(item).strip()]
        return [item.strip() for item in stripped.split(",") if item.strip()]
    raise HTTPException(status_code=422, detail="Жауап нұсқалары тізім немесе мәтін болуы керек")


def validate_task_payload(
    payload: dict[str, Any],
    *,
    existing: dict[str, Any] | None = None,
    image_url: str | None = None,
    document_url: str | None = None,
    document_name: str | None = None,
) -> dict[str, Any]:
    title = ensure_text(choose_value(payload, ("title",), existing["title"] if existing else None), "title")
    prompt = ensure_text(choose_value(payload, ("prompt",), existing["prompt"] if existing else None), "prompt")
    answer = ensure_text(choose_value(payload, ("answer",), existing["answer"] if existing else None), "answer")
    description = str(
        choose_value(
            payload,
            ("description",),
            existing["description"] if existing else prompt,
        )
    ).strip() or prompt
    grade_level = ensure_text(
        choose_value(payload, ("grade_level", "gradeLevel"), existing["grade_level"] if existing else "7-сынып"),
        "grade_level",
    )
    category = ensure_text(
        choose_value(payload, ("category",), existing["category"] if existing else "Логика"),
        "category",
    )
    difficulty = ensure_text(
        choose_value(payload, ("difficulty",), existing["difficulty"] if existing else "Бастапқы"),
        "difficulty",
    )
    status_value = ensure_text(
        choose_value(payload, ("status_value", "status"), existing["status"] if existing else "draft"),
        "status",
    ).lower()
    if status_value not in {"active", "draft"}:
        raise HTTPException(status_code=422, detail="Күйі active немесе draft болуы керек")
    estimated_minutes = parse_int(
        choose_value(
            payload,
            ("estimated_minutes", "estimatedMinutes"),
            existing["estimated_minutes"] if existing else 15,
        ),
        "estimated_minutes",
        15,
    )
    question_type = ensure_text(
        choose_value(
            payload,
            ("question_type", "questionType"),
            existing["question_type"] if existing else "numeric",
        ),
        "question_type",
    ).lower()
    if question_type not in {"numeric", "choice"}:
        raise HTTPException(status_code=422, detail="Түрі numeric немесе choice болуы керек")
    parsed_choices = parse_choices(
        choose_value(
            payload,
            ("choices_json", "choices", "choicesJson"),
            existing["choices_json"] if existing else None,
        )
    )
    if question_type == "choice" and not parsed_choices:
        raise HTTPException(status_code=422, detail="Таңдау тапсырмасына кемінде бір нұсқа керек")
    final_image_url = image_url if image_url is not None else choose_value(
        payload,
        ("image_url", "imageUrl"),
        existing["image_url"] if existing else None,
    )
    final_document_url = document_url if document_url is not None else choose_value(
        payload,
        ("document_url", "documentUrl"),
        existing["document_url"] if existing else None,
    )
    final_document_name = document_name if document_name is not None else choose_value(
        payload,
        ("document_name", "documentName"),
        existing["document_name"] if existing else None,
    )
    return {
        "title": title,
        "description": description,
        "prompt": prompt,
        "answer": answer,
        "grade_level": grade_level,
        "category": category,
        "difficulty": difficulty,
        "status": status_value,
        "image_url": final_image_url,
        "document_url": final_document_url,
        "document_name": final_document_name,
        "estimated_minutes": estimated_minutes,
        "badge": choose_value(payload, ("badge",), existing["badge"] if existing else "Жаңа"),
        "badge_tone": choose_value(payload, ("badge_tone", "badgeTone"), existing["badge_tone"] if existing else "primary"),
        "kind": choose_value(payload, ("kind",), existing["kind"] if existing else "practice"),
        "question_type": question_type,
        "choices_json": json.dumps(parsed_choices) if question_type == "choice" else None,
        "content_html": choose_value(
            payload,
            ("content_html", "contentHtml"),
            existing.get("content_html") if existing else None,
        ),
    }


def insert_task_record(task_data: dict[str, Any], user_id: int) -> dict[str, Any]:
    now = utc_now()
    cursor = db.execute(
        """
        INSERT INTO tasks (
            title, description, prompt, answer, grade_level, category, difficulty,
            status, image_url, document_url, document_name, estimated_minutes, badge, badge_tone, kind,
            question_type, choices_json, content_html, created_by, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            task_data["title"],
            task_data["description"],
            task_data["prompt"],
            task_data["answer"],
            task_data["grade_level"],
            task_data["category"],
            task_data["difficulty"],
            task_data["status"],
            task_data["image_url"],
            task_data["document_url"],
            task_data["document_name"],
            task_data["estimated_minutes"],
            task_data["badge"],
            task_data["badge_tone"],
            task_data["kind"],
            task_data["question_type"],
            task_data["choices_json"],
            task_data["content_html"],
            user_id,
            now,
            now,
        ),
    )
    task = db.fetchone("SELECT * FROM tasks WHERE id = ? LIMIT 1;", (cursor.lastrowid,))
    if task is None:
        raise HTTPException(status_code=500, detail="Тапсырма жасалмады")
    return task


def update_task_record(task_id: int, task_data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    db.execute(
        """
        UPDATE tasks
        SET title = ?, description = ?, prompt = ?, answer = ?, grade_level = ?,
            category = ?, difficulty = ?, status = ?, image_url = ?, document_url = ?,
            document_name = ?, estimated_minutes = ?, badge = ?, badge_tone = ?, kind = ?,
            question_type = ?, choices_json = ?, content_html = ?,
            updated_at = ?
        WHERE id = ?;
        """,
        (
            task_data["title"],
            task_data["description"],
            task_data["prompt"],
            task_data["answer"],
            task_data["grade_level"],
            task_data["category"],
            task_data["difficulty"],
            task_data["status"],
            task_data["image_url"],
            task_data["document_url"],
            task_data["document_name"],
            task_data["estimated_minutes"],
            task_data["badge"],
            task_data["badge_tone"],
            task_data["kind"],
            task_data["question_type"],
            task_data["choices_json"],
            task_data["content_html"],
            now,
            task_id,
        ),
    )
    task = db.fetchone("SELECT * FROM tasks WHERE id = ? LIMIT 1;", (task_id,))
    if task is None:
        raise HTTPException(status_code=404, detail="Тапсырма табылмады")
    return task


def save_upload_bytes(content: bytes, filename: str, content_type: str | None = None) -> str:
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail="Жүктелген файл тым үлкен")
    suffix = Path(filename).suffix.lower() or mimetypes.guess_extension(content_type or "") or ".bin"
    stored_name = f"{uuid4().hex}{suffix}"
    destination = settings.uploads_dir / stored_name
    destination.write_bytes(content)
    return f"/uploads/{stored_name}"


def save_upload(file: UploadFile | None) -> str | None:
    if file is None or not file.filename:
        return None
    return save_upload_bytes(file.file.read(), file.filename, file.content_type)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post(f"{settings.api_prefix}/auth/login")
def login(payload: LoginPayload) -> dict[str, Any]:
    user = db.fetchone("SELECT * FROM users WHERE email = ? LIMIT 1;", (payload.email.lower(),))
    if user is None or user["role"] != payload.role or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = issue_token(user["id"], user["role"])
    return {"token": token, "user": serialize_user(user)}


def create_student_session(
    payload: RegisterPayload,
    database: Database | None = None,
) -> dict[str, Any]:
    active_db = database or db
    email = normalize_email(payload.email)
    full_name = normalize_space(payload.full_name)
    grade_label = normalize_space(payload.grade_label or "") or "Оқушы"

    if not EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(status_code=422, detail="Электронды пошта дұрыс емес")
    if not full_name:
        raise HTTPException(status_code=422, detail="Аты-жөніңізді енгізіңіз")
    if len(payload.password) < 6:
        raise HTTPException(status_code=422, detail="Құпиясөз кемінде 6 таңба болуы керек")

    try:
        user = create_user(
            active_db,
            email=email,
            password=payload.password,
            role="student",
            full_name=full_name,
            grade_label=grade_label,
        )
    except ValueError as exc:
        if str(exc) == "email_exists":
            raise HTTPException(status_code=409, detail="Бұл пошта тіркелген") from exc
        raise HTTPException(status_code=400, detail="Тіркелу мүмкін болмады") from exc

    token = issue_token(user["id"], user["role"])
    return {"token": token, "user": serialize_user(user)}


@app.post(f"{settings.api_prefix}/auth/register")
def register(payload: RegisterPayload) -> dict[str, Any]:
    return create_student_session(payload)


@app.get(f"{settings.api_prefix}/student/dashboard")
def student_dashboard(
    request: Request,
    user: dict[str, Any] = Depends(require_role("student")),
) -> Response:
    cache_key = f"student-dashboard:{user['id']}"
    if cached := cached_payload(request, cache_key):
        return cached
    tasks = db.fetchall(
        """
        SELECT * FROM tasks
        WHERE status = 'active'
        ORDER BY updated_at DESC
        """
    )
    submissions = db.fetchall(
        """
        SELECT s.task_id, s.score, s.created_at, s.is_correct, t.title
        FROM submissions AS s
        INNER JOIN tasks AS t ON t.id = s.task_id
        WHERE s.user_id = ?
        ORDER BY s.created_at DESC;
        """,
        (user["id"],),
    )
    average_score = round(
        sum(item["score"] for item in submissions) / len(submissions),
        1,
    ) if submissions else 0
    completed_task_ids = {item["task_id"] for item in submissions}
    attempts_by_task = {task["id"]: 0 for task in tasks}
    latest_submission_by_task: dict[int, dict[str, Any]] = {}
    for item in submissions:
        attempts_by_task[item["task_id"]] = attempts_by_task.get(item["task_id"], 0) + 1
        latest_submission_by_task.setdefault(item["task_id"], item)
    next_task = next((task for task in tasks if task["id"] not in completed_task_ids), None)
    payload = {
        "user": serialize_user(user),
        "summary": {
            "activeTasks": len(tasks),
            "completedTasks": len(completed_task_ids),
            "pendingTasks": max(len(tasks) - len(completed_task_ids), 0),
            "averageScore": average_score,
        },
        "nextTask": normalize_task(next_task) if next_task is not None else None,
        "recentResults": [
            {
                "taskId": item["task_id"],
                "taskTitle": item["title"],
                "score": item["score"],
                "submittedAt": item["created_at"],
                "isCorrect": bool(item["is_correct"]),
            }
            for item in submissions[:5]
        ],
        "tests": [
            {
                **normalize_task(task),
                "completed": task["id"] in completed_task_ids,
                "lastScore": latest_submission_by_task.get(task["id"], {}).get("score"),
                "attemptCount": attempts_by_task.get(task["id"], 0),
            }
            for task in tasks
        ],
    }
    return cache_response(cache_key, payload)


@app.get(f"{settings.api_prefix}/student/tests/{{task_id}}")
def get_student_test(
    task_id: int,
    request: Request,
    user: dict[str, Any] = Depends(require_role("student")),
) -> Response:
    cache_key = f"student-test:{user['id']}:{task_id}"
    if cached := cached_payload(request, cache_key):
        return cached
    task = db.fetchone("SELECT * FROM tasks WHERE id = ? LIMIT 1;", (task_id,))
    if task is None or task["status"] != "active":
        raise HTTPException(status_code=404, detail="Тапсырма табылмады")
    ordered_tasks = db.fetchall(
        """
        SELECT id
        FROM tasks
        WHERE status = 'active'
        ORDER BY updated_at DESC;
        """
    )
    ordered_ids = [item["id"] for item in ordered_tasks]
    question_number = ordered_ids.index(task_id) + 1 if task_id in ordered_ids else 1
    total_questions = len(ordered_ids) or 1
    last_submission = db.fetchone(
        """
        SELECT submitted_answer, score, is_correct
        FROM submissions
        WHERE task_id = ? AND user_id = ?
        ORDER BY created_at DESC
        LIMIT 1;
        """,
        (task_id, user["id"]),
    )
    payload = {
        "user": serialize_user(user),
        "task": normalize_task(task),
        "meta": {
            "questionNumber": question_number,
            "totalQuestions": total_questions,
            "timeRemaining": f"{max(task['estimated_minutes'] - 1, 1):02d}:00",
            "progressPercent": round((question_number / total_questions) * 100),
            "hintText": "Бір жауапты таңдаңыз." if task["question_type"] == "choice" else "Заңдылықты табыңыз.",
        },
        "lastSubmission": {
            "answer": last_submission["submitted_answer"],
            "score": last_submission["score"],
            "isCorrect": bool(last_submission["is_correct"]),
        } if last_submission else None,
    }
    return cache_response(cache_key, payload)


@app.post(f"{settings.api_prefix}/student/tests/{{task_id}}/submit")
def submit_student_test(
    task_id: int,
    payload: SubmissionPayload,
    user: dict[str, Any] = Depends(require_role("student")),
) -> dict[str, Any]:
    task = db.fetchone("SELECT * FROM tasks WHERE id = ? LIMIT 1;", (task_id,))
    if task is None or task["status"] != "active":
        raise HTTPException(status_code=404, detail="Тапсырма табылмады")
    submitted_answer = payload.answer.strip()
    expected = task["answer"].strip()
    if task["question_type"] == "choice":
        choices = json.loads(task["choices_json"]) if task["choices_json"] else []
        if submitted_answer not in choices:
            raise HTTPException(status_code=422, detail="Берілген нұсқалардың бірін таңдаңыз")
    open_response = task["kind"] == "docx" or len(expected) > 80 or "мұғалім тексереді" in expected.lower()
    is_correct = True if open_response else submitted_answer.lower() == expected.lower()
    score = 100 if is_correct else 0
    db.execute(
        """
        INSERT INTO submissions (task_id, user_id, submitted_answer, is_correct, score, created_at)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (task_id, user["id"], submitted_answer, int(is_correct), score, utc_now()),
    )
    response_cache.clear()
    return {
        "taskId": task_id,
        "submittedAnswer": submitted_answer,
        "expectedAnswer": expected,
        "isCorrect": is_correct,
        "score": score,
        "message": (
            "Жауап қабылданды. Мұғалім шешу жолын тексереді."
            if open_response
            else "Дұрыс!" if is_correct else f"Әзірге қате. Дұрыс жауап: {expected}"
        ),
    }


def build_hint(task: dict[str, Any], level: int, current_answer: str | None) -> str:
    category = task["category"].lower()
    prompt = task["prompt"]
    answer = task["answer"].strip()
    attempt = normalize_space(current_answer or "")
    if level <= 1:
        if task["question_type"] == "choice":
            return "Алдымен шарттағы кілт сөздерді белгіле. Әр нұсқаны сол шартпен жеке салыстыр."
        return "Есепті бірден шығаруға асықпа: берілгендерін, сұралғанын және қандай тәсіл керек екенін бөлек жаз."
    if level == 2:
        if "инвариант" in category or "монвариант" in category:
            return "Қай шама өзгермей қалатынын немесе бір бағытта ғана өзгеретінін ізде. Әр амалдан кейін сол шаманы тексер."
        if "санау" in category or "комбинатор" in category or "рамсей" in category:
            return "Бір объектіні екі түрлі жолмен санап көр. Қатар, баған, жұп немесе байланыс саны бірдей нәтиже беруі мүмкін."
        if "логика" in category:
            return "Шарттарды кестеге түсір. Қайшылық туған нұсқаларды сызып тастап, қалған мүмкіндікті тексер."
        return f"Мына сөйлемге сүйен: «{truncate_text(prompt, 120)}». Шешімнің негізгі амалы осы шарттан басталады."
    if attempt:
        if attempt.lower() == answer.lower():
            return "Жауабың дұрыс көрінеді. Енді шешу жолын толық және ретімен жаз."
        return "Жауабыңды соңғы шартпен қайта тексер. Егер бір шарт орындалмаса, шешімді сол жерден түзет."
    return "Соңғы қадамда тек нәтижені емес, неге дәл солай болатынын дәлелде. Жауапты қысқа жаз, дәлелдеуді бөлек көрсет."


@app.post(f"{settings.api_prefix}/student/tests/{{task_id}}/hint")
def get_student_hint(
    task_id: int,
    payload: HintPayload,
    user: dict[str, Any] = Depends(require_role("student")),
) -> dict[str, Any]:
    del user
    task = db.fetchone("SELECT * FROM tasks WHERE id = ? LIMIT 1;", (task_id,))
    if task is None or task["status"] != "active":
        raise HTTPException(status_code=404, detail="Тапсырма табылмады")
    level = max(1, min(payload.level, 3))
    return {"hint": build_hint(task, level, payload.current_answer), "level": level}


@app.get(f"{settings.api_prefix}/admin/dashboard")
def admin_dashboard(
    request: Request,
    user: dict[str, Any] = Depends(require_role("admin")),
) -> Response:
    cache_key = f"admin-dashboard:{user['id']}"
    if cached := cached_payload(request, cache_key):
        return cached
    student_count = db.fetchone("SELECT COUNT(*) AS total FROM users WHERE role = 'student';")
    task_count = db.fetchone("SELECT COUNT(*) AS total FROM tasks;")
    avg_score = db.fetchone("SELECT AVG(score) AS average_score FROM submissions;")
    recent_results = db.fetchall(
        """
        SELECT s.score, s.created_at, u.full_name, t.title
        FROM submissions AS s
        INNER JOIN users AS u ON u.id = s.user_id
        INNER JOIN tasks AS t ON t.id = s.task_id
        ORDER BY s.created_at DESC
        LIMIT 4;
        """
    )
    payload = {
        "user": serialize_user(user),
        "metrics": {
            "activeStudents": student_count["total"] or 0,
            "totalTests": task_count["total"] or 0,
            "activeTasks": db.fetchone("SELECT COUNT(*) AS total FROM tasks WHERE status = 'active';")["total"] or 0,
            "draftTasks": db.fetchone("SELECT COUNT(*) AS total FROM tasks WHERE status = 'draft';")["total"] or 0,
            "totalSubmissions": db.fetchone("SELECT COUNT(*) AS total FROM submissions;")["total"] or 0,
            "averageScore": round(avg_score["average_score"] or 0, 1),
        },
        "recentResults": [
            {
                "studentName": item["full_name"],
                "taskTitle": item["title"],
                "score": item["score"],
                "timeLabel": item["created_at"],
            }
            for item in recent_results
        ],
        "recentTasks": [
            normalize_task_summary(item)
            for item in db.fetchall(
                """
                SELECT *
                FROM tasks
                ORDER BY updated_at DESC
                LIMIT 6;
                """
            )
        ],
    }
    return cache_response(cache_key, payload)


@app.get(f"{settings.api_prefix}/admin/tasks")
def list_admin_tasks(
    request: Request,
    search: str | None = None,
    user: dict[str, Any] = Depends(require_role("admin")),
) -> Response:
    search_term = f"%{(search or '').strip()}%"
    cache_key = f"admin-tasks:{user['id']}:{search_term}"
    if cached := cached_payload(request, cache_key):
        return cached
    tasks = db.fetchall(
        """
        SELECT * FROM tasks
        WHERE title LIKE ? OR description LIKE ? OR category LIKE ?
        ORDER BY updated_at DESC;
        """,
        (search_term, search_term, search_term),
    )
    payload = {
        "items": [normalize_task(task) for task in tasks],
        "summary": {
            "total": len(tasks),
            "active": sum(1 for task in tasks if task["status"] == "active"),
            "drafts": sum(1 for task in tasks if task["status"] == "draft"),
        },
    }
    return cache_response(cache_key, payload)


@app.post(f"{settings.api_prefix}/admin/tasks")
def create_task(
    title: str = Form(...),
    description: str = Form(...),
    prompt: str = Form(...),
    answer: str = Form(...),
    grade_level: str = Form(...),
    category: str = Form(...),
    difficulty: str = Form(...),
    status_value: str = Form("draft"),
    estimated_minutes: int = Form(15),
    question_type: str = Form("numeric"),
    choices_json: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    document: UploadFile | None = File(default=None),
    user: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    image_url = save_upload(image)
    document_url = save_upload(document)
    task = insert_task_record(
        validate_task_payload(
            {
                "title": title,
                "description": description,
                "prompt": prompt,
                "answer": answer,
                "grade_level": grade_level,
                "category": category,
                "difficulty": difficulty,
                "status_value": status_value,
                "estimated_minutes": estimated_minutes,
                "question_type": question_type,
                "choices_json": choices_json,
            },
            image_url=image_url,
            document_url=document_url,
            document_name=document.filename if document and document.filename else None,
        ),
        user["id"],
    )
    response_cache.clear()
    return {"item": normalize_task(task)} if task else {"item": None}


@app.put(f"{settings.api_prefix}/admin/tasks/{{task_id}}")
def update_task(
    task_id: int,
    title: str = Form(...),
    description: str = Form(...),
    prompt: str = Form(...),
    answer: str = Form(...),
    grade_level: str = Form(...),
    category: str = Form(...),
    difficulty: str = Form(...),
    status_value: str = Form("draft"),
    estimated_minutes: int = Form(15),
    question_type: str = Form("numeric"),
    choices_json: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    document: UploadFile | None = File(default=None),
    user: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    existing = db.fetchone("SELECT * FROM tasks WHERE id = ? LIMIT 1;", (task_id,))
    if existing is None:
        raise HTTPException(status_code=404, detail="Тапсырма табылмады")
    image_url = save_upload(image) if image is not None else None
    document_url = save_upload(document) if document is not None else None
    task = update_task_record(
        task_id,
        validate_task_payload(
            {
                "title": title,
                "description": description,
                "prompt": prompt,
                "answer": answer,
                "grade_level": grade_level,
                "category": category,
                "difficulty": difficulty,
                "status_value": status_value,
                "estimated_minutes": estimated_minutes,
                "question_type": question_type,
                "choices_json": choices_json,
            },
            existing=existing,
            image_url=image_url,
            document_url=document_url,
            document_name=document.filename if document and document.filename else None,
        ),
    )
    response_cache.clear()
    return {"item": normalize_task(task)} if task else {"item": None}


@app.post(f"{settings.api_prefix}/admin/tasks/import-json")
def import_tasks_json(
    file: UploadFile = File(...),
    user: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=422, detail="JSON файлын таңдаңыз")
    try:
        raw_payload = json.loads(file.file.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="JSON файлы дұрыс емес") from exc
    if isinstance(raw_payload, dict) and isinstance(raw_payload.get("tasks"), list):
        records = raw_payload["tasks"]
    elif isinstance(raw_payload, list):
        records = raw_payload
    elif isinstance(raw_payload, dict):
        records = [raw_payload]
    else:
        raise HTTPException(status_code=422, detail="JSON ішінде объект немесе тізім болуы керек")
    created_items = [
        normalize_task(insert_task_record(validate_task_payload(record), user["id"]))
        for record in records
    ]
    response_cache.clear()
    return {"count": len(created_items), "items": created_items}


@app.post(f"{settings.api_prefix}/admin/tasks/import-html")
def import_tasks_html(
    files: list[UploadFile] = File(...),
    user: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=422, detail="HTML файлын таңдаңыз")
    records: list[dict[str, Any]] = []
    for uploaded_file in files:
        if not uploaded_file.filename:
            raise HTTPException(status_code=422, detail="HTML файлын таңдаңыз")
        suffix = Path(uploaded_file.filename).suffix.lower()
        if suffix not in {".html", ".htm"}:
            raise HTTPException(status_code=422, detail="Тек HTML файлдарын импорттауға болады")
        try:
            raw_html = uploaded_file.file.read().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail=f"{uploaded_file.filename} UTF-8 форматында емес") from exc
        records.extend(parse_html_tasks(raw_html, uploaded_file.filename))
    created_items = [
        normalize_task(insert_task_record(validate_task_payload(record), user["id"]))
        for record in records
    ]
    response_cache.clear()
    return {"count": len(created_items), "items": created_items}


@app.post(f"{settings.api_prefix}/admin/tasks/import-docx")
def import_tasks_docx(
    files: list[UploadFile] = File(...),
    user: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=422, detail="DOCX файлын таңдаңыз")
    records: list[dict[str, Any]] = []
    for uploaded_file in files:
        if not uploaded_file.filename:
            raise HTTPException(status_code=422, detail="DOCX файлын таңдаңыз")
        suffix = Path(uploaded_file.filename).suffix.lower()
        if suffix != ".docx":
            raise HTTPException(status_code=422, detail="Тек DOCX файлдарын импорттауға болады")
        content = uploaded_file.file.read()
        document_url = save_upload_bytes(content, uploaded_file.filename, uploaded_file.content_type)
        records.extend(parse_docx_tasks(content, uploaded_file.filename, document_url))
    created_items = [
        normalize_task(insert_task_record(validate_task_payload(record), user["id"]))
        for record in records
    ]
    response_cache.clear()
    return {"count": len(created_items), "items": created_items}


@app.delete(f"{settings.api_prefix}/admin/tasks/{{task_id}}")
def delete_task(
    task_id: int,
    user: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, bool]:
    del user
    db.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
    response_cache.clear()
    return {"ok": True}


@app.get("/uploads/{filename}")
def serve_uploaded_file(filename: str) -> FileResponse:
    path = settings.uploads_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Файл табылмады")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=31536000, immutable"})
