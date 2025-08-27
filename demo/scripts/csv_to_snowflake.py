#!/usr/bin/env python3

import csv
import sys
from typing import List, Dict, Any
import argparse
from datetime import datetime


def is_date(date_string: str, date_formats: List[str] = ['%Y-%m-%d', '%m/%d/%Y', '%d-%b-%Y']):
    """
    Checks if a string is a valid date for a list of possible formats.

    Args:
        date_string (str): The string to check.
        date_formats (list): A list of expected date formats.

    Returns:
        bool: True if the string is a valid date, False otherwise.
    """
    for date_format in date_formats:
        try:
            datetime.strptime(date_string, date_format)
            return True
        except ValueError:
            # Continue to the next format if this one fails
            pass
    return False


def infer_snowflake_type(value: str) -> str:
    """Infer Snowflake data type from a sample value."""
    if not value or value.strip() == '':
        return 'empty'
   
    if is_date(value):
        return 'date'

    # Try integer
    try:
        int(value)
        return 'integer'
    except ValueError:
        pass
    
    # Try float
    try:
        float(value)
        return 'float'
    except ValueError:
        pass

    # Try bool
    if value.lower() == 'true' or value.lower() == 'false':
        return 'boolean'
    
    # Default to VARCHAR
    return 'varchar'


def analyze_csv_columns(file_path: str, sample_size: int = 50) -> List[Dict[str, Any]]:
    """Analyze CSV file and determine column types."""
    columns = []
    
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        headers = reader.fieldnames
        
        # Read first few rows to infer types
        sample_rows = []
        for i, row in enumerate(reader):
            sample_rows.append(row)
            if i >= sample_size:  # Sample first N rows
                break
    
    # Analyze each column
    for header in headers:
        column_info = {
            'name': header,
            'type': 'varchar(16777216)'  # Default
        }
        
        # Collect sample values
        sample_values = [row.get(header, '') for row in sample_rows if row.get(header, '').strip()]
        
        if sample_values:
            # Try to infer the most restrictive type that fits all samples
            types_found = set()
            for value in sample_values:
                types_found.add(infer_snowflake_type(value))
            
            # Priority: DATE > BOOL > INTEGER > FLOAT > VARCHAR
            if 'date' in types_found and all(t in ['date', 'empty'] for t in types_found):
                column_info['type'] = 'date'
            elif 'boolean' in types_found and len(types_found) == 1:
                column_info['type'] = 'boolean'
            elif 'integer' in types_found and len(types_found) == 1:
                column_info['type'] = 'integer'
            elif 'float' in types_found and all(t in ['integer', 'float'] for t in types_found):
                column_info['type'] = 'float'
            else:
                column_info['type'] = 'varchar(16777216)'
        
        columns.append(column_info)
    
    return columns


def generate_create_table_sql(table_name: str, columns: List[Dict[str, Any]]) -> str:
    """Generate CREATE TABLE SQL statement."""
    column_definitions = []
    
    for col in columns:
        col_name = col['name'].lower().replace(' ', '_') 
        col_type = col['type']
        column_definitions.append(f'    {col_name} {col_type}')
    
    sql = f"create or replace table {table_name} (\n"
    sql += ',\n'.join(column_definitions)
    sql += "\n);"
    
    return sql


def escape_sql_value(value: str, column_type: str) -> str:
    """Escape values for SQL insertion."""
    if not value or value.strip() == '':
        return 'NULL'
    
    if column_type in ['INTEGER', 'FLOAT']:
        try:
            if column_type == 'INTEGER':
                int(value)
            else:
                float(value)
            return value
        except ValueError:
            return 'NULL'
    
    # String values need quotes and escaping
    escaped = value.replace("'", "''")  # Escape single quotes
    return f"'{escaped}'"


def generate_insert_statement(table_name: str, file_path: str, columns: List[Dict[str, Any]]) -> str:
    """Generate a single INSERT statement with multiple rows."""
    all_values = []
    
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            row_values = []
            for col in columns:
                original_name = col['name']
                col_type = col['type']
                raw_value = row.get(original_name, '')
                escaped_value = escape_sql_value(raw_value, col_type)
                row_values.append(escaped_value)
            
            all_values.append(f"({', '.join(row_values)})")
    
    if not all_values:
        return ""
    
    column_names = [col['name'].upper().replace(' ', '_') for col in columns]
    sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES\n"
    sql += ',\n'.join(all_values) + ";"
    
    return sql


def main():
    parser = argparse.ArgumentParser(description='Generate Snowflake SQL from CSV file')
    parser.add_argument('csv_file', help='Path to CSV file')
    parser.add_argument('--table-name', default='my_table', help='Name for the Snowflake table')
    parser.add_argument('--output', help='Output file for SQL statements (default: stdout)')
    
    args = parser.parse_args()
    
    try:
        # Analyze CSV structure
        columns = analyze_csv_columns(args.csv_file)
        
        # Generate SQL statements
        create_sql = generate_create_table_sql(args.table_name, columns)
        insert_statement = generate_insert_statement(args.table_name, args.csv_file, columns)
        
        # Output results
        output_lines = [create_sql, '', insert_statement] if insert_statement else [create_sql]
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write('\n'.join(output_lines))
            print(f"SQL statements written to {args.output}")
        else:
            print('\n'.join(output_lines))
            
    except FileNotFoundError:
        print(f"Error: File '{args.csv_file}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
