CREATE OR REPLACE PROCEDURE {{ KB_DATABASE_NAME }}.{{ KB_SCHEMA_NAME }}.KB_SEARCH(REQUEST VARIANT)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS CALLER
COMMENT = 'Search the knowledge base using natural language queries via Cortex Search.'
AS
$$
DECLARE
    v_question         STRING;
    v_limit            NUMBER DEFAULT 10;
    v_kb_number        STRING;
    v_kb_sys_id        STRING;
    v_knowledge_base   STRING;
    v_can_read         STRING;
    v_cannot_read      STRING;
    v_exclude_articles BOOLEAN DEFAULT FALSE;
    qid                STRING;
    json_config        STRING DEFAULT '';
    json_config_escaped STRING DEFAULT '';
    search_results     VARIANT;
    articles           VARIANT;
    result             VARIANT;
BEGIN
    v_question := REQUEST:"question"::STRING;

    IF (v_question IS NULL OR v_question = '') THEN
        RETURN OBJECT_CONSTRUCT(
            'error', 'REQUEST must include a question field',
            'request', REQUEST
        )::VARIANT;
    END IF;

    v_limit := COALESCE(REQUEST:"limit"::NUMBER, 10);
    v_kb_number := REQUEST:"kb_number"::STRING;
    v_kb_sys_id := REQUEST:"kb_sys_id"::STRING;
    v_knowledge_base := REQUEST:"knowledge_base"::STRING;
    v_can_read := REQUEST:"can_read_user_criteria"::STRING;
    v_cannot_read := REQUEST:"cannot_read_user_criteria"::STRING;
    v_exclude_articles := COALESCE(REQUEST:"exclude_articles"::BOOLEAN, FALSE);

    json_config := '{' ||
        '"query": "' || REPLACE(:v_question, '"', '\\"') || '",' ||
        '"columns": ["KB_SYS_ID","KB_NUMBER","CHUNK_INDEX","CHUNK_TEXT"],' ||
        '"limit": ' || TO_VARCHAR(:v_limit);

    IF (v_kb_number IS NOT NULL OR v_kb_sys_id IS NOT NULL OR v_knowledge_base IS NOT NULL
        OR v_can_read IS NOT NULL OR v_cannot_read IS NOT NULL) THEN
        json_config := json_config || ',"filter": {';

        LET filter_parts ARRAY := ARRAY_CONSTRUCT();

        IF (v_kb_number IS NOT NULL) THEN
            filter_parts := ARRAY_APPEND(filter_parts, '"@eq": {"KB_NUMBER": "' || REPLACE(:v_kb_number, '"', '\\"') || '"}');
        END IF;
        IF (v_kb_sys_id IS NOT NULL) THEN
            filter_parts := ARRAY_APPEND(filter_parts, '"@eq": {"KB_SYS_ID": "' || REPLACE(:v_kb_sys_id, '"', '\\"') || '"}');
        END IF;
        IF (v_knowledge_base IS NOT NULL) THEN
            filter_parts := ARRAY_APPEND(filter_parts, '"@eq": {"KNOWLEDGE_BASE": "' || REPLACE(:v_knowledge_base, '"', '\\"') || '"}');
        END IF;
        IF (v_can_read IS NOT NULL) THEN
            filter_parts := ARRAY_APPEND(filter_parts, '"@eq": {"CAN_READ_USER_CRITERIA": "' || REPLACE(:v_can_read, '"', '\\"') || '"}');
        END IF;
        IF (v_cannot_read IS NOT NULL) THEN
            filter_parts := ARRAY_APPEND(filter_parts, '"@eq": {"CANNOT_READ_USER_CRITERIA": "' || REPLACE(:v_cannot_read, '"', '\\"') || '"}');
        END IF;

        IF (ARRAY_SIZE(filter_parts) = 1) THEN
            json_config := json_config || filter_parts[0];
        ELSE
            json_config := json_config || '"@and": [' || ARRAY_TO_STRING(filter_parts, ',') || ']';
        END IF;

        json_config := json_config || '}';
    END IF;

    json_config := json_config || '}';
    json_config_escaped := REPLACE(json_config, '''', '''''');

    EXECUTE IMMEDIATE
        'SELECT PARSE_JSON(' ||
            'SNOWFLAKE.CORTEX.SEARCH_PREVIEW(''' ||
                '{{ KB_DATABASE_NAME }}.{{ KB_SCHEMA_NAME }}.KB_SEARCH' || ''', ' ||
                '''' || json_config_escaped || '''' ||
            ')' ||
        '):"results" AS results';

    qid := LAST_QUERY_ID();

    SELECT ARRAY_AGG(r.value)::VARIANT
    INTO :search_results
    FROM TABLE(RESULT_SCAN(:qid)) t,
         LATERAL FLATTEN(input => t.results) r;

    IF (NOT v_exclude_articles) THEN
        SELECT ARRAY_AGG(
            OBJECT_CONSTRUCT(
                'kb_sys_id', a.KB_SYS_ID,
                'kb_number', a.KB_NUMBER,
                'summary', a.SUMMARY,
                'full_text', a.FULL_TEXT,
                'chunk_count', a.CHUNK_COUNT
            )
        )::VARIANT
        INTO :articles
        FROM (
            SELECT
                c.KB_SYS_ID,
                MAX(c.KB_NUMBER) AS KB_NUMBER,
                MAX(CASE WHEN c.CHUNK_INDEX = 0 OR c.CHUNK_INDEX = 1 THEN
                    {{ KB_DATABASE_NAME }}.{{ KB_SCHEMA_NAME }}.FN_DECOMPOSE_CHUNK(c.CHUNK_TEXT)['summary']::STRING
                END) AS SUMMARY,
                LISTAGG(
                    COALESCE({{ KB_DATABASE_NAME }}.{{ KB_SCHEMA_NAME }}.FN_DECOMPOSE_CHUNK(c.CHUNK_TEXT)['chunk_text']::STRING, ''),
                    ''
                ) WITHIN GROUP (ORDER BY TRY_TO_NUMBER(c.CHUNK_INDEX), c.CHUNK_INDEX) AS FULL_TEXT,
                COUNT(*) AS CHUNK_COUNT
            FROM {{ KB_DATABASE_NAME }}.{{ KB_SCHEMA_NAME }}.KB_CHUNKS c
            WHERE c.KB_SYS_ID IN (
                SELECT DISTINCT sr.value['KB_SYS_ID']::STRING
                FROM TABLE(FLATTEN(input => :search_results)) sr
            )
            GROUP BY c.KB_SYS_ID
        ) a;
    END IF;

    IF (v_exclude_articles) THEN
        result := OBJECT_CONSTRUCT(
            'query', v_question,
            'limit', v_limit,
            'results', search_results
        );
    ELSE
        result := OBJECT_CONSTRUCT(
            'query', v_question,
            'limit', v_limit,
            'results', search_results,
            'articles', articles
        );
    END IF;

    RETURN result;
END;
$$;
