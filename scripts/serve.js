const http = require('http');
const fs = require('fs');
const path = require('path');

const port = process.argv[2] ? parseInt(process.argv[2], 10) : 5000;
const root = process.cwd();

const mime = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.json': 'application/json',
  '.ico': 'image/x-icon'
};

http.createServer((req, res) => {
  let filePath = path.join(root, req.url.split('?')[0]);
  if (fs.existsSync(filePath) && fs.statSync(filePath).isDirectory()) {
    filePath = path.join(filePath, 'index.html');
  }
  if (!fs.existsSync(filePath)) {
    res.statusCode = 404;
    res.end('Not found');
    return;
  }
  const ext = path.extname(filePath).toLowerCase();
  const type = mime[ext] || 'application/octet-stream';
  res.writeHead(200, { 'Content-Type': type });
  const stream = fs.createReadStream(filePath);
  stream.pipe(res);
}).listen(port, () => console.log(`Static server running at http://localhost:${port}`));
