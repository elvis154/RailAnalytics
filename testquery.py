import oracledb
import sys

# --- Oracle Instant Client Configuration ---
INSTANT_CLIENT_PATH = r"C:\Users\Abishek\Downloads\instantclient-basic-windows.x64-23.8.0.25.04\instantclient_23_8"

# --- Database Connection Parameters ---
DB_USER = "intern"
DB_PASSWORD = "inT##2025"
DB_HOST = "10.3.9.4"
DB_PORT = 1523
DB_SID = "traffic"

# --- Table Details ---
TARGET_SCHEMA = "FOISGOODS"
TARGET_TABLE = "carr_apmt_excl_adv_19_20"

# Construct the DSN (Data Source Name) string for SID connection
DSN = f"{DB_HOST}:{DB_PORT}/{DB_SID}"

# --- Initialize Oracle Client for Thick Mode ---
try:
    oracledb.init_oracle_client(lib_dir=INSTANT_CLIENT_PATH)
except oracledb.Error as e:
    print(f"Oracle Client Initialization Error: {e}")
    sys.exit(1)

# --- Query Logic ---
connection = None
cursor = None

try:
    connection = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DSN)
    cursor = connection.cursor()

    # Query for Row 5 (total SUM(WR))
    query_row5 = f"""
            SELECT SUM(WR) AS SUM_DIFF
            FROM {TARGET_SCHEMA}.{TARGET_TABLE}
        """
    print("Executing Row 5 query:", query_row5)
    cursor.execute(query_row5)
    total_sum = cursor.fetchone()[0] or 0  # Handle null sum
    print(f"Row 5 Total SUM(WR): {int(total_sum)}")

    # Query for sum of WR by CMDT
    query_cmdt = f"""
            SELECT TRIM(CMDT) AS CMDT, SUM(WR) AS SUM_DIFF
            FROM {TARGET_SCHEMA}.{TARGET_TABLE}
            WHERE CMDT IS NOT NULL
            GROUP BY TRIM(CMDT)
            ORDER BY TRIM(CMDT)
        """
    print("Executing CMDT query:", query_cmdt)
    cursor.execute(query_cmdt)
    results = cursor.fetchall()  # Fetch all rows
    print("Sum of WR by CMDT:")
    cmdt_sum = 0  # Initialize sum of CMDT sums
    for row in results:
        cmdt = row[0]
        sum_wr = row[1] if row[1] is not None else 0  # Handle null sums
        print(f"{cmdt}: {int(sum_wr)}")  # Format as COAL: 1203
        cmdt_sum += sum_wr  # Add to total CMDT sum

    # Print the sum of CMDT sums
    print(f"Total sum of WR across all CMDT values: {int(cmdt_sum)}")

    # Verify number of distinct CMDT values
    query_count = f"""
            SELECT COUNT(DISTINCT TRIM(CMDT)) AS distinct_count
            FROM {TARGET_SCHEMA}.{TARGET_TABLE}
            WHERE CMDT IS NOT NULL
        """
    cursor.execute(query_count)
    count = cursor.fetchone()[0]
    print(f"Number of distinct CMDT values: {count}")

except oracledb.Error as e:
    print(f"Database Error: {e}")
except Exception as e:
    print(f"General Error: {e}")
finally:
    if cursor:
        cursor.close()
    if connection:
        connection.close()