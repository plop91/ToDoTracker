// ToDoTracker Frontend Application

const API_BASE = '/api';

// State
let todos = [];
let categories = [];
let currentFilter = 'pending';

// API Functions
async function fetchTodos(completed = null) {
    const params = new URLSearchParams();
    if (completed !== null) {
        params.append('completed', completed);
    }
    const response = await fetch(`${API_BASE}/todos?${params}`);
    const data = await response.json();
    return data.items || [];
}

async function fetchCategories() {
    const response = await fetch(`${API_BASE}/categories`);
    return await response.json();
}

async function createTodo(todo) {
    const response = await fetch(`${API_BASE}/todos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(todo)
    });
    return await response.json();
}

async function completeTodo(id) {
    const response = await fetch(`${API_BASE}/todos/${id}/complete`, {
        method: 'POST'
    });
    return await response.json();
}

async function updateTodo(id, updates) {
    const response = await fetch(`${API_BASE}/todos/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
    });
    return await response.json();
}

async function deleteTodo(id) {
    await fetch(`${API_BASE}/todos/${id}`, {
        method: 'DELETE'
    });
}

async function createCategory(category) {
    const response = await fetch(`${API_BASE}/categories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(category)
    });
    return await response.json();
}

// UI Functions
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);

    if (date.toDateString() === now.toDateString()) {
        return `Today ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } else if (date.toDateString() === tomorrow.toDateString()) {
        return `Tomorrow ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function getPriorityLabel(priority) {
    const labels = {
        1: 'Lowest', 2: 'Very Low', 3: 'Low', 4: 'Below Normal', 5: 'Normal',
        6: 'Above Normal', 7: 'High', 8: 'Very High', 9: 'Critical', 10: 'Urgent'
    };
    return labels[priority] || 'Normal';
}

function renderTodoItem(todo) {
    const subtasksHtml = todo.subtasks && todo.subtasks.length > 0 ? `
        <div class="subtasks">
            ${todo.subtasks.map(sub => `
                <div class="subtask-item ${sub.completed ? 'completed' : ''}">
                    <div class="todo-checkbox ${sub.completed ? 'checked' : ''}"
                         onclick="toggleTodo('${sub.id}', ${!sub.completed})"></div>
                    <span class="${sub.completed ? 'todo-title' : ''}">${escapeHtml(sub.title)}</span>
                </div>
            `).join('')}
        </div>
    ` : '';

    return `
        <div class="todo-item priority-${todo.priority} ${todo.completed ? 'completed' : ''}" data-id="${todo.id}">
            <div class="todo-checkbox ${todo.completed ? 'checked' : ''}"
                 onclick="toggleTodo('${todo.id}', ${!todo.completed})"></div>
            <div class="todo-content">
                <div class="todo-title">${escapeHtml(todo.title)}</div>
                <div class="todo-meta">
                    <span>P${todo.priority} - ${getPriorityLabel(todo.priority)}</span>
                    ${todo.due_date ? `<span>${formatDate(todo.due_date)}</span>` : ''}
                    ${todo.category ? `<span class="category-badge" style="background: ${todo.category.color || '#3b82f6'}">${escapeHtml(todo.category.name)}</span>` : ''}
                    ${todo.tags && todo.tags.length > 0 ? `<span>${todo.tags.map(t => t.name).join(', ')}</span>` : ''}
                </div>
                ${subtasksHtml}
            </div>
            <div class="todo-actions">
                <button onclick="deleteTodoItem('${todo.id}')" class="delete">Delete</button>
            </div>
        </div>
    `;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderTodoList() {
    const container = document.getElementById('todoList');

    if (todos.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <h3>No todos yet</h3>
                <p>Add your first todo above to get started!</p>
            </div>
        `;
        return;
    }

    container.innerHTML = todos.map(renderTodoItem).join('');
}

function renderCategories() {
    const select = document.getElementById('todoCategory');
    select.innerHTML = '<option value="">No Category</option>' +
        categories.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('') +
        '<option value="__new__">+ Add Category</option>';
}

// Event Handlers
async function toggleTodo(id, completed) {
    try {
        if (completed) {
            await completeTodo(id);
        } else {
            await updateTodo(id, { completed: false });
        }
        await loadTodos();
    } catch (error) {
        console.error('Error toggling todo:', error);
    }
}

async function deleteTodoItem(id) {
    if (!confirm('Are you sure you want to delete this todo?')) return;
    try {
        await deleteTodo(id);
        await loadTodos();
    } catch (error) {
        console.error('Error deleting todo:', error);
    }
}

async function loadTodos() {
    try {
        let completed = null;
        if (currentFilter === 'pending') completed = false;
        if (currentFilter === 'completed') completed = true;

        todos = await fetchTodos(completed);
        renderTodoList();
    } catch (error) {
        console.error('Error loading todos:', error);
        document.getElementById('todoList').innerHTML = `
            <div class="empty-state">
                <h3>Error loading todos</h3>
                <p>Please try refreshing the page.</p>
            </div>
        `;
    }
}

async function loadCategories() {
    try {
        categories = await fetchCategories();
        renderCategories();
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

function closeCategoryModal() {
    document.getElementById('categoryModal').classList.add('hidden');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Load initial data
    loadTodos();
    loadCategories();

    // Add todo form
    document.getElementById('addTodoForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const title = document.getElementById('todoTitle').value.trim();
        if (!title) return;

        const priority = parseInt(document.getElementById('todoPriority').value);
        const categoryId = document.getElementById('todoCategory').value;
        const dueDate = document.getElementById('todoDueDate').value;

        const todo = {
            title,
            priority,
            category_id: categoryId && categoryId !== '__new__' ? categoryId : null,
            due_date: dueDate ? new Date(dueDate).toISOString() : null
        };

        try {
            await createTodo(todo);
            document.getElementById('todoTitle').value = '';
            document.getElementById('todoDueDate').value = '';
            await loadTodos();
        } catch (error) {
            console.error('Error creating todo:', error);
            alert('Failed to create todo. Please try again.');
        }
    });

    // Category select handler
    document.getElementById('todoCategory').addEventListener('change', (e) => {
        if (e.target.value === '__new__') {
            document.getElementById('categoryModal').classList.remove('hidden');
            e.target.value = '';
        }
    });

    // Add category form
    document.getElementById('addCategoryForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const name = document.getElementById('categoryName').value.trim();
        const color = document.getElementById('categoryColor').value;

        if (!name) return;

        try {
            await createCategory({ name, color });
            closeCategoryModal();
            document.getElementById('categoryName').value = '';
            await loadCategories();
        } catch (error) {
            console.error('Error creating category:', error);
            alert('Failed to create category. Please try again.');
        }
    });

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            loadTodos();
        });
    });
});

// Make functions available globally for onclick handlers
window.toggleTodo = toggleTodo;
window.deleteTodoItem = deleteTodoItem;
window.closeCategoryModal = closeCategoryModal;
