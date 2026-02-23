"""CLI interface for wohnung-scraper development tasks."""

import shutil
import subprocess
import traceback
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from wohnung.marker_detector import MarkerDetector
from wohnung.models import Flat
from wohnung.site_config import SiteConfigLoader
from wohnung.site_storage import SiteStorage

app = typer.Typer(
    name="wohnung",
    help="🏠 Wohnung Scraper - Development & Operations CLI",
    add_completion=True,
    rich_markup_mode="rich",
)

board_app = typer.Typer(
    name="board",
    help="📋 Manage GitHub issues and project board",
)
app.add_typer(board_app, name="board")

site_app = typer.Typer(
    name="site",
    help="🌐 Manage site configurations",
)
app.add_typer(site_app, name="site")

console = Console()


def run_command(
    cmd: list[str],
    description: str,
    check: bool = True,
    cwd: Path | None = None,
) -> "subprocess.CompletedProcess[bytes]":
    """Run a shell command with nice output."""
    console.print(f"[cyan]▶[/cyan] {description}")
    result = subprocess.run(cmd, cwd=cwd, check=False)
    if check and result.returncode != 0:
        console.print(f"[red]✗[/red] {description} failed", style="bold red")
        raise typer.Exit(code=result.returncode)
    console.print(f"[green]✓[/green] {description} completed\n")
    return result


def check_gh_cli() -> bool:
    """Check if GitHub CLI is installed."""
    result = subprocess.run(["which", "gh"], capture_output=True, check=False)
    return result.returncode == 0


def ensure_gh_cli() -> None:
    """Ensure GitHub CLI is installed, exit with instructions if not."""
    if not check_gh_cli():
        console.print(
            Panel.fit(
                "[red]GitHub CLI not found![/red]\n\n"
                "Install it to use board commands:\n"
                "• macOS: [cyan]brew install gh[/cyan]\n"
                "• Linux: [cyan]https://github.com/cli/cli/blob/trunk/docs/install_linux.md[/cyan]\n"
                "• Windows: [cyan]winget install GitHub.cli[/cyan]\n\n"
                "Then authenticate: [cyan]gh auth login[/cyan]",
                title="❌ Missing Dependency",
                border_style="red",
            )
        )
        raise typer.Exit(1)


# Board management commands
@board_app.command("create")
def board_create_issue(
    title: Annotated[str, typer.Argument(help="Issue title")],
    body: Annotated[str | None, typer.Option("--body", "-b", help="Issue description")] = None,
    labels: Annotated[
        str | None, typer.Option("--labels", "-l", help="Comma-separated labels")
    ] = None,
    template: Annotated[
        str | None,
        typer.Option("--template", "-t", help="Use template: bug, feature, scraper"),
    ] = None,
) -> None:
    """Create a new GitHub issue/backlog item."""
    ensure_gh_cli()

    # Use template if specified
    if template:
        templates = {
            "bug": {
                "labels": "bug",
                "body": "## 🐛 Bug Description\n\n{}\n\n## Steps to Reproduce\n\n1. \n\n## Expected Behavior\n\n\n## Actual Behavior\n\n",
            },
            "feature": {
                "labels": "enhancement",
                "body": "## ✨ Feature Description\n\n{}\n\n## Motivation\n\n\n## Proposed Solution\n\n",
            },
            "scraper": {
                "labels": "scraper,enhancement",
                "body": "## 🏠 Scraper: {}\n\n**Website URL:** \n\n**Listing URL Pattern:** \n\n## Requirements\n\n- [ ] Scraper implementation\n- [ ] Tests with mocked responses\n- [ ] Update SCRAPERS registry\n- [ ] Update README\n\n## Notes\n\n",
            },
        }

        if template not in templates:
            console.print(f"[red]Unknown template:[/red] {template}", style="bold")
            console.print(f"[yellow]Available templates:[/yellow] {', '.join(templates.keys())}")
            raise typer.Exit(1)

        tmpl = templates[template]
        if not labels:
            labels = tmpl["labels"]
        if not body:
            body = tmpl["body"].format(title if template == "scraper" else "")

    # Build gh issue create command
    cmd = ["gh", "issue", "create", "--title", title]

    if body:
        cmd.extend(["--body", body])
    if labels:
        cmd.extend(["--label", labels])

    console.print(f"[cyan]Creating issue:[/cyan] {title}")
    result = subprocess.run(cmd, check=False)

    if result.returncode == 0:
        console.print(Panel.fit("✅ [green]Issue created![/green]", border_style="green"))
    else:
        console.print(Panel.fit("❌ [red]Failed to create issue[/red]", border_style="red"))
        raise typer.Exit(result.returncode)


@board_app.command("list")
def board_list_issues(
    state: Annotated[
        str, typer.Option("--state", "-s", help="Issue state: open, closed, all")
    ] = "open",
    labels: Annotated[str | None, typer.Option("--labels", "-l", help="Filter by labels")] = None,
    limit: Annotated[int, typer.Option("--limit", help="Number of issues to show")] = 20,
) -> None:
    """List GitHub issues."""
    ensure_gh_cli()

    cmd = ["gh", "issue", "list", "--state", state, "--limit", str(limit)]

    if labels:
        cmd.extend(["--label", labels])

    console.print(f"[cyan]Fetching issues (state={state})...[/cyan]\n")
    subprocess.run(cmd, check=False)


@board_app.command("view")
def board_view_issue(
    issue_number: Annotated[int, typer.Argument(help="Issue number")],
    web: Annotated[bool, typer.Option("--web", "-w", help="Open in browser")] = False,
) -> None:
    """View an issue."""
    ensure_gh_cli()

    if web:
        subprocess.run(["gh", "issue", "view", str(issue_number), "--web"], check=False)
    else:
        subprocess.run(["gh", "issue", "view", str(issue_number)], check=False)


@board_app.command("templates")
def board_show_templates() -> None:
    """Show available issue templates."""
    table = Table(title="📝 Issue Templates", show_header=True, header_style="bold cyan")
    table.add_column("Template", style="cyan", width=15)
    table.add_column("Labels", style="yellow", width=20)
    table.add_column("Usage", style="green")

    table.add_row(
        "bug",
        "bug",
        "wohnung board create 'Bug title' -t bug",
    )
    table.add_row(
        "feature",
        "enhancement",
        "wohnung board create 'Feature title' -t feature",
    )
    table.add_row(
        "scraper",
        "scraper, enhancement",
        "wohnung board create 'Site name' -t scraper",
    )

    console.print(table)
    console.print("\n[dim]Tip: You can override labels with --labels[/dim]")


@board_app.command("setup-check")
def board_setup_check() -> None:
    """Check if GitHub CLI is installed and authenticated."""
    if not check_gh_cli():
        ensure_gh_cli()  # Will show installation instructions and exit
        return

    console.print("[green]✓[/green] GitHub CLI is installed")

    # Check authentication
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, check=False)

    if result.returncode == 0:
        console.print("[green]✓[/green] GitHub CLI is authenticated")
        console.print(
            Panel.fit(
                "✅ [green]All set![/green]\n\n" "Try: [cyan]wohnung board list[/cyan]",
                border_style="green",
            )
        )
    else:
        console.print("[red]✗[/red] GitHub CLI is not authenticated")
        console.print(
            Panel.fit(
                "[yellow]Authenticate GitHub CLI:[/yellow]\n\n"
                "[cyan]gh auth login[/cyan]\n\n"
                "Follow the prompts to authenticate.",
                border_style="yellow",
            )
        )
        raise typer.Exit(1)


# Site configuration management commands
@site_app.command("list")
def site_list() -> None:
    """List all available site configurations."""
    loader = SiteConfigLoader("sites")

    try:
        all_sites = loader.load_all_sites()

        if not all_sites:
            console.print("[yellow]No site configurations found in sites/ directory[/yellow]")
            console.print("\n[dim]Tip: Create a .yaml file in the sites/ directory[/dim]")
            return

        table = Table(title="🌐 Site Configurations", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="cyan")
        table.add_column("Display Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Markers", style="magenta")

        for name, config in sorted(all_sites.items()):
            status = "✅ Enabled" if config.enabled else "❌ Disabled"
            marker_count = len(config.markers)
            table.add_row(
                name,
                config.display_name,
                status,
                f"{marker_count} markers",
            )

        console.print(table)
        console.print(f"\n[dim]Total: {len(all_sites)} site(s)[/dim]")
    except Exception as e:
        console.print(f"[red]Error loading sites:[/red] {e}")
        raise typer.Exit(1) from e


@site_app.command("validate")
def site_validate(
    config_file: Annotated[Path, typer.Argument(help="Path to YAML config file")],
) -> None:
    """Validate a site configuration file."""
    loader = SiteConfigLoader()

    console.print(f"[cyan]Validating:[/cyan] {config_file}")

    is_valid, message = loader.validate_config(config_file)

    if is_valid:
        console.print(
            Panel.fit(
                f"[green]{message}[/green]",
                title="✅ Valid Configuration",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel.fit(
                f"[red]{message}[/red]",
                title="❌ Invalid Configuration",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@site_app.command("info")
def site_info(
    site_name: Annotated[str, typer.Argument(help="Site name (e.g., oevw)")],
) -> None:
    """Show detailed information about a site configuration."""
    loader = SiteConfigLoader("sites")

    try:
        all_sites = loader.load_all_sites()

        if site_name not in all_sites:
            console.print(f"[red]Site '{site_name}' not found[/red]")
            console.print(f"\n[yellow]Available sites:[/yellow] {', '.join(all_sites.keys())}")
            raise typer.Exit(1)

        config = all_sites[site_name]

        # Basic info
        console.print(
            Panel(
                f"[bold]{config.display_name}[/bold]\n\n"
                f"[cyan]Name:[/cyan] {config.name}\n"
                f"[cyan]URL:[/cyan] {config.base_url}\n"
                f"[cyan]Status:[/cyan] {'✅ Enabled' if config.enabled else '❌ Disabled'}\n"
                f"[cyan]Timeout:[/cyan] {config.request_timeout}s\n"
                f"[cyan]Rate Limit:[/cyan] {config.rate_limit_delay}s between requests",
                title="🌐 Site Information",
                border_style="cyan",
            )
        )

        # Selectors
        console.print("\n[bold]Selectors:[/bold]")
        selector_table = Table(show_header=False)
        selector_table.add_column("Field", style="cyan")
        selector_table.add_column("Selector", style="green")

        for field, selector in config.selectors.model_dump().items():
            if selector:
                selector_table.add_row(field, selector)

        console.print(selector_table)

        # Markers
        if config.markers:
            console.print(f"\n[bold]Markers ({len(config.markers)}):[/bold]")
            marker_table = Table(show_header=True, header_style="bold magenta")
            marker_table.add_column("Label")
            marker_table.add_column("Priority")
            marker_table.add_column("Patterns")

            for marker in config.markers:
                marker_table.add_row(
                    marker.label,
                    marker.priority.upper(),
                    ", ".join(marker.patterns[:3]) + ("..." if len(marker.patterns) > 3 else ""),
                )

            console.print(marker_table)

        # Pagination
        if config.pagination and config.pagination.enabled:
            console.print(
                f"\n[bold]Pagination:[/bold] ✅ Enabled (max {config.pagination.max_pages} pages)"
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@site_app.command("test-markers")
def site_test_markers(  # noqa: PLR0915
    site_name: Annotated[str, typer.Argument(help="Site name (e.g., oevw)")],
    limit: Annotated[int, typer.Option(help="Maximum apartments to test")] = 10,
) -> None:
    """Test marker detection on stored apartments for a site."""
    loader = SiteConfigLoader("sites")
    storage = SiteStorage("data")

    try:
        # Load site config
        all_sites = loader.load_all_sites()
        if site_name not in all_sites:
            console.print(f"[red]Site '{site_name}' not found[/red]")
            console.print(f"\n[yellow]Available sites:[/yellow] {', '.join(all_sites.keys())}")
            raise typer.Exit(1)

        config = all_sites[site_name]

        # Check if site has markers configured
        if not config.markers:
            console.print(f"[yellow]Site '{site_name}' has no markers configured[/yellow]")
            raise typer.Exit(0)

        console.print(
            Panel(
                f"[bold]{config.display_name}[/bold]\n\n"
                f"[cyan]Markers configured:[/cyan] {len(config.markers)}\n"
                f"[cyan]Testing on:[/cyan] Up to {limit} apartments",
                title="🏷️  Marker Detection Test",
                border_style="cyan",
            )
        )

        # Load apartments from storage
        apartments_meta = storage.get_active_apartments(site_name)
        if not apartments_meta:
            console.print(f"\n[yellow]No apartments found for site '{site_name}'[/yellow]")
            console.print("[dim]Run 'wohnung scrape' first to collect apartments[/dim]")
            raise typer.Exit(0)

        console.print(f"\n[cyan]Found {len(apartments_meta)} active apartments[/cyan]")

        # Initialize marker detector
        detector = MarkerDetector(config.markers)

        # Test marker detection
        results_table = Table(show_header=True, header_style="bold magenta")
        results_table.add_column("Apartment", max_width=40)
        results_table.add_column("Markers", max_width=60)

        tested_count = 0
        total_markers_found = 0

        for apt_id, apt_meta in list(apartments_meta.items())[:limit]:
            # Convert metadata to Flat model
            flat_data = apt_meta.data.copy()
            flat_data["id"] = apt_id
            flat = Flat(**flat_data)

            # Detect markers
            detected = detector.detect_markers(flat)

            if detected:
                total_markers_found += len(detected)
                marker_labels = []
                for marker_name in detected:
                    label = detector.get_marker_label(marker_name)
                    priority = detector.get_marker_priority(marker_name)
                    priority_icon = (
                        "🔴" if priority == "high" else "🟡" if priority == "medium" else "⚪"
                    )
                    marker_labels.append(f"{priority_icon} {label or marker_name}")

                results_table.add_row(
                    flat.title[:40],
                    "\n".join(marker_labels),
                )

            tested_count += 1

        console.print("\n[bold]Results:[/bold]")
        console.print(results_table)

        console.print(
            f"\n[cyan]Tested:[/cyan] {tested_count} apartments\n"
            f"[cyan]Markers found:[/cyan] {total_markers_found} total"
        )

        # Show marker patterns for reference
        console.print("\n[bold]Configured Markers:[/bold]")
        marker_info_table = Table(show_header=True, header_style="bold")
        marker_info_table.add_column("Label")
        marker_info_table.add_column("Priority")
        marker_info_table.add_column("Patterns")

        for marker in config.markers:
            priority_icon = (
                "🔴" if marker.priority == "high" else "🟡" if marker.priority == "medium" else "⚪"
            )
            marker_info_table.add_row(
                marker.label,
                f"{priority_icon} {marker.priority.upper()}",
                ", ".join(marker.patterns[:2]) + ("..." if len(marker.patterns) > 2 else ""),
            )

        console.print(marker_info_table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@site_app.command("new")
def site_new(
    site_name: Annotated[str, typer.Argument(help="Site name (e.g., immoscout24)")],
    url: Annotated[str | None, typer.Option(help="Base URL for the site")] = None,
    display_name: Annotated[str | None, typer.Option(help="Display name for the site")] = None,
) -> None:
    """Generate a new site configuration template."""
    # Validate site name
    if not site_name.replace("-", "").replace("_", "").isalnum():
        console.print(
            "[red]Site name must contain only letters, numbers, hyphens, and underscores[/red]"
        )
        raise typer.Exit(1)

    # Check if file already exists
    sites_dir = Path("sites")
    sites_dir.mkdir(exist_ok=True)
    config_file = sites_dir / f"{site_name}.yaml"

    if config_file.exists():
        console.print(f"[yellow]Warning:[/yellow] {config_file} already exists!")
        overwrite = typer.confirm("Overwrite?")
        if not overwrite:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    # Interactive prompts if not provided
    if url is None:
        url = typer.prompt("Base URL")

    if display_name is None:
        # Generate default display name (capitalize words)
        default_display = " ".join(
            word.capitalize() for word in site_name.replace("-", " ").replace("_", " ").split()
        )
        display_name = typer.prompt("Display name", default=default_display)

    # Generate template
    template = {
        "name": site_name,
        "display_name": display_name,
        "base_url": url,
        "enabled": False,  # Disabled by default
        "selectors": {
            "listing": "article.listing, div.apartment-card  # TODO: Update selector",
            "title": "h2, h3.title  # TODO: Update selector",
            "url": "a.listing-link  # TODO: Update selector",
            "location": ".location, .address  # TODO: Update selector",
            "price": ".price  # Optional",
            "size": ".size  # Optional",
            "rooms": ".rooms  # Optional",
            "description": ".description  # Optional",
            "image": "img.apartment-image  # Optional",
        },
        "pagination": {
            "enabled": False,
            "max_pages": 5,
            "url_pattern": "?page={page}  # OR use next_selector",
        },
        "markers": [
            {
                "name": "example_marker",
                "label": "Example Marker",
                "patterns": ["keyword1", "keyword2"],
                "priority": "medium",
                "search_in": ["title", "description"],
            }
        ],
        "request_timeout": 30,
        "rate_limit_delay": 1.0,
    }

    # Write to file
    with open(config_file, "w", encoding="utf-8") as f:
        # Add header comments
        f.write(f"# {display_name} Configuration\n")
        f.write("# TODO: Update selectors after inspecting the website\n")
        f.write(f"# Base URL: {url}\n\n")

        # Write YAML with nice formatting
        yaml.dump(template, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    console.print(f"\n[green]✓[/green] Created {config_file}")
    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"1. Edit the configuration: [cyan]vim {config_file}[/cyan]")
    console.print("2. Update the selectors after inspecting the website")
    console.print(f"3. Validate: [cyan]wohnung site validate {config_file}[/cyan]")
    console.print(f"4. Test: [cyan]wohnung site test {site_name}[/cyan]")
    console.print(f"5. Enable: Set [cyan]enabled: true[/cyan] in {config_file}")
    console.print("\n[dim]See docs/adding-sites.md for detailed instructions[/dim]")


@site_app.command("test")
def site_test(  # noqa: C901, PLR0912, PLR0915
    site_name: Annotated[str, typer.Argument(help="Site name to test")],
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show verbose output")] = False,
) -> None:
    """Test and validate a site configuration (dry-run)."""
    loader = SiteConfigLoader("sites")

    try:
        # Load site config
        all_sites = loader.load_all_sites()

        if site_name not in all_sites:
            console.print(f"[red]Site '{site_name}' not found[/red]")
            console.print(f"\n[yellow]Available sites:[/yellow] {', '.join(all_sites.keys())}")
            raise typer.Exit(1)

        config = all_sites[site_name]

        console.print(
            Panel(
                f"[bold]{config.display_name}[/bold]\n\n"
                f"[cyan]URL:[/cyan] {config.base_url}\n"
                f"[cyan]Enabled:[/cyan] {'Yes' if config.enabled else 'No'}\n"
                f"[cyan]Timeout:[/cyan] {config.request_timeout}s\n"
                f"[cyan]Rate limit:[/cyan] {config.rate_limit_delay}s",
                title="🧪 Site Configuration Test",
                border_style="cyan",
            )
        )

        # Show selectors
        console.print("\n[bold]Configured Selectors:[/bold]")
        selector_table = Table(show_header=True, header_style="bold magenta")
        selector_table.add_column("Field")
        selector_table.add_column("Selector")
        selector_table.add_column("Required")

        selectors_dict = config.selectors.model_dump()
        required = ["listing", "title", "url", "location"]

        for field, selector in selectors_dict.items():
            if selector:
                is_required = "✓" if field in required else ""
                selector_table.add_row(field, selector, is_required)

        console.print(selector_table)

        # Show pagination if configured
        if config.pagination and config.pagination.enabled:
            console.print("\n[bold]Pagination:[/bold] Enabled")
            console.print(f"  Max pages: {config.pagination.max_pages}")
            if config.pagination.url_pattern:
                console.print(f"  Pattern: {config.pagination.url_pattern}")
            if config.pagination.next_selector:
                console.print(f"  Next selector: {config.pagination.next_selector}")

        # Show markers if configured
        if config.markers:
            console.print(f"\n[bold]Markers:[/bold] {len(config.markers)} configured")
            for marker in config.markers[:3]:  # Show first 3
                priority_icon = (
                    "🔴"
                    if marker.priority == "high"
                    else "🟡"
                    if marker.priority == "medium"
                    else "⚪"
                )
                console.print(f"  {priority_icon} {marker.label}: {', '.join(marker.patterns[:2])}")
            if len(config.markers) > 3:
                console.print(f"  [dim]... and {len(config.markers) - 3} more[/dim]")

        # Validation summary
        console.print("\n[bold]Validation:[/bold]")
        all_good = True

        # Check required selectors
        required_present = [bool(getattr(config.selectors, field)) for field in required]
        if not all(required_present):
            console.print("  [red]✗[/red] Missing required selectors")
            all_good = False
        else:
            console.print("  [green]✓[/green] All required selectors present")

        # Check base URL
        if config.base_url:
            console.print("  [green]✓[/green] Base URL configured")
        else:
            console.print("  [red]✗[/red] Missing base URL")
            all_good = False

        if all_good:
            console.print("\n[green]✓[/green] Configuration looks good!")
            console.print("\n[bold]Next steps:[/bold]")
            console.print("  1. Run actual scrape test (requires scraper implementation)")
            console.print("  2. Enable the site: Set [cyan]enabled: true[/cyan] in config")
            console.print("  3. Run: [cyan]wohnung scrape[/cyan]")
        else:
            console.print("\n[yellow]⚠[/yellow] Configuration has issues - please fix before using")

        console.print("\n[dim]Note: Full scraping test requires scraper implementation.[/dim]")
        console.print("[dim]Use 'wohnung scrape' once the site is enabled.[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            console.print("\n[dim]" + traceback.format_exc() + "[/dim]")
        raise typer.Exit(1) from e


@app.command()
def install(
    skip_hooks: Annotated[
        bool, typer.Option("--skip-hooks", help="Skip pre-commit hook installation")
    ] = False,
) -> None:
    """Install dependencies and set up development environment."""
    run_command(["uv", "sync", "--all-extras"], "Installing dependencies with uv")

    if not skip_hooks:
        run_command(["uv", "run", "pre-commit", "install"], "Installing pre-commit hooks")

    console.print(Panel.fit("✨ [green]Installation complete![/green]", border_style="green"))


@app.command()
def test(
    coverage: Annotated[bool, typer.Option("--coverage/--no-coverage")] = True,
    verbose: Annotated[bool, typer.Option("-v", "--verbose")] = False,
    fast: Annotated[bool, typer.Option("-x", "--fast", help="Stop on first failure")] = False,
) -> None:
    """Run the test suite."""
    cmd = ["uv", "run", "pytest"]

    if coverage:
        cmd.extend(["--cov", "--cov-report=term-missing"])
    if verbose:
        cmd.append("-v")
    if fast:
        cmd.append("-x")

    run_command(cmd, "Running tests")


@app.command()
def lint(
    fix: Annotated[bool, typer.Option("--fix", help="Auto-fix issues")] = False,
    complexity: Annotated[bool, typer.Option("--complexity", help="Show complexity only")] = False,
) -> None:
    """Run ruff linter (includes complexity checks)."""
    if complexity:
        run_command(
            ["uv", "run", "ruff", "check", "--select", "C90", "src", "tests"],
            "Checking code complexity (max: 10)",
        )
    else:
        cmd = ["uv", "run", "ruff", "check"]
        if fix:
            cmd.append("--fix")
        cmd.extend(["src", "tests"])
        run_command(cmd, "Running ruff linter")


@app.command()
def format(
    check: Annotated[bool, typer.Option("--check", help="Check only, don't modify")] = False,
) -> None:
    """Format code with black."""
    cmd = ["uv", "run", "black"]
    if check:
        cmd.append("--check")
    cmd.extend(["src", "tests"])

    action = "Checking" if check else "Formatting"
    run_command(cmd, f"{action} code with black")


@app.command(name="type-check")
def type_check() -> None:
    """Run mypy type checker."""
    run_command(["uv", "run", "mypy", "src"], "Running mypy type checker")


@app.command(name="pre-commit")
def pre_commit_run(
    all_files: Annotated[bool, typer.Option("--all-files")] = True,
) -> None:
    """Run pre-commit hooks."""
    cmd = ["uv", "run", "pre-commit", "run"]
    if all_files:
        cmd.append("--all-files")

    run_command(cmd, "Running pre-commit hooks")


@app.command()
def check() -> None:
    """Run all quality checks (lint, format check, type check)."""
    console.print(Panel("🔍 Running all quality checks", style="cyan bold"))

    try:
        run_command(
            ["uv", "run", "ruff", "check", "src", "tests"],
            "Linting with ruff",
        )
        run_command(
            ["uv", "run", "black", "--check", "src", "tests"],
            "Checking code formatting",
        )
        run_command(
            ["uv", "run", "mypy", "src"],
            "Type checking with mypy",
        )

        console.print(Panel.fit("✅ [green]All checks passed![/green]", border_style="green"))
    except typer.Exit:
        console.print(Panel.fit("❌ [red]Some checks failed[/red]", border_style="red"))
        raise


@app.command(name="all")
def run_all() -> None:
    """Run all checks and tests."""
    console.print(Panel("🚀 Running full validation", style="cyan bold"))

    try:
        # Run checks first
        run_command(
            ["uv", "run", "ruff", "check", "src", "tests"],
            "Linting with ruff",
        )
        run_command(
            ["uv", "run", "black", "--check", "src", "tests"],
            "Checking code formatting",
        )
        run_command(
            ["uv", "run", "mypy", "src"],
            "Type checking with mypy",
        )

        # Then run tests
        run_command(
            ["uv", "run", "pytest", "--cov", "--cov-report=term-missing"],
            "Running tests with coverage",
        )

        console.print(Panel.fit("✅ [green]All validations passed![/green]", border_style="green"))
    except typer.Exit:
        console.print(Panel.fit("❌ [red]Some validations failed[/red]", border_style="red"))
        raise


@app.command()
def clean() -> None:
    """Clean up cache and build artifacts."""
    patterns = [
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "htmlcov",
        ".coverage",
        "__pycache__",
        "*.pyc",
    ]

    root = Path.cwd()
    removed = []

    # Remove specific directories
    for pattern in patterns[:5]:
        for path in root.rglob(pattern):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                removed.append(str(path.relative_to(root)))
            elif path.is_file():
                path.unlink(missing_ok=True)
                removed.append(str(path.relative_to(root)))

    # Remove __pycache__ directories
    for path in root.rglob("__pycache__"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            removed.append(str(path.relative_to(root)))

    # Remove .pyc files
    for path in root.rglob("*.pyc"):
        path.unlink(missing_ok=True)
        removed.append(str(path.relative_to(root)))

    if removed:
        console.print(f"[green]✓[/green] Cleaned {len(removed)} items")
    else:
        console.print("[yellow]No artifacts to clean[/yellow]")


@app.command()
def scrape(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Run without sending emails")] = False,
) -> None:
    """Run the flat scraper."""
    cmd = ["uv", "run", "wohnung-scrape"]
    if dry_run:
        cmd.append("--dry-run")

    mode = "dry-run mode" if dry_run else "production mode"
    run_command(cmd, f"Running scraper in {mode}")


@app.command()
def info() -> None:
    """Show project information and available commands."""
    table = Table(title="🏠 Wohnung Scraper", show_header=True, header_style="bold cyan")
    table.add_column("Category", style="cyan", width=20)
    table.add_column("Commands", style="green")

    table.add_row(
        "Setup",
        "install",
    )
    table.add_row(
        "Testing",
        "test [--no-coverage] [-v] [-x]",
    )
    table.add_row(
        "Code Quality",
        "lint [--fix] [--complexity]\nformat [--check]\ntype-check\npre-commit\ncheck\nall",
    )
    table.add_row(
        "Scraping",
        "scrape [--dry-run]",
    )
    table.add_row(
        "Maintenance",
        "clean\ninfo",
    )
    table.add_row(
        "Board/Issues",
        "board create TITLE [--template bug|feature|scraper]\nboard list [--state open|closed|all]\nboard view NUMBER\nboard templates\nboard setup-check",
    )
    table.add_row(
        "Site Config",
        "site list\nsite new NAME [--url URL]\nsite validate FILE\nsite info SITE\nsite test SITE\nsite test-markers SITE [--limit N]",
    )

    console.print(table)
    console.print("\n[dim]Run 'wohnung --help' or 'wohnung COMMAND --help' for more details[/dim]")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
