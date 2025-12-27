create network rule if not exists pg_network_database.pg_network_schema.dev_vpn_ingress
    type = ipv4
    mode = postgres_ingress
    value_list = ('34.214.158.144/32')
    comment = 'allow ingress only from corporate dev vpn';

create network rule if not exists pg_network_database.pg_network_schema.allow_all
    type = ipv4
    mode = postgres_ingress
    value_list = ('0.0.0.0/0')
    comment = 'allow ingress from all ip addresses';

create network policy if not exists p67_postgres_ingress
    allowed_network_rule_list = (
        pg_network_database.pg_network_schema.dev_vpn_ingress,
        snowflake.network_security.githubactions_global
    );

-- Note(2025-12-27): The githubactions_global network rule does not appear to work, so to unblock github action usage,
-- we are temporarily changing the policy to allow ingress from all ip addresses.
alter network policy p67_postgres_ingress set allowed_network_rule_list = (pg_network_database.pg_network_schema.allow_all);

-- Create postgres service
create postgres service if not exists p67
  compute_family = 'standard_m'
  storage_size_gb = 10
  authentication_authority = postgres
  postgres_version = 17
  high_availability = false
  comment = 'project 67 control plane db'
  network_policy = p67_postgres_ingress;

