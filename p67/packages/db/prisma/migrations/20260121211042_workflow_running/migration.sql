-- CreateEnum
CREATE TYPE "WorkflowRunStatus" AS ENUM ('Running', 'Completed', 'Failed', 'Cancelled');

-- AlterTable
ALTER TABLE "WorkflowRun" ADD COLUMN     "status" "WorkflowRunStatus" NOT NULL DEFAULT 'Running';

-- CreateIndex
CREATE INDEX "WorkflowRun_status_idx" ON "WorkflowRun"("status");
