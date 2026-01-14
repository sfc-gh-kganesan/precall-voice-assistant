CREATE OR REPLACE PROCEDURE <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.KB_EXPLORE()
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS CALLER
COMMENT = 'Discover available filter values and statistics from the Cortex Search Service.'
AS
$$
DECLARE
    v_total_chunks     NUMBER;
    v_article_count    NUMBER;
    v_knowledge_bases  VARIANT;
    v_proc_versions    VARIANT;
    result             VARIANT;
BEGIN
    SELECT COUNT(*)
    INTO :v_total_chunks
    FROM TABLE(CORTEX_SEARCH_DATA_SCAN(SERVICE_NAME => '<% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.KB_SEARCH'));

    SELECT COUNT(DISTINCT KB_SYS_ID)
    INTO :v_article_count
    FROM TABLE(CORTEX_SEARCH_DATA_SCAN(SERVICE_NAME => '<% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.KB_SEARCH'));

    SELECT ARRAY_AGG(DISTINCT KNOWLEDGE_BASE)::VARIANT
    INTO :v_knowledge_bases
    FROM TABLE(CORTEX_SEARCH_DATA_SCAN(SERVICE_NAME => '<% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.KB_SEARCH'))
    WHERE KNOWLEDGE_BASE IS NOT NULL;

    SELECT ARRAY_AGG(DISTINCT PROCESSING_VERSION)::VARIANT
    INTO :v_proc_versions
    FROM TABLE(CORTEX_SEARCH_DATA_SCAN(SERVICE_NAME => '<% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.KB_SEARCH'))
    WHERE PROCESSING_VERSION IS NOT NULL;

    result := OBJECT_CONSTRUCT(
        'total_chunks', v_total_chunks,
        'article_count', v_article_count,
        'knowledge_bases', v_knowledge_bases,
        'processing_versions', v_proc_versions
    );

    RETURN result;
END;
$$;
