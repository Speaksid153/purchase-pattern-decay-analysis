import { spawnSync } from 'node:child_process';

const executable = process.platform === 'win32' ? 'py' : 'python3';
const result = spawnSync(
  executable,
  ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py'],
  { stdio: 'inherit' },
);

if (result.error) {
  console.error(`Unable to start ${executable}: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
