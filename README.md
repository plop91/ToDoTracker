# ToDoTracker

A task manager application designed as a Home Assistant add-on that lets you spend less time setting up and more time doing.

Built with FastAPI + SQLAlchemy + SQLite.

## Features

- **Quick Todo Entry** - Add todos with minimal friction
- **Priority Levels** - 10 customizable levels (Lowest to Urgent) with colors
- **Categories** - Organize todos into categories
- **Tags** - Flexible labeling with multiple tags per todo
- **Subtasks** - Break down tasks into smaller steps (full recursive support)
- **File Attachments** - Attach files to your todos
- **Due Dates** - Set deadlines with date and time
- **REST API** - Full API for Home Assistant automations
- **CLI Interface** - Command-line tool for local testing
- **Web UI** - Dark-themed interface for the browser
- **Home Assistant Add-on** - Ingress support for seamless HA integration

## Installation

### As a Python Package

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/todotracker.git
cd todotracker

# Install the package
pip install -e .

# Run the CLI
todo --help

# Start the API server
todo server
```

### As a Home Assistant Add-on

1. Add this repository to your Home Assistant add-on store
2. Install the ToDoTracker add-on
3. Start the add-on
4. Click "Open Web UI" in the sidebar

## CLI Usage

```bash
# Add todos
todo add "Buy groceries"
todo add "Project deadline" --due "2025-01-15 17:00" --priority 8
todo add "Meeting notes" --category work --tags "urgent,important"

# List todos
todo list              # Show pending todos
todo list --all        # Include completed
todo list --today      # Due today
todo list --category work

# Complete a todo
todo done <id>

# Add subtasks
todo add "Write intro" --parent <parent-id>

# Manage categories and tags
todo categories
todo tags
todo priorities
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/todos` | GET | List todos (supports filtering) |
| `/api/todos` | POST | Create a new todo |
| `/api/todos/{id}` | GET | Get a specific todo |
| `/api/todos/{id}` | PUT | Update a todo |
| `/api/todos/{id}` | DELETE | Delete a todo |
| `/api/todos/{id}/complete` | POST | Mark todo as complete |
| `/api/todos/{id}/subtasks` | POST | Add a subtask |
| `/api/categories` | GET, POST | List/create categories |
| `/api/tags` | GET, POST | List/create tags |
| `/api/priorities` | GET | List priority levels |
| `/api/priorities/{level}` | PUT | Update priority name/color |
| `/api/todos/{id}/attachments` | POST | Upload attachment |
| `/api/attachments/{id}` | GET, DELETE | Download/delete attachment |

## Home Assistant Integration

### REST Sensor (Pending Todos Count)

```yaml
rest:
  - resource: http://localhost:8099/api/todos?completed=false
    scan_interval: 60
    sensor:
      - name: "Pending Todos"
        value_template: "{{ value_json.total }}"
```

### REST Commands

```yaml
rest_command:
  add_todo:
    url: http://localhost:8099/api/todos
    method: POST
    content_type: application/json
    payload: '{"title": "{{ title }}", "priority": {{ priority | default(5) }}}'

  complete_todo:
    url: "http://localhost:8099/api/todos/{{ todo_id }}/complete"
    method: POST
```

### Automation Example

```yaml
automation:
  - alias: "Morning reminder"
    trigger:
      - platform: time
        at: "08:00:00"
    action:
      - service: rest_command.add_todo
        data:
          title: "Check daily tasks"
          priority: 7
```

## Development

### Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with debug mode
TODOTRACKER_DEBUG=true todo server
```

### Project Structure

```
todotracker/
├── src/todotracker/
│   ├── api/           # FastAPI endpoints
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   ├── cli.py         # CLI interface
│   ├── config.py      # Configuration
│   ├── database.py    # Database setup
│   └── main.py        # FastAPI app
├── tests/             # Unit tests
├── frontend/          # Web UI
├── hassio/            # Home Assistant add-on
└── alembic/           # Database migrations
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TODOTRACKER_DEBUG` | `false` | Enable debug mode |
| `TODOTRACKER_DATA_DIR` | `data` | Data directory path |
| `TODOTRACKER_DATABASE_URL` | `sqlite+aiosqlite:///data/todotracker.db` | Database URL |
| `TODOTRACKER_API_HOST` | `0.0.0.0` | API host |
| `TODOTRACKER_API_PORT` | `8000` | API port |
| `TODOTRACKER_FRONTEND_DIR` | None | Frontend static files directory |

## License

MIT License
