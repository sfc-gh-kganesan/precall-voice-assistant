CREATE OR REPLACE PROCEDURE GET_CALL_TRANSCRIPT(INPUT_CALL_ID VARCHAR)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
DECLARE
    transcript VARCHAR;
BEGIN
    -- Select the transcript into the variable
    SELECT CALL_TRANSCRIPT
    INTO transcript
    FROM SANDBOX.SCRATCH.FAKE_SALES_CALL_TRANSCRIPTS
    WHERE CALL_ID = :INPUT_CALL_ID;

    -- Return the transcript if found, otherwise return a message
    RETURN COALESCE(transcript, 'CALL_ID not found');
END;
$$;
