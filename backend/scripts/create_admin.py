#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import create_user, get_database  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an admin user.")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--full-name", required=True, help="Admin display name")
    parser.add_argument("--password", help="Admin password. If omitted, you will be prompted.")
    return parser.parse_args()


def read_password(raw_password: str | None) -> str:
    if raw_password:
        return raw_password
    env_password = os.getenv("ADMIN_PASSWORD")
    if env_password:
        return env_password
    password = getpass.getpass("Admin password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    return password


def main() -> int:
    args = parse_args()
    password = read_password(args.password)
    if len(password) < 6:
        raise SystemExit("Password must be at least 6 characters.")

    try:
        user = create_user(
            get_database(),
            email=args.email,
            password=password,
            role="admin",
            full_name=args.full_name.strip(),
            grade_label="Әкімші",
        )
    except ValueError as exc:
        if str(exc) == "email_exists":
            raise SystemExit("A user with this email already exists.") from exc
        raise

    print(f"Admin created: {user['email']} (id={user['id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
