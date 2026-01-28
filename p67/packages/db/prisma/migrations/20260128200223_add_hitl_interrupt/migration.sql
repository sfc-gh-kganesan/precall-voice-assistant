-- CreateEnum
CREATE TYPE "InterruptStatus" AS ENUM ('Pending', 'Resumed', 'Expired');

-- AlterEnum
ALTER TYPE "WorkflowRunStatus" ADD VALUE 'Interrupted';

-- CreateTable
CREATE TABLE "WorkflowInterrupt" (
    "id" TEXT NOT NULL,
    "runId" TEXT NOT NULL,
    "workflowId" TEXT NOT NULL,
    "payload" JSONB NOT NULL,
    "nodeId" TEXT,
    "status" "InterruptStatus" NOT NULL DEFAULT 'Pending',
    "response" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "resumedAt" TIMESTAMP(3),

    CONSTRAINT "WorkflowInterrupt_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "WorkflowInterrupt_runId_idx" ON "WorkflowInterrupt"("runId");

-- CreateIndex
CREATE INDEX "WorkflowInterrupt_workflowId_idx" ON "WorkflowInterrupt"("workflowId");

-- CreateIndex
CREATE INDEX "WorkflowInterrupt_status_idx" ON "WorkflowInterrupt"("status");

-- AddForeignKey
ALTER TABLE "WorkflowInterrupt" ADD CONSTRAINT "WorkflowInterrupt_runId_fkey" FOREIGN KEY ("runId") REFERENCES "WorkflowRun"("id") ON DELETE CASCADE ON UPDATE CASCADE;
