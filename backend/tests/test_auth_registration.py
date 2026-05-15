from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from app.auth import verify_password
from app.database import Database, build_initials, create_user, initialize_database
from app.main import RegisterPayload, create_student_session


class AuthRegistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "test.sqlite3")
        initialize_database(self.db)

    def tearDown(self) -> None:
        self.db._connection.close()
        self.temp_dir.cleanup()

    def test_create_user_hashes_password_and_generates_initials(self) -> None:
        user = create_user(
            self.db,
            email=" NEW.ADMIN@Example.COM ",
            password="secure123",
            role="admin",
            full_name="Жаңа Әкімші",
            grade_label="Әкімші",
        )

        stored = self.db.fetchone("SELECT * FROM users WHERE id = ?;", (user["id"],))
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored["email"], "new.admin@example.com")
        self.assertEqual(stored["initials"], "ЖӘ")
        self.assertTrue(verify_password("secure123", stored["password_hash"]))

    def test_register_student_returns_session(self) -> None:
        session = create_student_session(
            RegisterPayload(
                email="student.new@example.com",
                password="student123",
                full_name="Жаңа Оқушы",
                grade_label="8-сынып",
            ),
            self.db,
        )

        self.assertIn("token", session)
        self.assertEqual(session["user"]["role"], "student")
        self.assertEqual(session["user"]["email"], "student.new@example.com")
        self.assertEqual(session["user"]["gradeLabel"], "8-сынып")

    def test_register_student_rejects_duplicate_email(self) -> None:
        payload = RegisterPayload(
            email="duplicate@example.com",
            password="student123",
            full_name="Бірінші Оқушы",
            grade_label="7-сынып",
        )
        create_student_session(payload, self.db)

        with self.assertRaises(HTTPException) as context:
            create_student_session(
                RegisterPayload(
                    email="DUPLICATE@example.com",
                    password="student123",
                    full_name="Екінші Оқушы",
                    grade_label="7-сынып",
                ),
                self.db,
            )

        self.assertEqual(context.exception.status_code, 409)

    def test_register_student_validates_password_length(self) -> None:
        with self.assertRaises(HTTPException) as context:
            create_student_session(
                RegisterPayload(
                    email="short@example.com",
                    password="123",
                    full_name="Қысқа Құпия",
                    grade_label="7-сынып",
                ),
                self.db,
            )

        self.assertEqual(context.exception.status_code, 422)

    def test_initials_fallback(self) -> None:
        self.assertEqual(build_initials(""), "О")


if __name__ == "__main__":
    unittest.main()
