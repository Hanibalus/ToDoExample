(() => {
  const form = document.getElementById('todo-form');
  const input = document.getElementById('todo-input');
  const list = document.getElementById('todo-list');
  const STORAGE_KEY = 'simple_todos_v1';

  function readTodos(){
    try{
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    }catch(e){
      console.error('Failed to read todos', e);
      return [];
    }
  }

  function writeTodos(todos){
    try{
      localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
    }catch(e){
      console.error('Failed to write todos', e);
    }
  }

  function createTodoElement(todo){
    const li = document.createElement('li');
    li.className = 'todo-item';
    li.dataset.id = todo.id;

    const left = document.createElement('div');
    left.style.display = 'flex';
    left.style.alignItems = 'center';

    const checkbox = document.createElement('button');
    checkbox.className = 'todo-checkbox';
    checkbox.type = 'button';
    checkbox.setAttribute('aria-pressed', todo.completed ? 'true' : 'false');
    if(todo.completed){
      checkbox.classList.add('checked');
    }
    checkbox.addEventListener('click', () => toggleCompleted(todo.id));

    const span = document.createElement('span');
    span.className = 'todo-text';
    span.textContent = todo.text;
    if(todo.completed) span.classList.add('completed');

    left.appendChild(checkbox);
    left.appendChild(span);

    const actions = document.createElement('div');
    actions.className = 'todo-actions';

    const del = document.createElement('button');
    del.className = 'btn-delete';
    del.type = 'button';
    del.textContent = 'Delete';
    del.addEventListener('click', () => removeTodo(todo.id));

    actions.appendChild(del);
    li.appendChild(left);
    li.appendChild(actions);
    return li;
  }

  function render(){
    const todos = readTodos();
    list.innerHTML = '';
    if(todos.length === 0){
      const p = document.createElement('p');
      p.className = 'muted';
      p.textContent = 'No todos yet — add one above.';
      list.appendChild(p);
      return;
    }

    const frag = document.createDocumentFragment();
    todos.forEach(t => frag.appendChild(createTodoElement(t)));
    list.appendChild(frag);
  }

  function addTodo(text){
    const todos = readTodos();
    const todo = { id: Date.now().toString(36) + Math.random().toString(36).slice(2,5), text: text.trim(), completed: false };
    todos.unshift(todo);
    writeTodos(todos);
    render();
  }

  function toggleCompleted(id){
    const todos = readTodos();
    const idx = todos.findIndex(t => t.id === id);
    if(idx === -1) return;
    todos[idx].completed = !todos[idx].completed;
    writeTodos(todos);
    render();
  }

  function removeTodo(id){
    let todos = readTodos();
    todos = todos.filter(t => t.id !== id);
    writeTodos(todos);
    render();
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const value = input.value.trim();
    if(!value) return;
    addTodo(value);
    input.value = '';
    input.focus();
  });

  // keyboard shortcut: Ctrl+K focuses input
  window.addEventListener('keydown', (e) => {
    if((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k'){
      e.preventDefault();
      input.focus();
    }
  });

  // initial render
  render();

})();
