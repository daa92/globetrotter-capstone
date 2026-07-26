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

app.add_typer(auth_app, name="auth")
app.add_typer(destinations_app, name="destinations")
app.add_typer(itineraries_app, name="itineraries")
app.add_typer(places_app, name="places")
app.add_typer(feedback_app, name="feedback")

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
):
    """Create a new GT account."""
    client = GTClient()
    prefs = [p.strip() for p in preferences.split(",") if p.strip()]
    try:
        client.register(username, email, password, prefs)
    except GTApiError as exc:
        _handle_error(exc)
        return
    console.print(f"[bold green]Account created for {username}.[/bold green] Now run `gt auth login`.")


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
