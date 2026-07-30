"""
gt_cli/main.py

The `gt` command-line client — talks to a running GT API over plain REST,
same as the web frontend would. Install with:

    pip install -e cli/

then run `gt --help`.
"""
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from gt_cli import config
from gt_cli.client import GTApiError, GTClient

app = typer.Typer(help="GT — discover and plan trips across Cameroon, from your terminal.")
auth_app = typer.Typer(help="Register, login, logout, MFA.")
destinations_app = typer.Typer(help="Search the Cameroon destination catalogue.")
itineraries_app = typer.Typer(help="Plan and manage your trips.")
places_app = typer.Typer(help="Advertise a place / view your submissions.")
feedback_app = typer.Typer(help="Send feedback to the GT team.")
earnings_app = typer.Typer(help="Track usage, view earnings, request a payout.")
notifications_app = typer.Typer(help="View, mark read, or delete your notifications.")

app.add_typer(auth_app, name="auth")
app.add_typer(destinations_app, name="destinations")
app.add_typer(itineraries_app, name="itineraries")
app.add_typer(places_app, name="places")
app.add_typer(feedback_app, name="feedback")
app.add_typer(earnings_app, name="earnings")
app.add_typer(notifications_app, name="notifications")

console = Console()


def _handle_error(exc: GTApiError) -> None:
    console.print(f"[bold red]Error {exc.status_code}:[/bold red] {exc.detail}")
    if exc.status_code == 401:
        console.print("[dim]Try `gt auth login` again.[/dim]")
    raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------

@auth_app.command("register")
def auth_register(
    username: str = typer.Option(..., prompt=True),
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
    preferences: str = typer.Option("", help="Comma-separated tags, e.g. beach,hiking"),
    referral_code: Optional[str] = typer.Option(None, help="Referral code of the user who invited you, if any"),
):
    """Create a new GT account. You'll need to verify it (check your email)
    within 30 minutes before you can log in, or the account is deleted."""
    client = GTClient()
    prefs = [p.strip() for p in preferences.split(",") if p.strip()]
    try:
        client.register(username, email, password, prefs, referral_code=referral_code)
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print(
        f"[bold green]Account created for {username}.[/bold green] "
        "Check your email for a verification token, then run `gt auth verify <token>` "
        "within 30 minutes — unverified accounts are automatically deleted."
    )


@auth_app.command("verify")
def auth_verify(token: str = typer.Argument(..., help="Verification token from your email")):
    """Verify a newly registered account."""
    client = GTClient()
    try:
        client.verify(token)
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print("[bold green]Account verified.[/bold green] You can now `gt auth login`.")


@auth_app.command("register-phone")
def auth_register_phone(
    username: str = typer.Option(..., prompt=True),
    phone: str = typer.Option(..., prompt=True, help="e.g. +237650000000"),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
    preferences: str = typer.Option("", help="Comma-separated tags, e.g. beach,hiking"),
    referral_code: Optional[str] = typer.Option(None, help="Referral code of the user who invited you, if any"),
):
    """Create a new GT account with a phone number instead of email."""
    client = GTClient()
    prefs = [p.strip() for p in preferences.split(",") if p.strip()]
    try:
        client.register_phone(username, phone, password, prefs, referral_code=referral_code)
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print(
        f"[bold green]Account created for {username}.[/bold green] "
        "Check your SMS for a verification code, then run `gt auth verify <code>` "
        "within 30 minutes — unverified accounts are automatically deleted."
    )


@auth_app.command("password-reset-request")
def auth_password_reset_request(username: str = typer.Option(..., prompt=True)):
    """Request a password reset code (sent via SMS or email, whichever the account has)."""
    client = GTClient()
    try:
        result = client.request_password_reset(username)
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print(result["detail"])


@auth_app.command("password-reset-confirm")
def auth_password_reset_confirm(
    token: str = typer.Argument(..., help="Reset code you received"),
    new_password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
):
    """Confirm a password reset with the code you received."""
    client = GTClient()
    try:
        result = client.confirm_password_reset(token, new_password)
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print(f"[bold green]{result['detail']}[/bold green]")


@auth_app.command("login")
def auth_login(
    username: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True),
):
    """Log in. If MFA is enabled on the account, you'll be prompted for a code."""
    client = GTClient()
    try:
        result = client.login(username, password)
        if result.get("mfa_required"):
            code = typer.prompt("Enter your 6-digit MFA code")
            result = client.login(username, password, mfa_code=code)
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print(f"[bold green]Logged in as {username}.[/bold green]")


@auth_app.command("logout")
def auth_logout():
    """Log out and clear locally stored tokens."""
    client = GTClient()
    client.logout()
    console.print("Logged out.")


@auth_app.command("whoami")
def auth_whoami():
    """Show the currently logged-in user's profile."""
    client = GTClient()
    try:
        me = client.whoami()
    except GTApiError as exc:
        _handle_error(exc)
        return
    table = Table(show_header=False)
    for key, value in me.items():
        table.add_row(key, str(value))
    console.print(table)


@auth_app.command("mfa-setup")
def auth_mfa_setup():
    """Start MFA enrollment: prints a QR provisioning URI + raw secret."""
    client = GTClient()
    try:
        result = client.mfa_setup()
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print(f"Secret: [bold]{result['secret']}[/bold]")
    console.print(f"Provisioning URI (scan or paste into a QR generator):\n{result['provisioning_uri']}")
    console.print("Then run: [bold]gt auth mfa-confirm <code-from-your-authenticator-app>[/bold]")


@auth_app.command("mfa-confirm")
def auth_mfa_confirm(code: str = typer.Argument(..., help="6-digit code from your authenticator app")):
    """Confirm MFA enrollment with a code, enabling it on your account."""
    client = GTClient()
    try:
        client.mfa_confirm(code)
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print("[bold green]MFA enabled.[/bold green] You'll need a code on every future login.")


# ---------------------------------------------------------------------------
# destinations
# ---------------------------------------------------------------------------

@destinations_app.command("search")
def destinations_search(
    q: Optional[str] = typer.Option(None, help="Free-text search"),
    tag: Optional[str] = typer.Option(None, help="e.g. beach, hiking, culture"),
    region: Optional[str] = typer.Option(None),
    max_cost: Optional[int] = typer.Option(None, help="Max average cost in FCFA"),
):
    """Search the Cameroon destination catalogue."""
    client = GTClient()
    try:
        results = client.search_destinations(q=q, tag=tag, region=region, max_cost=max_cost)
    except GTApiError as exc:
        _handle_error(exc)
        return
    if not results:
        console.print("No destinations matched.")
        raise typer.Exit()
    table = Table(title="Destinations")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Region")
    table.add_column("Tags")
    table.add_column("Cost (FCFA)")
    for d in results:
        table.add_row(d["id"], d["name"], d["region"], ", ".join(d["tags"]), str(d.get("avg_cost_fcfa", "-")))
    console.print(table)
    for d in results:
        console.print(f"\n[bold]{d['name']}[/bold]\n{d['description']}\nImage: {d['image_url']}")


# ---------------------------------------------------------------------------
# recommendations (top-level command, no subgroup needed for a single action)
# ---------------------------------------------------------------------------

@app.command("recommendations")
def recommendations(limit: int = typer.Option(10, help="How many results to return")):
    """Get personalised destination recommendations based on your preferences."""
    client = GTClient()
    try:
        results = client.recommendations(limit=limit)
    except GTApiError as exc:
        _handle_error(exc)
        return
    if not results:
        console.print("No recommendations yet — try updating your preferences.")
        raise typer.Exit()
    table = Table(title="Recommended for you")
    table.add_column("Name")
    table.add_column("Region")
    table.add_column("Tags")
    for d in results:
        table.add_row(d["name"], d["region"], ", ".join(d["tags"]))
    console.print(table)


# ---------------------------------------------------------------------------
# itineraries
# ---------------------------------------------------------------------------

@itineraries_app.command("create")
def itineraries_create(
    title: str = typer.Option(..., prompt=True),
    destinations: str = typer.Option(..., prompt=True, help="Comma-separated destination IDs"),
    start_date: str = typer.Option(..., prompt=True, help="YYYY-MM-DD"),
    end_date: str = typer.Option(..., prompt=True, help="YYYY-MM-DD"),
):
    """Create a new trip itinerary."""
    client = GTClient()
    dest_ids = [d.strip() for d in destinations.split(",") if d.strip()]
    try:
        itinerary = client.create_itinerary(title, dest_ids, start_date, end_date)
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print(f"[bold green]Created itinerary '{itinerary['title']}'[/bold green] (id: {itinerary['id']})")


@itineraries_app.command("list")
def itineraries_list():
    """List your itineraries."""
    client = GTClient()
    try:
        items = client.list_itineraries()
    except GTApiError as exc:
        _handle_error(exc)
        return
    if not items:
        console.print("No itineraries yet. Create one with `gt itineraries create`.")
        raise typer.Exit()
    table = Table()
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Dates")
    table.add_column("Destinations")
    for it in items:
        table.add_row(it["id"], it["title"], f"{it['start_date']} → {it['end_date']}", ", ".join(it["destinations"]))
    console.print(table)


@itineraries_app.command("delete")
def itineraries_delete(itinerary_id: str = typer.Argument(...)):
    """Delete one of your itineraries by ID."""
    client = GTClient()
    try:
        client.delete_itinerary(itinerary_id)
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print("Deleted.")


# ---------------------------------------------------------------------------
# places
# ---------------------------------------------------------------------------

@places_app.command("submit")
def places_submit(
    name: str = typer.Option(..., prompt=True),
    region: str = typer.Option(..., prompt=True),
    description: str = typer.Option(..., prompt=True),
    image_url: str = typer.Option(..., prompt=True),
    latitude: float = typer.Option(..., prompt=True),
    longitude: float = typer.Option(..., prompt=True),
    tags: str = typer.Option("", help="Comma-separated tags"),
    avg_cost_fcfa: Optional[int] = typer.Option(None),
):
    """Advertise a new place — submitted for admin review before it appears publicly."""
    client = GTClient()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    try:
        place = client.submit_place(
            name=name, region=region, description=description, image_url=image_url,
            latitude=latitude, longitude=longitude, tags=tag_list, avg_cost_fcfa=avg_cost_fcfa,
        )
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print(f"[bold green]Submitted '{place['name']}'[/bold green] — status: {place['status']} (pending admin review).")


@places_app.command("mine")
def places_mine():
    """List places you've submitted, with their review status."""
    client = GTClient()
    try:
        items = client.my_places()
    except GTApiError as exc:
        _handle_error(exc)
        return
    if not items:
        console.print("You haven't submitted any places yet.")
        raise typer.Exit()
    table = Table()
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Submitted at")
    for p in items:
        table.add_row(p["name"], p["status"], p["submitted_at"])
    console.print(table)


# ---------------------------------------------------------------------------
# feedback
# ---------------------------------------------------------------------------

@feedback_app.command("submit")
def feedback_submit(
    category: str = typer.Option(..., prompt=True, help="bug | suggestion | place_report | other"),
    message: str = typer.Option(..., prompt=True),
    rating: Optional[int] = typer.Option(None, min=1, max=5),
):
    """Send feedback to the GT team."""
    client = GTClient()
    try:
        client.submit_feedback(category, message, rating)
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print("[bold green]Thanks — feedback submitted.[/bold green]")


# ---------------------------------------------------------------------------
# earnings
# ---------------------------------------------------------------------------

@earnings_app.command("heartbeat")
def earnings_heartbeat(elapsed_seconds: int = typer.Argument(90, help="Seconds active since your last heartbeat")):
    """Report active usage time — call this periodically while using the app."""
    client = GTClient()
    try:
        result = client.heartbeat(elapsed_seconds)
    except GTApiError as exc:
        _handle_error(exc)
        return
    status_msg = "5-min daily threshold met!" if result["threshold_met"] else "not yet at today's 5-min threshold"
    console.print(f"Today: {result['active_seconds']}s active — {status_msg}")


@earnings_app.command("show")
def earnings_show():
    """Show your full earnings breakdown: usage days, referrals, feedback, payout eligibility."""
    client = GTClient()
    try:
        e = client.earnings()
    except GTApiError as exc:
        _handle_error(exc)
        return

    console.print(f"[bold]Total earned:[/bold] ${e['total_earned_usd']} (FCFA {e['available_fcfa']:,.0f} available)")
    console.print(f"  Usage: {e['qualifying_days']} qualifying day(s) -> ${e['usage_earnings_usd']}")
    console.print(f"  Referrals: {e['referral_count']} -> ${e['referral_earnings_usd']}")
    console.print(f"  Good feedback given: {e['good_feedback_count']}")
    console.print(f"  Your referral link: {e['referral_link']}")

    elig = e["payout_eligibility"]
    console.print("\n[bold]Payout eligibility:[/bold]")
    for key in ("balance", "referrals", "good_feedback"):
        req = elig[key]
        mark = "[green]✓[/green]" if req["met"] else "[red]✗[/red]"
        console.print(f"  {mark} {key}: {req['have']} / {req['need']}")
    console.print(f"  {'[bold green]Eligible for payout![/bold green]' if elig['eligible'] else '[dim]Not yet eligible.[/dim]'}")


@earnings_app.command("request-payout")
def earnings_request_payout():
    """Request a payout, if eligible."""
    client = GTClient()
    try:
        result = client.request_payout()
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print(f"[bold green]Payout requested:[/bold green] ${result['amount_usd']} (FCFA {result['amount_fcfa']:,.0f}) — status: {result['status']}")


# ---------------------------------------------------------------------------
# notifications
# ---------------------------------------------------------------------------

@notifications_app.command("list")
def notifications_list(unread_only: bool = typer.Option(False, "--unread-only")):
    """List your notifications, newest first."""
    client = GTClient()
    try:
        items = client.list_notifications(unread_only=unread_only)
    except GTApiError as exc:
        _handle_error(exc)
        return
    if not items:
        console.print("No notifications." if not unread_only else "No unread notifications.")
        raise typer.Exit()
    table = Table()
    table.add_column("")
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Category")
    table.add_column("Sent")
    for n in items:
        mark = " " if n["is_read"] else "[bold green]●[/bold green]"
        table.add_row(mark, n["id"][:8], n["title"], n["category"], n["created_at"])
    console.print(table)
    for n in items:
        if not n["is_read"]:
            console.print(f"\n[bold]{n['title']}[/bold]\n{n['message']}")


@notifications_app.command("unread-count")
def notifications_unread_count():
    """Just the unread count — handy for a shell prompt or script."""
    client = GTClient()
    try:
        count = client.unread_notification_count()
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print(str(count))


@notifications_app.command("read")
def notifications_mark_read(
    ids: list[str] = typer.Argument(None, help="Notification IDs to mark read (omit with --all)"),
    all_: bool = typer.Option(False, "--all", help="Mark every notification as read"),
):
    """Mark one, some, or all notifications as read."""
    client = GTClient()
    try:
        result = client.mark_notifications_read(ids=ids or None, all_=all_)
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print(f"Marked {result['marked_read']} notification(s) as read.")


@notifications_app.command("delete")
def notifications_delete(
    ids: list[str] = typer.Argument(None, help="Notification IDs to delete (omit with --all)"),
    all_: bool = typer.Option(False, "--all", help="Delete every notification"),
):
    """Delete one, some, or all notifications."""
    client = GTClient()
    try:
        if ids and len(ids) == 1 and not all_:
            client.delete_notification(ids[0])
            console.print("Deleted 1 notification.")
        else:
            result = client.delete_notifications(ids=ids or None, all_=all_)
            console.print(f"Deleted {result['deleted']} notification(s).")
    except GTApiError as exc:
        _handle_error(exc)


# ---------------------------------------------------------------------------
# misc
# ---------------------------------------------------------------------------

@app.command("config")
def show_config():
    """Show where the CLI is pointing and whether you're logged in."""
    cfg = config.load_config()
    console.print(f"API URL: {cfg['api_url']}")
    console.print(f"Logged in as: {cfg.get('username', '[not logged in]')}")


if __name__ == "__main__":
    app()
