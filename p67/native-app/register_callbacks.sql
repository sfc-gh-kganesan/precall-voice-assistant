create or replace procedure v1.register_reference(ref_name string, operation string, ref_or_alias string)
 returns string
 language sql
 as $$
      begin
      case (upper(operation))
         when 'ADD' then
            select system$set_reference(:ref_name, :ref_or_alias);
         when 'REMOVE' then
            select system$remove_reference(:ref_name);
         when 'CLEAR' then
            select system$remove_reference(:ref_name);
         else
            return 'unknown operation: ' || operation;
      end case;
      return 'operation ' || operation || ' succeeds.';
      end;
   $$;
grant usage on procedure v1.register_reference(string, string, string) to application role app_admin;

