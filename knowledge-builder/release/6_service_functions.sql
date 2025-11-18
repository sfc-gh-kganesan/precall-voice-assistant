create or replace function <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.KNOWLEDGE_SEARCH_UDF(
    QUESTION        string,      -- user query
    USERNAME        string,      -- caller’s username or email
    USER_ROLE       string,      -- role/group (e.g., "IT_AGENT", "EMPLOYEE")
    REGION          string,      -- region code (e.g., "CA", "FR", "US")
    LOCALE          string,      -- locale (e.g., "en-US", "fr-FR")
    MAX_RESULTS     integer,     -- desired number of hits (default in caller)
    SCORING_PROFILE string       -- routing/scoring key (e.g., "SELF_HELP", "TECH")
)
returns variant
language sql
as
$$
object_construct(
  'query', QUESTION,
  'context', object_construct(
    'username', USERNAME,
    'user_role', USER_ROLE,
    'region', REGION,
    'locale', LOCALE,
    'max_results', MAX_RESULTS,
    'scoring_profile', SCORING_PROFILE
  ),
  'results', array_construct(
    object_construct(
      'id', 'KNG-61',
      'title', 'SA SSF AVD – Azure Virtual Desktop (WaaS AVD)',
      'score', 0.89,
      'knowledgebase', 'Self Help',
      'category', 'SSF',
      'url', 'https://sanofi-dev.eu.elementum.io/kb/KNG-61',
      'snippet', 'Article excerpt about AVD setup and troubleshooting.'
    ),
    object_construct(
      'id', 'KNG-27',
      'title', 'Mobile: Configure Apps on Personal Mobile (Personally Owned)',
      'score', 0.83,
      'knowledgebase', 'Self Help',
      'category', 'Mobile',
      'url', 'https://sanofi-dev.eu.elementum.io/kb/KNG-27',
      'snippet', 'Steps to configure mobile apps.'
    ),
    object_construct(
      'id', 'KNG-56',
      'title', 'SSF Zoom',
      'score', 0.80,
      'knowledgebase', 'GUEST',
      'category', 'SSF',
      'url', 'https://sanofi-dev.eu.elementum.io/kb/KNG-56',
      'snippet', 'Zoom setup and common fixes.'
    )
  )
)::variant
$$;


-- SELECT KNOWLEDGE_BUILDER.CORE.KNOWLEDGE_SEARCH_UDF(
--     'How do I set up Azure Virtual Desktop?',  
--     'john.doe@example.com',                    
--     'IT_AGENT',                                
--     'US',                                      
--     'en-US',                                   
--     5,                                         
--     'SELF_HELP'                                
-- );