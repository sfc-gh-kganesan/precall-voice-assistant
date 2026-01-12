-- Setup Cortex Agent with SPROCs
-- Database: AI_FDE, Schema: CACHE_EXPERIMENTS
-- Safe: Only creates SPROCs, no table modifications

USE DATABASE AI_FDE;
USE SCHEMA CACHE_EXPERIMENTS;

-- Create stored procedures for math operations
CREATE OR REPLACE PROCEDURE add(a FLOAT, b FLOAT)
RETURNS FLOAT
LANGUAGE SQL
AS
$$
BEGIN
    -- Simulate production tool latency (7 seconds)
    CALL SYSTEM$SLEEP(7000);
    RETURN a + b;
END;
$$;

CREATE OR REPLACE PROCEDURE multiply(a FLOAT, b FLOAT)
RETURNS FLOAT
LANGUAGE SQL
AS
$$
BEGIN
    -- Simulate production tool latency (7 seconds)
    CALL SYSTEM$SLEEP(7000);
    RETURN a * b;
END;
$$;

CREATE OR REPLACE PROCEDURE divide(a FLOAT, b FLOAT)
RETURNS FLOAT
LANGUAGE SQL
AS
$$
BEGIN
    -- Simulate production tool latency (7 seconds)
    CALL SYSTEM$SLEEP(7000);
    RETURN a / b;
END;
$$;

CREATE OR REPLACE PROCEDURE subtract(a FLOAT, b FLOAT)
RETURNS FLOAT
LANGUAGE SQL
AS
$$
BEGIN
    -- Simulate production tool latency (7 seconds)
    CALL SYSTEM$SLEEP(7000);
    RETURN a - b;
END;
$$;

CREATE OR REPLACE PROCEDURE calculate_average(numbers ARRAY)
RETURNS FLOAT
LANGUAGE SQL
AS
$$
DECLARE
    avg_val FLOAT;
BEGIN
    -- Simulate production tool latency (7 seconds)
    CALL SYSTEM$SLEEP(7000);

    SELECT AVG(VALUE) INTO avg_val FROM TABLE(FLATTEN(INPUT => :numbers));
    RETURN avg_val;
END;
$$;

-- Test SPROCs
SELECT '=== Testing Math SPROCs ===' as test_section;
CALL add(5, 3);
CALL multiply(4, 2);
CALL divide(10, 2);
CALL subtract(10, 3);
CALL calculate_average([1, 2, 3, 4, 5]);

SELECT '=== Done ===' as status;
