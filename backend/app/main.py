from __future__ import annotations

import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .auth import decode_token, issue_token, verify_password
from .cache import ResponseCache
from .config import get_settings
from .database import Database, get_database, utc_now

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


class SubmissionPayload(BaseModel):
    answer: str


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
        "estimatedMinutes": row["estimated_minutes"],
        "badge": row["badge"],
        "badgeTone": row["badge_tone"] or "primary",
        "questionType": row["question_type"],
        "choices": json.loads(row["choices_json"]) if row["choices_json"] else [],
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
                raise HTTPException(status_code=422, detail="choices_json is invalid") from exc
            if not isinstance(data, list):
                raise HTTPException(status_code=422, detail="choices_json must be an array")
            return [str(item).strip() for item in data if str(item).strip()]
        return [item.strip() for item in stripped.split(",") if item.strip()]
    raise HTTPException(status_code=422, detail="choices must be a list or string")


def validate_task_payload(
    payload: dict[str, Any],
    *,
    existing: dict[str, Any] | None = None,
    image_url: str | None = None,
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
        choose_value(payload, ("grade_level", "gradeLevel"), existing["grade_level"] if existing else "Grade 1"),
        "grade_level",
    )
    category = ensure_text(
        choose_value(payload, ("category",), existing["category"] if existing else "Logic"),
        "category",
    )
    difficulty = ensure_text(
        choose_value(payload, ("difficulty",), existing["difficulty"] if existing else "Beginner"),
        "difficulty",
    )
    status_value = ensure_text(
        choose_value(payload, ("status_value", "status"), existing["status"] if existing else "draft"),
        "status",
    ).lower()
    if status_value not in {"active", "draft"}:
        raise HTTPException(status_code=422, detail="status must be active or draft")
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
        raise HTTPException(status_code=422, detail="question_type must be numeric or choice")
    parsed_choices = parse_choices(
        choose_value(
            payload,
            ("choices_json", "choices", "choicesJson"),
            existing["choices_json"] if existing else None,
        )
    )
    if question_type == "choice" and not parsed_choices:
        raise HTTPException(status_code=422, detail="choice tasks require at least one option")
    final_image_url = image_url if image_url is not None else choose_value(
        payload,
        ("image_url", "imageUrl"),
        existing["image_url"] if existing else None,
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
        "estimated_minutes": estimated_minutes,
        "badge": choose_value(payload, ("badge",), existing["badge"] if existing else "New"),
        "badge_tone": choose_value(payload, ("badge_tone", "badgeTone"), existing["badge_tone"] if existing else "primary"),
        "kind": choose_value(payload, ("kind",), existing["kind"] if existing else "practice"),
        "question_type": question_type,
        "choices_json": json.dumps(parsed_choices) if question_type == "choice" else None,
    }


def insert_task_record(task_data: dict[str, Any], user_id: int) -> dict[str, Any]:
    now = utc_now()
    cursor = db.execute(
        """
        INSERT INTO tasks (
            title, description, prompt, answer, grade_level, category, difficulty,
            status, image_url, estimated_minutes, badge, badge_tone, kind,
            question_type, choices_json, created_by, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
            task_data["estimated_minutes"],
            task_data["badge"],
            task_data["badge_tone"],
            task_data["kind"],
            task_data["question_type"],
            task_data["choices_json"],
            user_id,
            now,
            now,
        ),
    )
    task = db.fetchone("SELECT * FROM tasks WHERE id = ? LIMIT 1;", (cursor.lastrowid,))
    if task is None:
        raise HTTPException(status_code=500, detail="Task was not created")
    return task


def update_task_record(task_id: int, task_data: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    db.execute(
        """
        UPDATE tasks
        SET title = ?, description = ?, prompt = ?, answer = ?, grade_level = ?,
            category = ?, difficulty = ?, status = ?, image_url = ?, estimated_minutes = ?,
            badge = ?, badge_tone = ?, kind = ?, question_type = ?, choices_json = ?,
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
            task_data["estimated_minutes"],
            task_data["badge"],
            task_data["badge_tone"],
            task_data["kind"],
            task_data["question_type"],
            task_data["choices_json"],
            now,
            task_id,
        ),
    )
    task = db.fetchone("SELECT * FROM tasks WHERE id = ? LIMIT 1;", (task_id,))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def save_upload(file: UploadFile | None) -> str | None:
    if file is None or not file.filename:
        return None
    content = file.file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail="Uploaded file is too large")
    suffix = Path(file.filename).suffix.lower() or mimetypes.guess_extension(file.content_type or "") or ".bin"
    filename = f"{uuid4().hex}{suffix}"
    destination = settings.uploads_dir / filename
    destination.write_bytes(content)
    return f"/uploads/{filename}"


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
        raise HTTPException(status_code=404, detail="Task not found")
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
            "hintText": "Select one answer." if task["question_type"] == "choice" else "Find the number pattern.",
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
        raise HTTPException(status_code=404, detail="Task not found")
    submitted_answer = payload.answer.strip()
    expected = task["answer"].strip()
    if task["question_type"] == "choice":
        choices = json.loads(task["choices_json"]) if task["choices_json"] else []
        if submitted_answer not in choices:
            raise HTTPException(status_code=422, detail="Choose one of the listed options")
    is_correct = submitted_answer.lower() == expected.lower()
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
        "message": "Correct" if is_correct else f"Incorrect. Correct answer: {expected}",
    }


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
    user: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    image_url = save_upload(image)
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
    user: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    existing = db.fetchone("SELECT * FROM tasks WHERE id = ? LIMIT 1;", (task_id,))
    if existing is None:
        raise HTTPException(status_code=404, detail="Task not found")
    image_url = save_upload(image) if image is not None else None
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
        raise HTTPException(status_code=422, detail="JSON file is required")
    try:
        raw_payload = json.loads(file.file.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="Invalid JSON file") from exc
    if isinstance(raw_payload, dict) and isinstance(raw_payload.get("tasks"), list):
        records = raw_payload["tasks"]
    elif isinstance(raw_payload, list):
        records = raw_payload
    elif isinstance(raw_payload, dict):
        records = [raw_payload]
    else:
        raise HTTPException(status_code=422, detail="JSON must contain an object or array")
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
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=31536000, immutable"})
