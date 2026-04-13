const path = require('path');

module.exports = {
  apps: [
    {
      name: 'tg-downloader',
      script: 'server.py',
      interpreter: path.join(__dirname, '.venv', 'bin', 'python3'),
      cwd: path.join(__dirname, 'web'),
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: path.join(__dirname)
      },
    }
  ],
};
