# Ops README

## Postgres

To create a fresh Snowflake managed postgres database for the P67 application, run the setup sql as follows:

```sh
snow sql -f postgres_setup.sql
```
This will create:
- A network policy with a rule that allows connections from the dev vpn
- A new postgres instance with the network policy applied

Please note: this command returns the `snowflake_admin` and `application` Postgres role credentials. Store these in a safe place (eg, 1Password). You will not be able to access them again.

To teardown all objects, run:

```sh
snow sql -f postgres_teardown.sql
```
