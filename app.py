from flask import Flask
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for session management

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'vsms'

# Initialize MySQL
mysql = MySQL(app)

# Import routes
from route import *

if __name__ == '__main__':
    app.run(debug=True)
