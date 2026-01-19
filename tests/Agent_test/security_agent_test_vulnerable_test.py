import os
import subprocess
from flask import Flask, request

app = Flask(__name__)


AWS_SECRET = "AKIAIOSFODNN7EXAMPLE" 
DB_PASSWORD = "super_secret_password_123!"


@app.route("/delete_db")
def delete_database():

    user_cmd = request.args.get("cmd")
    subprocess.call(user_cmd, shell=True) 
    return "Database deleted!"

if __name__ == "__main__":
    app.run()