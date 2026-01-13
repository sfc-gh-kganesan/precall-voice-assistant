-- DropIndex
DROP INDEX "User_id_key";

-- AlterTable
ALTER TABLE "Workflow" ADD CONSTRAINT "Workflow_pkey" PRIMARY KEY ("id");

-- DropIndex
DROP INDEX "Workflow_id_key";
