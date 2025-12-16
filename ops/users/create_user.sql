CREATE USER IF NOT EXISTS <% login_name %>
  LOGIN_NAME = '<% login_name %>'
  DISPLAY_NAME = '<% display_name %>'
  FIRST_NAME = '<% first_name %>'
  LAST_NAME = '<% last_name %>'
  EMAIL = '<% email %>'
  PASSWORD = '<% password %>'
  MUST_CHANGE_PASSWORD = <% must_change_password %>
  DEFAULT_WAREHOUSE = <% default_warehouse %>
  DEFAULT_ROLE = <% default_role %>;

GRANT ROLE SIADMIN TO USER <% login_name %>;
GRANT ROLE P67_USER_RL TO USER <% login_name %>;
