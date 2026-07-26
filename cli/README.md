# GT CLI

A command-line client for GT, talking to the same REST API as the web
frontend. Useful for quick actions without opening a browser, or for
scripting (e.g. bulk itinerary creation, CI smoke tests).

## Install

```bash
cd cli
python -m venv .venv && source .venv/bin/activate
pip install -e .
gt --help
```

This registers a real `gt` command on your PATH (via the `[project.scripts]`
entry point in `pyproject.toml`), backed by the `gt_cli` package.

By default it talks to `http://localhost:8000`. Point it elsewhere with:

```bash
export GT_API_URL=https://api.your-deployed-domain.com
```

## Usage

```bash
gt auth register --username alice --email alice@example.com --password ...
gt auth login --username alice --password ...
gt auth whoami
gt auth mfa-setup            # prints a secret + provisioning URI
gt auth mfa-confirm 123456   # enable MFA with a code from your authenticator app
gt auth logout

gt destinations search --tag beach
gt recommendations

gt itineraries create --title "Coastal weekend" --destinations limbe-botanic-beach --start-date 2026-09-01 --end-date 2026-09-03
gt itineraries list
gt itineraries delete <id>

gt places submit --name "..." --region "..." --description "..." --image-url "..." --latitude ... --longitude ...
gt places mine

gt feedback submit --category suggestion --message "..." --rating 5

gt config   # shows API URL + whether you're logged in
```

Any option can also be answered interactively — omit `--password`, for
example, and the CLI will prompt for it with hidden input instead of it
ever appearing in your shell history.

## Where your session lives

Since each `gt` command is a separate process (unlike a browser tab that
stays open), the CLI stores your session on disk under `~/.gt/`:

- `~/.gt/config.json` — API URL, username, access token, and its expiry.
- `~/.gt/cookies.txt` — the refresh-token cookie, in the same format
  `requests` reads/writes natively.

Both files are created with `0600` permissions (readable/writable only by
you) the moment they're written — same intent as marking a browser cookie
httpOnly, just enforced at the filesystem level since there's no browser
here to do it for us.

The access token refreshes automatically and silently right before it
would expire (checked against the stored expiry, with a 30-second buffer),
so you generally never need to log in again until the refresh token itself
expires (7 days by default) — exactly like staying logged into a website.

`gt auth logout` clears both files. If you ever want to nuke your local
session by hand: `rm -rf ~/.gt`.

## Change where the CLI stores its session (e.g. for testing)

```bash
export GT_CONFIG_DIR=/some/other/path
```
