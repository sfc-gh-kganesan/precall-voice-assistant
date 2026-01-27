-- CreateEnum
CREATE TYPE "SecretType" AS ENUM ('Secret', 'OAuth');

-- AlterTable
ALTER TABLE "Secret" ADD COLUMN     "type" "SecretType" NOT NULL DEFAULT 'Secret';
