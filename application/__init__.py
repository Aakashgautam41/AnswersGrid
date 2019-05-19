import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
# from flask_mail import Mail
from os import environ

app = Flask(__name__)
app.config['SECRET_KEY'] = '5a9eaa60a27455b18c5f516d030e23ec'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Instance of SQLAlchemy database
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'akashgautam10071997@gmail.com'
app.config['MAIL_PASSWORD'] = 'kpripwtjykyvhqpx'
# mail = Mail(app)


from application import routes