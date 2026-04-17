import typer

app = typer.Typer(help="Nimble — cross-platform Python hotkey daemon.")

_PLACEHOLDER_HELP = "Placeholder — daemon commands added in Epic 2."


def placeholder() -> None:
    typer.echo("Use 'nimble --help' to see available commands.")


app.command(name="placeholder", help=_PLACEHOLDER_HELP)(placeholder)
# Typer/Click subcommands are case-sensitive; common mistake is Title Case from prose.
app.command(name="Placeholder", help=_PLACEHOLDER_HELP, hidden=True)(placeholder)


if __name__ == "__main__":
    app()
