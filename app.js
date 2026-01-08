(() => {
  const form = document.getElementById('todo-form');
  const input = document.getElementById('todo-input');
  const list = document.getElementById('todo-list');
  const STORAGE_KEY = 'simple_todos_v1';
  const FILTER_KEY = 'todos_filter_v1';
  const SEARCH_KEY = 'todos_search_v1';
  const SORT_KEY = 'todos_sort_v1';

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

  // toolbar elements (may be absent in older versions)
  const searchInput = document.getElementById('todo-search');
  const sortSelect = document.getElementById('todo-sort');
  const filterButtons = Array.from(document.querySelectorAll('.filter-btn'));

  function getToolbarState(){
    try{
      return {
        filter: localStorage.getItem(FILTER_KEY) || 'all',
        search: localStorage.getItem(SEARCH_KEY) || '',
        sort: localStorage.getItem(SORT_KEY) || 'newest'
      };
    }catch(e){
      return { filter: 'all', search: '', sort: 'newest' };
    }
  }

  function setToolbarState(state){
    try{
      if(state.filter !== undefined) localStorage.setItem(FILTER_KEY, state.filter);
      if(state.search !== undefined) localStorage.setItem(SEARCH_KEY, state.search);
      if(state.sort !== undefined) localStorage.setItem(SORT_KEY, state.sort);
    }catch(e){}
  }

  function initToolbar(){
    const s = getToolbarState();
    // initialize filter buttons
    filterButtons.forEach(btn => {
      const f = btn.getAttribute('data-filter');
      btn.setAttribute('aria-pressed', f === s.filter ? 'true' : 'false');
      btn.addEventListener('click', () => {
        setToolbarState({ filter: f });
        // update aria-pressed
        filterButtons.forEach(b => b.setAttribute('aria-pressed', b.getAttribute('data-filter') === f ? 'true' : 'false'));
        render();
      });
    });

    if(searchInput){
      searchInput.value = s.search || '';
      searchInput.addEventListener('input', () => {
        setToolbarState({ search: searchInput.value });
        render();
      });
    }

    if(sortSelect){
      sortSelect.value = s.sort || 'newest';
      sortSelect.addEventListener('change', () => {
        setToolbarState({ sort: sortSelect.value });
        render();
      });
    }
  }

  function createTodoElement(todo){
    const li = document.createElement('li');
    li.className = 'todo-item';
    li.dataset.id = todo.id;
    li.classList.add('enter');

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
    checkbox.setAttribute('aria-label', todo.completed ? 'Mark as not completed' : 'Mark as completed');

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
    let todos = readTodos();
    // apply filter/search/sort from toolbar state
    const s = getToolbarState();

    // filter
    if(s.filter === 'active') todos = todos.filter(t => !t.completed);
    else if(s.filter === 'completed') todos = todos.filter(t => t.completed);

    // search (case-insensitive substring)
    if(s.search && s.search.trim() !== ''){
      const q = s.search.trim().toLowerCase();
      todos = todos.filter(t => t.text.toLowerCase().includes(q));
    }

    // sort
    if(s.sort === 'oldest'){
      todos = todos.slice().reverse();
    }else if(s.sort === 'alpha'){
      todos = todos.slice().sort((a,b) => a.text.localeCompare(b.text));
    } // newest is the default (current storage order)

    list.innerHTML = '';
    if(todos.length === 0){
      const p = document.createElement('p');
      p.className = 'muted';
      p.textContent = 'No todos yet — add one above.';
      list.appendChild(p);
      return;
    }

    const frag = document.createDocumentFragment();
    todos.forEach((t, i) => {
      const el = createTodoElement(t);
      // small stagger for entrance
      el.style.animationDelay = (Math.min(6, i) * 30) + 'ms';
      frag.appendChild(el);
    });
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

  // Undo/delete buffer
  let undoTimer = null;
  let buffered = null;

  function removeTodo(id){
    const todos = readTodos();
    const idx = todos.findIndex(t => t.id === id);
    if(idx === -1) return;

    const [item] = todos.splice(idx, 1);
    writeTodos(todos);
    render();

    // buffer the removed item and show undo snackbar
    buffered = { item, index: idx };
    showSnackbar();
  }

  function showSnackbar(){
    const sb = document.getElementById('undo-snackbar');
    if(!sb) return;
    const action = sb.querySelector('.snackbar-action');
    const close = sb.querySelector('.snackbar-close');

    // set message
    const msg = sb.querySelector('.snackbar-message');
    msg.textContent = 'Todo deleted';

    action.onclick = () => {
      undoDelete();
      action.focus();
    };

    close.onclick = () => {
      clearSnackbar();
    };

    sb.classList.add('show');
    sb.setAttribute('aria-hidden', 'false');

    // auto-dismiss after 6s
    if(undoTimer) clearTimeout(undoTimer);
    undoTimer = setTimeout(() => {
      clearSnackbar();
      buffered = null;
    }, 6000);
  }

  function clearSnackbar(){
    const sb = document.getElementById('undo-snackbar');
    if(!sb) return;
    sb.classList.remove('show');
    sb.setAttribute('aria-hidden', 'true');
    if(undoTimer) { clearTimeout(undoTimer); undoTimer = null; }
  }

  function undoDelete(){
    if(!buffered) return;
    const todos = readTodos();
    // restore at the original index
    todos.splice(buffered.index, 0, buffered.item);
    writeTodos(todos);
    render();
    clearSnackbar();
    buffered = null;
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

  // theme toggle + persistence
  const THEME_KEY = 'theme_pref_v1';
  const themeToggle = document.getElementById('theme-toggle');
  function setTheme(theme){
    const t = theme === 'dark' ? 'dark' : 'light';
    if(t === 'dark') document.documentElement.classList.add('dark'); else document.documentElement.classList.remove('dark');
    try{ localStorage.setItem(THEME_KEY, t); }catch(e){}
    if(themeToggle){
      themeToggle.setAttribute('aria-pressed', t === 'dark' ? 'true' : 'false');
      themeToggle.textContent = t === 'dark' ? '☀️' : '🌙';
    }
  }
  // initialize theme from storage or system preference
  try{
    const stored = localStorage.getItem(THEME_KEY);
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    setTheme(stored || (prefersDark ? 'dark' : 'light'));
  }catch(e){ setTheme('light'); }
  if(themeToggle){
    themeToggle.addEventListener('click', () => setTheme(document.documentElement.classList.contains('dark') ? 'light' : 'dark'));
  }

  // initialize toolbar and render
  initToolbar();
  render();

})();
