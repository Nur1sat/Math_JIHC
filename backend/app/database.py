from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any

from .auth import hash_password
from .config import get_settings


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = RLock()
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON;")
        self._connection.execute("PRAGMA journal_mode = WAL;")
        self._connection.execute("PRAGMA synchronous = NORMAL;")

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        with self._lock:
            cursor = self._connection.execute(query, params)
            self._connection.commit()
            return cursor

    def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(query, params).fetchone()
            return dict(row) if row is not None else None

    def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(query, params).fetchall()
            return [dict(row) for row in rows]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def initialize_database(db: Database) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            full_name TEXT NOT NULL,
            grade_label TEXT,
            initials TEXT NOT NULL,
            avatar_url TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            prompt TEXT NOT NULL,
            answer TEXT NOT NULL,
            grade_level TEXT NOT NULL,
            category TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            status TEXT NOT NULL,
            image_url TEXT,
            estimated_minutes INTEGER NOT NULL DEFAULT 15,
            badge TEXT,
            badge_tone TEXT,
            kind TEXT NOT NULL DEFAULT 'practice',
            question_type TEXT NOT NULL DEFAULT 'numeric',
            choices_json TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
        );
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            submitted_answer TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            score INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )
    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        """
    )
    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tasks_status_grade ON tasks(status, grade_level);
        """
    )
    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_submissions_task_user ON submissions(task_id, user_id);
        """
    )
    seed_data(db)


def seed_data(db: Database) -> None:
    existing_user = db.fetchone("SELECT id FROM users LIMIT 1;")
    if existing_user is not None:
        return
    created_at = utc_now()
    users = [
        (
            "student@oasis.edu",
            hash_password("student123"),
            "student",
            "Alex Johnson",
            "Grade 1 Student",
            "AJ",
            "https://lh3.googleusercontent.com/aida-public/AB6AXuBZm0J70UMexkn1mPztZFL5tMZwysV2ebpIFbUJdPC0rJvJC2XlmjQVnPUZ00IqwkoXsPQBFMACLYf8Z7CLgXwZhpGVqUsNjBiIUvud7h-7J0JK9oxVx58YXS6Ed9-4L8x9lOtV3aw2IbDbhbvs3ePFsi6zlJw-tlhA-Tp0pguDkyLF0pD2BLHTEATbHRmWgOtODqURsIHfsF4l4vZZAiQYdGK3SC4trbQh5EZw3_Yx_E_WYkfdY5nG3KBajb52LB162B3U8nwjrM65",
            created_at,
        ),
        (
            "admin@mathacademy.edu",
            hash_password("admin123"),
            "admin",
            "Dr. Sarah Chen",
            "Administrator",
            "SC",
            "https://lh3.googleusercontent.com/aida-public/AB6AXuCh_dbyTMpXmJS8SdHrj8vz0jeXzqGLv9JzwWeI2reYn55y-_9XZEr8NgkbvR54Slk4k0UQshs8kIKDNmDNt2bFuRQg-QcGP595AcErsnVNN4jD7QqL5Ypoi3El-CWlw3apz3Q5f0X-IDIxwKobLWeSDADA8Zh_zN1EJ6PUHslsqOjTrrKIU0LiVImiRVtXxckcfDxGkNRZehEK2qrMt-bR7JFsjTRqi-SW_v0I6Y0hBTYS8GGb6H-Xi09NNTlQQZ78eejzw4GP33W4",
            created_at,
        ),
    ]
    for user in users:
        db.execute(
            """
            INSERT INTO users (
                email, password_hash, role, full_name, grade_label, initials, avatar_url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            user,
        )
    admin = db.fetchone("SELECT id FROM users WHERE role = 'admin' LIMIT 1;")
    seed_tasks = [
        {
            "title": "Counting Apples (4-6)",
            "description": "Practice counting groups of objects up to 6 using illustrated prompts.",
            "prompt": "How many apples are there in the basket?",
            "answer": "5",
            "grade_level": "Grade 1",
            "category": "Counting",
            "difficulty": "Beginner",
            "status": "active",
            "image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuB9NiKolxaHjD0WLyh9eXWCljw7bHRAhrcESxqNsL5D_nm3IDyFzLB_vubHzONDL4jlV9DXcs2v0GCG9HZDIdviTlOfSphOACreQdj5Zv5oJMkwsjwq_CZ05RlwAspcXLOGk7McP38hSK9o3iY_syJ6IpjJa1DiKXKSMsb2lA9vO62GRfQ3ISKJHvVvrFMIxNI74YDilR7uw0nYbFWgeXgO0zVr7yN8ONgm7fpI9ndQXhVCxWELuRCppxH77A_HVDL69GJdP87SQ9iM",
            "estimated_minutes": 8,
            "badge": "8 Tasks",
            "badge_tone": "primary",
            "kind": "practice",
            "question_type": "choice",
            "choices_json": json.dumps(["1", "2", "3", "4", "5", "6", "7", "8", "9"]),
        },
        {
            "title": "Big Numbers (7-9)",
            "description": "Master the biggest single-digit numbers with visual recognition and sequence drills.",
            "prompt": "Which number comes after 8?",
            "answer": "9",
            "grade_level": "Grade 1",
            "category": "Number Sense",
            "difficulty": "Intermediate",
            "status": "active",
            "image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuDdfBSsxdokt7Vcr5-M7bg8HuAfBpHqL8nIv6igfh3UvKY2d5IMBOeTu7emWKciIITL7AQZS5fQuHsRRQ8l5mTjK-7WSSEqWaNGI7yt3LpmQ1aBscvhXl8aOvLDaN_LPYPrMr70yuKjUaFGuBnEHPycWISk1LE9pU_u9Ed1mHv9Vt0TK2pnhQ8GOH2avxHsw94-Fc1deIBOkAcJmfF8pL401TJuMqWvvKAnQOK8tLCt7FOVqVkavSBZzAwNL6tHn-2Sh_cBKYkOUHwE",
            "estimated_minutes": 10,
            "badge": "5 Tasks left",
            "badge_tone": "tertiary",
            "kind": "practice",
            "question_type": "choice",
            "choices_json": json.dumps(["6", "7", "8", "9"]),
        },
        {
            "title": "Logical Patterns",
            "description": "Find the next number in a geometric progression.",
            "prompt": "Look at the pattern 2, 4, 8, 16. What number comes next?",
            "answer": "32",
            "grade_level": "Grade 3",
            "category": "Logic",
            "difficulty": "Intermediate",
            "status": "active",
            "image_url": None,
            "estimated_minutes": 15,
            "badge": "Logic Quest",
            "badge_tone": "secondary",
            "kind": "practice",
            "question_type": "numeric",
            "choices_json": None,
        },
    ]
    for task in seed_tasks:
        db.execute(
            """
            INSERT INTO tasks (
                title, description, prompt, answer, grade_level, category, difficulty,
                status, image_url, estimated_minutes, badge, badge_tone, kind,
                question_type, choices_json, created_by, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
                task["image_url"],
                task["estimated_minutes"],
                task["badge"],
                task["badge_tone"],
                task["kind"],
                task["question_type"],
                task["choices_json"],
                admin["id"] if admin else None,
                created_at,
                created_at,
            ),
        )
    student = db.fetchone("SELECT id FROM users WHERE role = 'student' LIMIT 1;")
    task = db.fetchone("SELECT id FROM tasks WHERE title = 'Logical Patterns' LIMIT 1;")
    if student and task:
        db.execute(
            """
            INSERT INTO submissions (task_id, user_id, submitted_answer, is_correct, score, created_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (task["id"], student["id"], "32", 1, 100, created_at),
        )


def get_database() -> Database:
    settings = get_settings()
    db = Database(settings.database_path)
    initialize_database(db)
    return db
