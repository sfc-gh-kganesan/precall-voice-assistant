CREATE OR REPLACE PROCEDURE <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.KB_GET(REQUEST VARIANT)
RETURNS VARIANT
LANGUAGE SQL
EXECUTE AS CALLER
COMMENT = 'Retrieve a single knowledge base article by sys_id or kb_number.'
AS
$$
DECLARE
    v_kb_sys_id    STRING;
    v_kb_number    STRING;
    v_summary      STRING;
    v_text         STRING;
    v_chunk_count  NUMBER;
BEGIN
    v_kb_sys_id := COALESCE(
        REQUEST:"kb_sys_id"::STRING,
        REQUEST:"KB_SYS_ID"::STRING
    );

    v_kb_number := COALESCE(
        REQUEST:"kb_number"::STRING,
        REQUEST:"KB_NUMBER"::STRING
    );

    IF (v_kb_sys_id IS NULL AND v_kb_number IS NULL) THEN
        RETURN OBJECT_CONSTRUCT(
            'text', NULL,
            'error', 'REQUEST must include either kb_sys_id or kb_number',
            'request', REQUEST
        )::VARIANT;
    END IF;

    IF (v_kb_sys_id IS NOT NULL) THEN
        SELECT
            MAX(CASE WHEN CHUNK_INDEX = 0 OR CHUNK_INDEX = 1 THEN
                <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.FN_DECOMPOSE_CHUNK(CHUNK_TEXT)['summary']::STRING
            END) AS summary,
            LISTAGG(
                COALESCE(<% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.FN_DECOMPOSE_CHUNK(CHUNK_TEXT)['chunk_text']::STRING, ''),
                ''
            ) WITHIN GROUP (ORDER BY TRY_TO_NUMBER(CHUNK_INDEX), CHUNK_INDEX) AS text,
            COUNT(*) AS chunk_count,
            MAX(KB_NUMBER)::STRING AS kb_number
        INTO :v_summary, :v_text, :v_chunk_count, :v_kb_number
        FROM <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.KB_CHUNKS
        WHERE KB_SYS_ID = :v_kb_sys_id;
    ELSE
        SELECT
            MAX(CASE WHEN CHUNK_INDEX = 0 OR CHUNK_INDEX = 1 THEN
                <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.FN_DECOMPOSE_CHUNK(CHUNK_TEXT)['summary']::STRING
            END) AS summary,
            LISTAGG(
                COALESCE(<% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.FN_DECOMPOSE_CHUNK(CHUNK_TEXT)['chunk_text']::STRING, ''),
                ''
            ) WITHIN GROUP (ORDER BY TRY_TO_NUMBER(CHUNK_INDEX), CHUNK_INDEX) AS text,
            COUNT(*) AS chunk_count,
            MAX(KB_SYS_ID)::STRING AS kb_sys_id
        INTO :v_summary, :v_text, :v_chunk_count, :v_kb_sys_id
        FROM <% KB_DATABASE_NAME %>.<% KB_SCHEMA_NAME %>.KB_CHUNKS
        WHERE KB_NUMBER::STRING = :v_kb_number;
    END IF;

    RETURN OBJECT_CONSTRUCT(
        'summary', COALESCE(v_summary, ''),
        'text', COALESCE(v_text, ''),
        'kb_sys_id', v_kb_sys_id,
        'kb_number', v_kb_number,
        'chunk_count', COALESCE(v_chunk_count, 0)
    )::VARIANT;
END;
$$;
