-- Network rules for external access

-- CDN for Swagger UI
CREATE OR REPLACE NETWORK RULE ${DATABASE}.${SCHEMA}.cdn_jsdelivr_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('cdn.jsdelivr.net:443');

-- OpenAI (if using directly instead of Cortex)
CREATE OR REPLACE NETWORK RULE ${DATABASE}.${SCHEMA}.openai_network_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('api.openai.com:443');

-- LangSmith (optional)
CREATE OR REPLACE NETWORK RULE ${DATABASE}.${SCHEMA}.langsmith_network_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('api.smith.langchain.com:443');

-- External access integration
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION ${EXTERNAL_ACCESS_INTEGRATION}
  ALLOWED_NETWORK_RULES = (${DATABASE}.${SCHEMA}.cdn_jsdelivr_rule, ${DATABASE}.${SCHEMA}.openai_network_rule, ${DATABASE}.${SCHEMA}.langsmith_network_rule)
  ENABLED = true;

