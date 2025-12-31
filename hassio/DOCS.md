# ToDoTracker

A task manager for Home Assistant that lets you spend less time setting up and more time doing.

## Features

- **Quick Todo Entry** - Add todos with minimal friction
- **Priority Levels** - 10 customizable priority levels (Lowest to Urgent)
- **Categories** - Organize todos into categories with colors
- **Tags** - Flexible labeling with multiple tags per todo
- **Subtasks** - Break down large tasks into smaller steps
- **Due Dates** - Set deadlines with date and time
- **File Attachments** - Attach files to your todos
- **REST API** - Full API for Home Assistant automations

## Installation

1. Add this repository to your Home Assistant add-on store
2. Install the ToDoTracker add-on
3. Start the add-on
4. Click "Open Web UI" in the sidebar

## Configuration

### Option: `log_level`

The log level for the application. Valid options are:
- `debug` - Detailed debugging information
- `info` - General operational information (default)
- `warning` - Warning messages only
- `error` - Error messages only

## Home Assistant Integration

ToDoTracker exposes a REST API that you can use with Home Assistant's REST integration.

### Example: Pending Todos Sensor

```yaml
rest:
  - resource: http://localhost:8099/api/todos?completed=false
    scan_interval: 60
    sensor:
      - name: "Pending Todos"
        value_template: "{{ value_json.total }}"
```

### Example: Add Todo via Automation

```yaml
rest_command:
  add_todo:
    url: http://localhost:8099/api/todos
    method: POST
    content_type: application/json
    payload: '{"title": "{{ title }}", "priority": {{ priority | default(5) }}}'
```

Usage in automation:

```yaml
automation:
  - alias: "Add reminder todo"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: rest_command.add_todo
        data:
          title: "Daily standup meeting"
          priority: 7
```

### Example: Complete a Todo

```yaml
rest_command:
  complete_todo:
    url: "http://localhost:8099/api/todos/{{ todo_id }}/complete"
    method: POST
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
| `/api/categories` | GET | List categories |
| `/api/categories` | POST | Create a category |
| `/api/tags` | GET | List tags |
| `/api/tags` | POST | Create a tag |
| `/api/priorities` | GET | List priority levels |

## Support

For issues and feature requests, please visit the GitHub repository.
