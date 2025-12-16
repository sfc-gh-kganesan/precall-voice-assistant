create or replace procedure v1.configure_reference(ref_name string)
returns string
language sql
as
$$
begin
    case (upper(ref_name))
        when 'GOOGLE_OAUTH_EAI' then
            return '{
                "type": "CONFIGURATION",
                "payload": {
                    "host_ports": [
                        "oauth2.googleapis.com",
                        "accounts.google.com",
                        "www.googleapis.com"
                    ],
                    "allowed_secrets": "NONE"
                }
            }';
        when 'GOOGLE_OAUTH_CLIENT_ID' then
            return '{
                "type": "CONFIGURATION",
                "payload":{
                    "type": "GENERIC_STRING"
                }
            }';
        when 'GOOGLE_OAUTH_CLIENT_SECRET' then
            return '{
                "type": "CONFIGURATION",
                "payload": {
                    "type": "GENERIC_STRING"
                }
            }';
        when 'POSTGRES_EAI' then
            return '{
                "type": "CONFIGURATION",
                "payload": {
                    "host_ports": [
                        "xe5sle7s5bc3jovhaefnmrc5qq.sfengineering-aifde.us-west-2.aws.postgres.snowflake.app:5432"
                    ],
                    "allowed_secrets": "NONE"
                }
            }';
        when 'POSTGRES_CONNECTION_URL' then
            return '{
                "type": "CONFIGURATION",
                "payload": {
                    "type": "GENERIC_STRING"
                }
            }';
        else
            return '';
    end case;
end;
$$;

grant usage on procedure v1.configure_reference(string) to application role app_admin;

