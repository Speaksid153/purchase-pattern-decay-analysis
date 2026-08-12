import { spawnSync } from 'node:child_process';

const configured = process.env.PYTHON?.trim();
const candidates = configured
  ? [configured]
  : process.platform === 'win32'
    ? ['py', 'python', 'python3']
    : ['python3', 'python'];

for (const executable of candidates) {
  const result = spawnSync(
    executable,
    ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py'],
    { stdio: 'inherit' },
  );
  if (!result.error) {
    process.exit(result.status ?? 1);
  }
  if (result.error.code !== 'ENOENT') {
    console.error(`Unable to start ${executable}: ${result.error.message}`);
    process.exit(1);
  }
}

console.error(`Unable to find Python. Tried: ${candidates.join(', ')}`);
process.exit(1);
