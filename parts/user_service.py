from datetime import datetime, timedelta
from flask import request
import uuid
import mariadb
import urllib


class UserService:
    def __init__(self, pool: mariadb.ConnectionPool):
        self.pool = pool

    def get_all_users(self):
        conn = self.pool.get_connection()
        cur = conn.cursor()

        cur.execute(
            """SELECT U.id, U.username, U.name, GROUP_CONCAT(R.role_name) FROM users U LEFT JOIN userroles R ON U.id = R.user_id GROUP BY U.id""")
        result = cur.fetchall()
        conn.close()

        return [
            {
                "id": r[0],
                "username": r[1],
                "name": r[2],
                "roles": [] if str(r[3]) == "None" else str(r[3]).split(",")
            }
            for r in result]


    def get_user_info_id(self, id: int):
        conn = self.pool.get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT U.username, U.name, GROUP_CONCAT(R.role_name) 
            FROM users U 
            LEFT JOIN userroles R ON U.id = R.user_id 
            WHERE U.id = %s
            GROUP BY U.id
            """, (id,))
        r = cur.fetchone()
        conn.close()

        if r is not None:
            return {
                "username": r[0],
                "name": r[1],
                "roles": [] if str(r[2]) == "None" else str(r[2]).split(",")
            }

    def get_user_info_username(self, username):
        conn = self.pool.get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT U.username, U.name, GROUP_CONCAT(R.role_name) 
            FROM users U 
            LEFT JOIN userroles R ON U.id = R.user_id 
            WHERE U.username = %s
            GROUP BY U.id
            """, (username,))
        r = cur.fetchone()
        conn.close()

        if r is not None:
            return {
                "username": r[0],
                "name": r[1],
                "roles": [] if str(r[2]) == "None" else str(r[2]).split(",")
            }

    def create_session(self, username, rememberMe=False):
        guid = uuid.uuid4().hex
        date = None if rememberMe else datetime.now() + timedelta(days=1)

        conn = self.pool.get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO `sessions` (`id`, `user_id`, `key_value`, `expiration_time`) 
            VALUES (NULL, (
                SELECT id FROM users WHERE username = %s LIMIT 1
            ), %s, %s)
        """, (username, guid, date))

        conn.commit()
        conn.close()

        return guid, date

    def post_login_session(self, headers):
        """Perform login with as session key"""

        # Read session key from header
        sessionKey = urllib.parse.unquote(headers["Authorization"][8:])

        # Check if session key is in database
        conn = self.pool.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT user_id FROM sessions 
            WHERE key_value = %s 
            AND (expiration_time > CURRENT_TIMESTAMP() OR expiration_time IS NULL)
            LIMIT 1
            """, (sessionKey, ))
        result = cur.fetchone()
        conn.close()

        # If so, fetch user data and return user info
        if result is not None:

            # Get user info
            userInfo = self.get_user_info_id(result[0])

            # Send back session info
            userInfo["sessionKey"] = sessionKey
            userInfo["expiration"] = None

            return {"result": True, "data": userInfo}
        else:
            return {"result": False, "data": {"message": "ERROR: No matching session was found!"}}

    def post_login_password(self, headers, body):
        """Perform login with username and password"""

        # Read json body and headers
        rememberMe: bool = body['rememberMe']
        decoded = (urllib.parse.unquote(headers["Authorization"][6:])).split(":")

        # Check if login data is correct
        conn = self.pool.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT username, password FROM users 
            WHERE username = %s AND password = %s
            """, (decoded[0], decoded[1]))
        result = cur.fetchone()
        conn.close()

        # If so, fetch user data and return
        if result is not None:

            # Get user info
            userInfo = self.get_user_info_username(decoded[0])

            # Create session for user
            sessionKey = self.create_session(decoded[0], rememberMe)
            userInfo["sessionKey"], userInfo["expiration"] = sessionKey

            return {"result": True, "data": userInfo}

        else:
            return {"result": False, "data": {"message": "ERROR: No user with matching login data was found!"}}

    def check_authorization(self, roles, headers, allReq=False) -> bool:

        # If no authorization header is set, return false
        if headers.get("Authorization", None) is None:
            return False

        # Read session key from header
        sessionKey = urllib.parse.unquote(headers["Authorization"][8:])

        # DB request
        conn = self.pool.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT R.role_name FROM sessions S 
            JOIN users U ON S.user_id = U.id 
            JOIN userroles R ON U.id = R.user_id 
            WHERE S.key_value = %s
            AND (S.expiration_time > CURRENT_TIMESTAMP() OR S.expiration_time IS NULL)
        """, (sessionKey,))

        conn.close()

        result = [e[0] for e in cur.fetchall()]

        # Return false if no roles are retrieved
        if len(result) <= 0:
            return False

        # Check if one (or all) of the required roles is present in the roles of the user
        check = [(True if e in result else False) for e in roles]
        return all(check) if allReq else any(check)