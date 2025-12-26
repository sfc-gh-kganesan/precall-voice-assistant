import type { GlobalOptions } from '@p67-cli/global-options';
import type { ConnectionOptions } from '@p67-cli/middleware/connection';

export type WorkflowOptions = GlobalOptions & ConnectionOptions;
