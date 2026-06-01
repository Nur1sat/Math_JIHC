#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import get_database, utc_now  # noqa: E402


DEFAULT_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "full_tasks_seed.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import the full bundled task seed.")
    parser.add_argument(
        "--fixture",
        default=str(DEFAULT_FIXTURE),
        help="Path to the JSON fixture. Defaults to backend/fixtures/full_tasks_seed.json.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing tasks and submissions before importing.",
    )
    return parser.parse_args()


def load_tasks(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("tasks"), list):
        return payload["tasks"]
    if isinstance(payload, list):
        return payload
    raise SystemExit("Fixture must be a JSON list or an object with a tasks list.")


def main() -> int:
    args = parse_args()
    fixture_path = Path(args.fixture).expanduser().resolve()
    tasks = load_tasks(fixture_path)
    db = get_database()
    admin = db.fetchone("SELECT id FROM users WHERE role = 'admin' LIMIT 1;")
    admin_id = admin["id"] if admin else None

    if args.replace:
        db.execute("DELETE FROM submissions;")
        db.execute("DELETE FROM tasks;")

    now = utc_now()
    inserted = 0
    skipped = 0
    for task in tasks:
        existing = db.fetchone(
            """
            SELECT id FROM tasks
            WHERE title = ? AND COALESCE(document_name, '') = COALESCE(?, '')
            LIMIT 1;
            """,
            (task["title"], task.get("document_name")),
        )
        if existing is not None:
            skipped += 1
            continue

        choices = task.get("choices") or []
        db.execute(
            """
            INSERT INTO tasks (
                title, description, prompt, answer, grade_level, category, difficulty,
                status, image_url, document_url, document_name, estimated_minutes,
                badge, badge_tone, kind, question_type, choices_json, content_html,
                created_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                task["title"],
                task["description"],
                task["prompt"],
                task["answer"],
                task["grade_level"],
                task["category"],
                task["difficulty"],
                task["status"],
                task.get("image_url"),
                task.get("document_url"),
                task.get("document_name"),
                int(task.get("estimated_minutes") or 15),
                task.get("badge"),
                task.get("badge_tone"),
                task.get("kind") or "practice",
                task.get("question_type") or "numeric",
                json.dumps(choices, ensure_ascii=False) if choices else None,
                task.get("content_html"),
                admin_id,
                now,
                now,
            ),
        )
        inserted += 1

    total = db.fetchone("SELECT COUNT(*) AS total FROM tasks;")["total"]
    print(f"Inserted {inserted} tasks, skipped {skipped}, total tasks: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
