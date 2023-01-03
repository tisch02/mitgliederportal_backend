from flask import Flask, request, abort
from flask_cors import CORS
import mariadb
import dbconfig

# Import all services
from parts.user_service import UserService

# Create flask app and connect to database
app = Flask(__name__)
CORS(app)
pool = mariadb.ConnectionPool(**dbconfig.pool_config)

# Create services
user_service = UserService(pool)


# Authorizazion Wrapper ---------------------------------------------------------
def authorizeAcces(roles=None, all=False):

    def wrap_f(func):
        def wrap(*args, **kwargs):

            # Do Authorization
            valid = True if roles is None else user_service.check_authorization(roles, request.headers, all)

            # Return error or result
            if valid:
                return func(*args, **kwargs)
            else:
                abort(403)

        wrap.__name__ = func.__name__
        return wrap

    return wrap_f


# Routes ------------------------------------------------------------------------
@app.route('/test')
@authorizeAcces(["admin", "user"])
def get_test():
    print("Test")
    return "Test"


@app.route('/users')
@authorizeAcces(["admin"])
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
