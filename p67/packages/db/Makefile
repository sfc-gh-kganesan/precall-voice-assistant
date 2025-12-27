.PHONY: sql diff deploy

.env:
	cp .env.example .env

sql:
	pnpm prisma migrate diff --from-empty --to-schema prisma/schema.prisma --script

diff:
	pnpm prisma migrate diff --from-config-datasource --to-schema prisma/schema.prisma --script

deploy:
	pnpm prisma migrate deploy
