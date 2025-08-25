import typer
import sqlite3
from . import server

app = typer.Typer()


@app.callback()
def callback():
    """
    db command
    """


@app.command()
def init(db_file: str, sql_file: str):
    """
    Initialize the database.
    """
    try:
        with open(sql_file, "r") as file:
            sql_script = file.read()
    except FileNotFoundError:
        print(f"Error: The file '{sql_file}' was not found.")
        exit(1)

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        for statement in sql_script.split(";"):
            clean_statement = statement.strip()
            if clean_statement:
                try:
                    print(f"\n{clean_statement}\n")
                    cursor.execute(clean_statement)
                except sqlite3.Error as e:
                    print(f"Error executing SQL statement: {clean_statement}")
                    print(f"SQLite error: {e}")
                    break

        conn.commit()
        print("All SQL statements executed successfully.")

    except sqlite3.Error as e:
        print(f"Database connection error: {e}")

    finally:
        if conn:        # Execute SQL commands here...
            conn.close()


@app.command()
def serve(port: int = 50051):
    """
    Start the Database gRPC service
    """
    print(f"Starting server on port {port}...")
    server.run(port)
