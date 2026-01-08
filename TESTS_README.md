This project includes a simple Playwright + axe-core test for basic accessibility and a screenshot.

Prerequisites:
- Node.js installed

Install dev dependencies:

```bash
npm install
```

Run the test locally (serving the project on port 5000):

```bash
# serve the current folder (one simple option)
npx http-server -p 5000 -c-1

# in another terminal, run the playwright test
npm run test:accessibility
```

The test will run an accessibility scan using axe and save `tests/todo-screenshot.png` for visual review.
