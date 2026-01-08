# Simple Todo App

![Accessibility CI](https://github.com/Hanibalus/ToDoExample/actions/workflows/accessibility.yml/badge.svg)

Minimal todo app using plain HTML, CSS, and JavaScript. Todos are persisted in the browser `localStorage`.

How to open

- Open `index.html` in your browser (double-click or use a local server).

Usage

- Type a todo in the input and press `Add` or Enter.
- Each todo has a `Delete` button to remove it.
- Press `Ctrl+K` (or `Cmd+K` on macOS) to focus the input.
 - Click the checkbox area left of a todo to mark it completed (strikethrough). The completed state is saved.

Files

- index.html — main page
- styles.css — styles
- app.js — todo logic and persistence

Run accessibility workflow manually

- Go to the repository on GitHub and open the `Actions` tab.
- Find the workflow named "Accessibility (Playwright + axe)" in the list (or search for `accessibility.yml`).
- Click the workflow, then click the "Run workflow" dropdown on the right and choose the branch (usually `master`).
- Click the green "Run workflow" button to start the job. The workflow will run and upload artifacts (screenshot + axe report) when complete.

Note: This workflow is configured as manual-only (`workflow_dispatch`) and will not run automatically on PRs or on a schedule.
