"""
scripts/set_principal_admin.py

One-time migration for accounts that were already promoted to admin via
the old POST /auth/admin/bootstrap (back when it only set is_admin=True,
before the principal-admin/permissions system existed). That flow never
set is_principal_admin, so nobody in the system can currently use the
"manage admins" endpoints — this script fixes that once, directly against
the DB, for a single named account.

Run against the SAME DATABASE_URL as your deployed backend:

    export DATABASE_URL="mysql+pymysql://user:password@host:4000/globetrotter"
    python -m scripts.set_principal_admin <username>

Refuses to run if a principal admin already exists (use --force to
transfer principal status instead — this demotes the previous principal
to a regular admin with no permissions, so use it deliberately).
"""
import argparse
import os
import sys
from datetime import datetime, timezone

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE_DIR)

from app import storage  # noqa: E402
from app.dependencies import ADMIN_PERMISSIONS  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username", help="Existing account to designate as principal admin")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Transfer principal status even if one is already set (demotes the previous principal)",
    )
    args = parser.parse_args()

    users = storage.read_all(storage.USERS_FILE)
    target = next((u for u in users if u["username"] == args.username), None)
    if not target:
        print(f"No such user: {args.username!r}")
        sys.exit(1)

    existing_principal = next((u for u in users if u.get("is_principal_admin")), None)
    if existing_principal and existing_principal["username"] != args.username:
        if not args.force:
            print(
                f"'{existing_principal['username']}' is already the principal admin. "
                "Re-run with --force to transfer principal status to "
                f"'{args.username}' instead (this demotes '{existing_principal['username']}' "
                "to a regular admin with no permissions)."
            )
            sys.exit(1)
        storage.update_one(
            storage.USERS_FILE,
            "username",
            existing_principal["username"],
            {"is_principal_admin": False, "admin_permissions": []},
        )
        print(f"Demoted previous principal admin: {existing_principal['username']}")

    storage.update_one(
        storage.USERS_FILE,
        "username",
        args.username,
        {
            "is_admin": True,
            "is_principal_admin": True,
            "admin_permissions": sorted(ADMIN_PERMISSIONS),
            "admin_promoted_at": datetime.now(timezone.utc).isoformat(),
            "admin_promoted_by": "migration:set_principal_admin",
        },
    )
    print(f"'{args.username}' is now the principal admin.")


if __name__ == "__main__":
    main()
