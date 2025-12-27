-- Drop postgres service
drop postgres service p67;
-- Drop network policy
drop network policy p67_postgres_ingress;
-- Drop network rule
drop network rule pg_network_database.pg_network_schema.dev_vpn_ingress;
drop network rule pg_network_database.pg_network_schema.allow_all;
