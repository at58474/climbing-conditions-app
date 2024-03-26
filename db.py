import pymysql

# Set the database credentials
host = 'route-database.cnkg64eooql0.us-east-2.rds.amazonaws.com'
port = 3306
user = 'at58474'
password = 'Azsxdcfv12^^!!'
database = 'route-database'

# Connect to the database
connection = pymysql.connect(
    host=host,
    port=port,
    user=user,
    password=password,
    database=database
)

# Create a cursor object
cursor = connection.cursor()

# inserting data to db
def add_text(text_value):
    cursor.execute("INSERT INTO test(test_id, text) VALUES (DEFAULT, %s)", (text_value))
    connection.commit()
    return 1

# Close the cursor and connection
cursor.close()
connection.close()