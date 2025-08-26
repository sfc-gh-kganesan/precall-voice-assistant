# This gets the one-time password for your Snowflake FDE user from 1password.
OPT := $(shell op read "op://Employee/Snowflake - FDE account/one-time password?attribute=otp")

init:
	snow sql -c fde --mfa-passcode $(OPT)

init2:
	op run --no-masking --env-file="./.env" -- $(MAKE) foo

foo:
	echo $(SNOW_FDE_USER)
