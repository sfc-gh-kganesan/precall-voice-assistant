-- Call the stored procedure on one file
CALL inviq.service.extract_invoice_file('fe4dc8da-48a1-4c2b-aea1-43a307f0268b_invoice_01.pdf');

-- List all files in the stage
list @inviq.service.tmpfiles;


