import typer

app = typer.Typer(help="Nimble — cross-platform Python hotkey daemon.")


@app.command()
def placeholder() -> None:
    """Placeholder — daemon commands added in Epic 2."""
    typer.echo("Use 'nimble --help' to see available commands.")


if __name__ == "__main__":
    app()
