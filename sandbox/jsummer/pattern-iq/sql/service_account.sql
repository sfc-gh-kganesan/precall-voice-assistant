-- Team CI service account for GitHub Actions + Snowflake workflows.
-- Run once by an ACCOUNTADMIN.
--
-- Setup:
--   1. Generate a key pair:
--        openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out aifde_ci.p8 -nocrypt
--        openssl rsa -in aifde_ci.p8 -pubout -out aifde_ci.pub
--   2. Replace <PUBLIC_KEY> below with the contents of aifde_ci.pub
--      (exclude the -----BEGIN PUBLIC KEY----- and -----END PUBLIC KEY----- lines).
--   3. Store the private key (aifde_ci.p8) in 1Password for distribution to repo owners.
--   4. Delete both key files from your local machine.
--
-- Per-project setup:
--   Grant project-specific roles to this user in each project's setup.sql.
--   Example: GRANT ROLE MY_PROJECT TO USER AIFDE_CI_SVC;

CREATE USER IF NOT EXISTS AIFDE_CI_SVC
    TYPE = SERVICE
    DEFAULT_ROLE = PUBLIC
    DEFAULT_WAREHOUSE = COMPUTE_WH
    RSA_PUBLIC_KEY = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAw2n3ADX5wfzOsIcOgCft
IwEAWUxcT2cvDANlPfd+F9Cqn/dt/pY4yoRa7d0ZcwoLo7CtTrsPeEguOs0BN0TR
cmlYzv6lQ1YvPXkQ/zh5q8vg8XtMrsj5AiSk7Am2BtDUYsU4CswSu4VpVY1EM8qD
tJm5alJk+/Hc++cF2/R1JcWIQcno1pfhsMIetddsyBU92XPqG2FZd/o9bu6J3zyR
tw6X6CM8PTK00auCxWRR+YftWqsBHW4hXpv3BKs6hlj15Ti2ImolACMelB/vDxAv
qsJMsw8RqvJoh26ohOhUzi3IENg+whADr/Pbb8YvrtyZpoFw/JdUewo4M3ooCPei
8QIDAQAB';

