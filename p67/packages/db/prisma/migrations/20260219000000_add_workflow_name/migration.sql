-- AlterTable
ALTER TABLE "Workflow" ADD COLUMN "name" TEXT;

-- CreateIndex
CREATE INDEX "Workflow_name_ownerId_createdAt_idx" ON "Workflow"("name", "ownerId", "createdAt" DESC);
