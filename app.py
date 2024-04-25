#!/usr/bin/env python3

import os
import sys
import subprocess
import datetime
from flask import Flask, render_template, request, redirect, url_for, make_response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash


import sentry_sdk
from sentry_sdk.integrations.flask import (
    FlaskIntegration,
)  # delete this if not using sentry.io

# from markupsafe import escape
import pymongo
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv(override=True)  # take environment variables from .env.

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    # enable_tracing=True,
    # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100% of sampled transactions.
    # We recommend adjusting this value in production.
    # profiles_sample_rate=1.0,
    integrations=[FlaskIntegration()],
    send_default_pii=True,
)

# instantiate the app using sentry for debugging
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)

# # turn on debugging if in development mode
app.debug = True if os.getenv("FLASK_ENV", "development") == "development" else False

# try to connect to the database, and quit if it doesn't work
try:
    cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
    db = cxn[os.getenv("MONGO_DBNAME")]  # store a reference to the selected database

    # verify the connection works by pinging the database
    cxn.admin.command("ping")  # The ping command is cheap and does not require auth.
    print(" * Connected to MongoDB!")  # if we get here, the connection worked!
except ConnectionFailure as e:
    # catch any database errors
    # the ping command failed, so the connection is not available.
    print(" * MongoDB connection error:", e)  # debug
    sentry_sdk.capture_exception(e)  # send the error to sentry.io. delete if not using
    sys.exit(1)  # this is a catastrophic error, so no reason to continue to live


# User
class User(UserMixin):
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username

    @staticmethod
    def get(user_id):
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return None
        return User(user_id, user['username'])

    def get_id(self):
        return str(self.user_id)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# set up the routes


@app.route("/")
def home():
    """
    Route for the home page.
    Simply returns to the browser the content of the index.html file located in the templates folder.
    """
    if current_user.is_authenticated:
        return redirect(url_for('todos'))
    
    return render_template("index.html")

@app.route("/login", methods=['POST', 'GET'])
def login():
    """
    Route for the login page.
    Simply returns to the browser the content of the login.html file located in the templates folder.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            user = User(user["_id"], username)
            login_user(user)

            return redirect(url_for('todos'))
        else:
            return render_template('login.html', error='Invalid username or password')
        
    if current_user.is_authenticated:
        return redirect(url_for('todos'))
    
    return render_template("login.html")

@app.route("/register", methods=['POST', 'GET'])
def register():
    """
    Route for the register page.
    Simply returns to the browser the content of the register.html file located in the templates folder.
    """
    if request.method == 'POST':
        username = request.form['username']
        existing_user = db.users.find_one({'username': username})
        if existing_user:
            return render_template('register.html', error='Username already exists')
        password = generate_password_hash(request.form['password'])
        db.users.insert_one({'username': username, 'password': password})
        return redirect(url_for('login'))
    
    if current_user.is_authenticated:
        return redirect(url_for('todos'))

    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    """
    Route for the logout.
    """
    logout_user()

    return redirect(url_for('home'))


@app.route("/todos")
# @login_required
def todos():
    """
    Route for GET requests to the todos page.
    """
    print("Todos:",current_user.username)

    todo_objs = db.todoapp.find({"username": current_user.username})

    return render_template("todos.html", todos=todo_objs) 

@app.route("/create_todo", methods=["POST"])
@login_required
def create_todo():
    """
    Route for POST requests to the create todo.
    Accepts the form submission data for a new tod and saves the todo to the database.
    """
    todo = request.form["todo"]
    date = request.form["date"]

    
    # create a new todo with the data the user entered
    todo_obj = {"username": current_user.username, "todo": todo, "date":date, "status": "incomplete"}

    db.todoapp.insert_one(todo_obj)  # insert a new todo

    return redirect(url_for('todos'))

@app.route("/update_todo_status/<mongoid>")
@login_required
def update_todo_status(mongoid):
    """
    Route for POST requests to the update todo status.
    Accepts the form submission data for the specified todo and updates the status of todo in the database.

    Parameters:
    mongoid (str): The MongoDB ObjectId of the record to be edited.
    """

    todo_obj = {
        "status": "complete"
    }

    db.todoapp.update_one(
        {"_id": ObjectId(mongoid)}, {"$set": todo_obj} 
    )

    return redirect(url_for('todos'))

@app.route("/delete_todo/<mongoid>")
@login_required
def delete(mongoid):
    """
    Route for GET requests to the delete todo.
    Deletes the specified todo from the database, and then redirects the browser to the todo page.

    Parameters:
    mongoid (str): The MongoDB ObjectId of the todo to be deleted.
    """
    db.todoapp.delete_one({"_id": ObjectId(mongoid)})

    return redirect(url_for('todos'))


@app.errorhandler(Exception)
def handle_error(e):
    """
    Output any errors - good for debugging.
    """
    return render_template("error.html", error=e)  # render the edit template


# run the app
if __name__ == "__main__":
    # logging.basicConfig(filename="./flask_error.log", level=logging.DEBUG)
    # app.run(load_dotenv=True)
    app.run(debug=True)
