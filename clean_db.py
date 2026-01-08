import os
import snowflake.connector
import re

def clean_database():
    conn=snowflake.connector.connect(
        user=os.environ.get("SNOWFLAKE_USER"),
        password=os.environ.get("SNOWFLAKE_PASSWORD"),
        account=os.environ.get("SNOWFLAKE_ACCOUNT"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
        database=os.environ.get("SNOWFLAKE_DATABASE"),
        schema=os.environ.get("SNOWFLAKE_SCHEMA"),
    )
    cur=conn.cursor()

    cur.execute("DROP TABLE IF EXISTS ANALYSIS_METRICS")
    cur.execute("DROP TABLE IF EXISTS PROJECT_SUMMARY")

    cur.close()
    conn.close()
    print("Database cleaned.")

if __name__=="__main__":
    clean_database()
