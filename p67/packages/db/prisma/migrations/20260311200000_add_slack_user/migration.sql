-- CreateTable
CREATE TABLE "SlackUser" (
    "id" TEXT NOT NULL,
    "slackUserId" TEXT NOT NULL,
    "slackTeamId" TEXT NOT NULL,
    "slackUsername" TEXT,
    "userId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "SlackUser_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "SlackUser_slackUserId_slackTeamId_key" ON "SlackUser"("slackUserId", "slackTeamId");

-- CreateIndex
CREATE INDEX "SlackUser_userId_idx" ON "SlackUser"("userId");

-- AddForeignKey
ALTER TABLE "SlackUser" ADD CONSTRAINT "SlackUser_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;
