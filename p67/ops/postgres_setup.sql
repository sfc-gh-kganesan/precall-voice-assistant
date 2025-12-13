-- Create network rule that only allows ingress to postgres from the dev vpn
create or replace network rule pg_network_database.pg_network_schema.dev_vpn_ingress
    type = ipv4
    mode = postgres_ingress
    value_list = ('34.214.158.144/32')
    comment = 'allow ingress only from corporate dev vpn';

-- Create network policy that uses the ingress rule
create or replace network policy dev_vpn_ingress
    allowed_network_rule_list = (pg_network_database.pg_network_schema.dev_vpn_ingress);

-- Create postgres service
create postgres service if not exists p67
  compute_family = 'standard_m'
  storage_size_gb = 10
  authentication_authority = postgres
  postgres_version = 17
  high_availability = false
  comment = 'project 67 control plane db'
  network_policy = dev_vpn_ingress;

