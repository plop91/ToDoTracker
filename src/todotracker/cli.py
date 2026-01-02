"""CLI interface for ToDoTracker."""

import asyncio
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from todotracker.database import get_async_session_maker, init_db
from todotracker.services.todo_service import (
    TodoService,
    CategoryService,
    TagService,
    PriorityService,
)
from todotracker.schemas.todo import TodoCreate, TodoUpdate

app = typer.Typer(
    name="todo",
    help="ToDoTracker - Spend less time setting up, more time doing.",
    no_args_is_help=True,
)
console = Console()


def run_async(coro):
    """Run async function in sync context."""
    return asyncio.run(coro)


async def ensure_db():
    """Ensure database is initialized."""
    await init_db()
    async with get_async_session_maker()() as session:
        priority_service = PriorityService(session)
        await priority_service.seed_defaults()
        await session.commit()


@app.command()
def add(
    title: str = typer.Argument(..., help="Todo title"),
    description: str = typer.Option(None, "--desc", "-d", help="Description"),
    due: Optional[str] = typer.Option(None, "--due", help="Due date (YYYY-MM-DD HH:MM)"),
    priority: int = typer.Option(5, "--priority", "-p", min=1, max=10, help="Priority (1-10)"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Category name"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    parent: Optional[str] = typer.Option(None, "--parent", help="Parent todo ID for subtask"),
):
    """Add a new todo."""

    async def _add():
        await ensure_db()
        async with get_async_session_maker()() as session:
            # Resolve category
            category_id = None
            if category:
                cat_service = CategoryService(session)
                categories = await cat_service.get_all()
                for c in categories:
                    if c.name.lower() == category.lower():
                        category_id = c.id
                        break
                if not category_id:
                    # Create category if it doesn't exist
                    new_cat = await cat_service.create(name=category)
                    category_id = new_cat.id

            # Resolve tags
            tag_ids = []
            if tags:
                tag_service = TagService(session)
                existing_tags = await tag_service.get_all()
                tag_map = {t.name.lower(): t.id for t in existing_tags}

                for tag_name in tags.split(","):
                    tag_name = tag_name.strip()
                    if tag_name.lower() in tag_map:
                        tag_ids.append(tag_map[tag_name.lower()])
                    else:
                        new_tag = await tag_service.create(name=tag_name)
                        tag_ids.append(new_tag.id)

            # Parse due date
            due_date = None
            if due:
                try:
                    due_date = datetime.fromisoformat(due.replace(" ", "T"))
                except ValueError:
                    console.print(f"[red]Invalid date format: {due}[/red]")
                    console.print("Use format: YYYY-MM-DD or YYYY-MM-DD HH:MM")
                    raise typer.Exit(1)

            todo_service = TodoService(session)
            todo_data = TodoCreate(
                title=title,
                description=description,
                due_date=due_date,
                priority=priority,
                category_id=category_id,
                tag_ids=tag_ids,
                parent_id=parent,
            )

            if parent:
                todo = await todo_service.add_subtask(parent, todo_data)
                if not todo:
                    console.print(f"[red]Parent todo not found: {parent}[/red]")
                    raise typer.Exit(1)
            else:
                todo = await todo_service.create(todo_data)

            await session.commit()

            console.print(Panel(
                f"[green]Created:[/green] {todo.title}\n"
                f"[dim]ID: {todo.id}[/dim]",
                title="Todo Added",
            ))

    run_async(_add())


@app.command("list")
def list_todos(
    all_todos: bool = typer.Option(False, "--all", "-a", help="Show completed todos too"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    priority_min: Optional[int] = typer.Option(None, "--priority-min", help="Minimum priority"),
    today: bool = typer.Option(False, "--today", help="Show todos due today"),
):
    """List todos."""

    async def _list():
        await ensure_db()
        async with get_async_session_maker()() as session:
            todo_service = TodoService(session)

            # Resolve category
            category_id = None
            if category:
                cat_service = CategoryService(session)
                categories = await cat_service.get_all()
                for c in categories:
                    if c.name.lower() == category.lower():
                        category_id = c.id
                        break

            due_before = None
            due_after = None
            if today:
                now = datetime.now()
                due_after = now.replace(hour=0, minute=0, second=0, microsecond=0)
                due_before = now.replace(hour=23, minute=59, second=59, microsecond=999999)

            todos, total = await todo_service.get_all(
                completed=None if all_todos else False,
                category_id=category_id,
                priority_min=priority_min,
                due_before=due_before,
                due_after=due_after,
            )

            if not todos:
                console.print("[dim]No todos found.[/dim]")
                return

            table = Table(title=f"Todos ({total} total)")
            table.add_column("ID", style="dim", width=8)
            table.add_column("Pri", justify="center", width=3)
            table.add_column("Title", style="bold")
            table.add_column("Due", width=16)
            table.add_column("Category", style="cyan")
            table.add_column("Tags", style="magenta")

            for todo in todos:
                # Priority color
                pri_color = "green" if todo.priority <= 3 else "yellow" if todo.priority <= 6 else "red"
                pri = f"[{pri_color}]{todo.priority}[/{pri_color}]"

                # Format due date
                due_str = ""
                if todo.due_date:
                    due_str = todo.due_date.strftime("%Y-%m-%d %H:%M")

                # Category
                cat_name = todo.category.name if todo.category else ""

                # Tags
                tag_names = ", ".join(t.name for t in todo.tags)

                # Title with completion status
                title = todo.title
                if todo.completed:
                    title = f"[strike dim]{title}[/strike dim]"

                table.add_row(
                    todo.id[:8],
                    pri,
                    title,
                    due_str,
                    cat_name,
                    tag_names,
                )

                # Show subtasks
                for subtask in todo.subtasks:
                    sub_title = f"  +-- {subtask.title}"
                    if subtask.completed:
                        sub_title = f"[strike dim]{sub_title}[/strike dim]"
                    table.add_row(
                        subtask.id[:8],
                        f"[dim]{subtask.priority}[/dim]",
                        sub_title,
                        "",
                        "",
                        "",
                    )

            console.print(table)

    run_async(_list())


@app.command()
def done(
    todo_id: str = typer.Argument(..., help="Todo ID (or partial ID)"),
):
    """Mark a todo as complete."""

    async def _done():
        await ensure_db()
        async with get_async_session_maker()() as session:
            todo_service = TodoService(session)

            # Try to find by partial ID
            todos, _ = await todo_service.get_all(page_size=100)
            found = None
            for t in todos:
                if t.id.startswith(todo_id):
                    found = t
                    break
                # Also check subtasks
                for s in t.subtasks:
                    if s.id.startswith(todo_id):
                        found = s
                        break

            if not found:
                console.print(f"[red]Todo not found: {todo_id}[/red]")
                raise typer.Exit(1)

            todo = await todo_service.mark_complete(found.id)
            await session.commit()

            console.print(f"[green]Completed:[/green] {todo.title}")

    run_async(_done())


@app.command()
def delete(
    todo_id: str = typer.Argument(..., help="Todo ID (or partial ID)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a todo."""

    async def _delete():
        await ensure_db()
        async with get_async_session_maker()() as session:
            todo_service = TodoService(session)

            # Find todo
            todo = await todo_service.get_by_id(todo_id)
            if not todo:
                # Try partial match
                todos, _ = await todo_service.get_all(page_size=100)
                for t in todos:
                    if t.id.startswith(todo_id):
                        todo = t
                        break

            if not todo:
                console.print(f"[red]Todo not found: {todo_id}[/red]")
                raise typer.Exit(1)

            if not force:
                confirm = typer.confirm(f"Delete '{todo.title}'?")
                if not confirm:
                    raise typer.Abort()

            await todo_service.delete(todo.id)
            await session.commit()

            console.print(f"[red]Deleted:[/red] {todo.title}")

    run_async(_delete())


@app.command()
def categories():
    """List all categories."""

    async def _categories():
        await ensure_db()
        async with get_async_session_maker()() as session:
            service = CategoryService(session)
            cats = await service.get_all()

            if not cats:
                console.print("[dim]No categories found.[/dim]")
                return

            table = Table(title="Categories")
            table.add_column("ID", style="dim", width=8)
            table.add_column("Name", style="bold")
            table.add_column("Color")
            table.add_column("Icon")

            for cat in cats:
                table.add_row(
                    cat.id[:8],
                    cat.name,
                    cat.color or "",
                    cat.icon or "",
                )

            console.print(table)

    run_async(_categories())


@app.command()
def tags():
    """List all tags."""

    async def _tags():
        await ensure_db()
        async with get_async_session_maker()() as session:
            service = TagService(session)
            all_tags = await service.get_all()

            if not all_tags:
                console.print("[dim]No tags found.[/dim]")
                return

            table = Table(title="Tags")
            table.add_column("ID", style="dim", width=8)
            table.add_column("Name", style="bold")
            table.add_column("Color")

            for tag in all_tags:
                table.add_row(
                    tag.id[:8],
                    tag.name,
                    tag.color or "",
                )

            console.print(table)

    run_async(_tags())


@app.command()
def priorities():
    """List priority levels."""

    async def _priorities():
        await ensure_db()
        async with get_async_session_maker()() as session:
            service = PriorityService(session)
            levels = await service.get_all()

            table = Table(title="Priority Levels")
            table.add_column("Level", justify="center")
            table.add_column("Name", style="bold")
            table.add_column("Color")

            for p in levels:
                table.add_row(
                    str(p.level),
                    p.name,
                    p.color or "",
                )

            console.print(table)

    run_async(_priorities())


@app.command()
def server(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
):
    """Start the API server."""
    import uvicorn

    console.print(f"[green]Starting ToDoTracker server at http://{host}:{port}[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    uvicorn.run(
        "todotracker.main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    app()
