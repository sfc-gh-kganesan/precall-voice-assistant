-- Network rules for external access

-- CDN for Swagger UI
CREATE OR REPLACE NETWORK RULE cdn_jsdelivr_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('cdn.jsdelivr.net:443');

-- OpenAI (if using directly instead of Cortex)
CREATE OR REPLACE NETWORK RULE openai_network_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('api.openai.com:443');

-- LangSmith (optional)
CREATE OR REPLACE NETWORK RULE langsmith_network_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('api.smith.langchain.com:443');

-- External access integration
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION sales_ai_external_access
  ALLOWED_NETWORK_RULES = (cdn_jsdelivr_rule, openai_network_rule, langsmith_network_rule)
  ENABLED = true;

