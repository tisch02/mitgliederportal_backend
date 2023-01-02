from flask import Flask, request
from flask_cors import CORS
import mariadb
import dbconfig

# Import all services
from parts.user_service import UserService

# Create flask app and connect to database
app = Flask(__name__)
CORS(app)
conn = mariadb.connect(**dbconfig.config)

# Create services
user_service = UserService(conn)


# Routes ------------------------------------------------------------------------
@app.route('/users')
def get_all_users():
    return user_service.get_all_users()


@app.route('/login/password', methods=['POST'])
def post_login():
    if request.method == 'POST':
        return user_service.post_login_password(request.headers, request.json)


@app.route('/login/session', methods=['POST'])
def post_login_session():
    if request.method == 'POST':
        return user_service.post_login_session(request.headers)


# Run app -----------------------------------------------------------------------
if __name__ == '__main__':
    app.run()
