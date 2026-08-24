"""
app/username_rename.py

Renaming a username is the one profile edit that isn't a simple
single-record update: the username is the de-facto primary key used
across most of the app's storage collections (JSON-backed "tables"
with no foreign keys, no transactions, no cascade support of any
kind — see app/storage.py). If we only updated the users record, every
other collection would silently point at an account that no longer
exists under that name: itineraries would vanish from "my trips",
activity history would zero out (breaking earnings), payouts/feedback/
comments would look like someone else's.

What gets renamed (functional references — things the app actually
reads back to compute something or show "your X"):
  users.username itself, itineraries.username, places.submitted_by,
  feedback.username, activity.username, referrals.sponsor_username,
  payouts.username, notifications.username, destination_votes.username,
  destination_comments.username.

What deliberately does NOT get rewritten (historical records — an
audit trail should say what actually happened under the name that was
actually used at the time, not be silently rewritten after the fact):
  audit_log.actor / audit_log.target, notifications.sent_by,
  notification_batches.sent_by, admin_promoted_by. These are exactly
  the kind of record where mutating history is worse than a stale name.

No real transactions are available with this storage layer, so the
new username's availability is checked (and the whole users table
locked implicitly via storage's own lock) immediately before starting,
to make the window for a race as small as practical — see
app/storage.py's module-level lock, which every read_all/replace_all
call already goes through.
"""
from app import storage


class UsernameTakenError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


def _rename_in(collection: str, field: str, old_username: str, new_username: str) -> None:
    records = storage.read_all(collection)
    changed = False
    for r in records:
        if r.get(field) == old_username:
            r[field] = new_username
            changed = True
    if changed:
        storage.replace_all(collection, records)


def rename_username(old_username: str, new_username: str) -> dict:
    """Returns the updated user record. Raises UsernameTakenError or
    UserNotFoundError without changing anything on failure."""
    users = storage.read_all(storage.USERS_FILE)

    if any(u["username"].lower() == new_username.lower() for u in users if u["username"] != old_username):
        raise UsernameTakenError(f"'{new_username}' is already taken")

    target = next((u for u in users if u["username"] == old_username), None)
    if target is None:
        raise UserNotFoundError(f"No such user: {old_username}")

    target["username"] = new_username
    storage.replace_all(storage.USERS_FILE, users)

    _rename_in(storage.ITINERARIES_FILE, "username", old_username, new_username)
    _rename_in(storage.PLACES_FILE, "submitted_by", old_username, new_username)
    _rename_in(storage.FEEDBACK_FILE, "username", old_username, new_username)
    _rename_in(storage.ACTIVITY_FILE, "username", old_username, new_username)
    _rename_in(storage.REFERRALS_FILE, "sponsor_username", old_username, new_username)
    _rename_in(storage.PAYOUTS_FILE, "username", old_username, new_username)
    _rename_in(storage.NOTIFICATIONS_FILE, "username", old_username, new_username)
    _rename_in(storage.DESTINATION_VOTES_FILE, "username", old_username, new_username)
    _rename_in(storage.DESTINATION_COMMENTS_FILE, "username", old_username, new_username)

    # Destinations that came from this user's own approved place
    # submissions also carry submitted_by — keep those in sync too.
    _rename_in(storage.DESTINATIONS_FILE, "submitted_by", old_username, new_username)

    return target
