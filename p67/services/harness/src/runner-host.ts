import { ExecuteMessage, ExecuteMessageSchema } from './schema.js';
import * as path from 'path';
import * as fs from 'fs';

function error(err: Error | string) {
  process.send!({
    type: 'error',
    error: err instanceof Error ? err.message : String(error),
  });
}

process.on('message', async (message: ExecuteMessage) => {
  const m = ExecuteMessageSchema.safeParse(message);
  if (!m.success) {
    error(m.error);
    process.exit(1);
  }

  try {
    // Dynamically import the script
    const scriptPath = path.resolve(m.data.dir, 'index.js');
    if (!fs.existsSync(scriptPath)) {
      throw new Error(`${scriptPath} does not exist, exiting.`);
    }

    console.log(`loading script ${scriptPath}`);
    const script = await import(scriptPath);
    console.log(`Loaded script!`);

    // Check if main function exists
    if (typeof script.main !== 'function') {
      throw new Error('Script does not export a main function');
    }

    // Execute the main function with the provided data
    const result = await script.main();

    // Send the result back to parent
    process.send!({ type: 'result', data: result });
  } catch (error) {
    // Send error back to parent
    process.send!({
      type: 'error',
      error: error instanceof Error ? error.message : String(error),
    });
    process.exit(1);
  }

  process.exit(0);
});
