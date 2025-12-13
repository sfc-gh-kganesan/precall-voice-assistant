-- Drop postgres service
drop postgres service p67;
-- Drop network policy
drop network policy dev_vpn_ingress;
-- Drop network rule
drop network rule pg_network_database.pg_network_schema.dev_vpn_ingress;
