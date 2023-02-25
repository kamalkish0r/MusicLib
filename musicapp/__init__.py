import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail



app = Flask(__name__)
app.config['SECRET_KEY'] = 'bff174118bab515992e19912ccc83e8d'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'musicapp/static/uploads')
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")
mail = Mail(app)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@app.before_first_request
def create_tables():
    db.create_all()


app.add_url_rule(
    "/song/download/<int:song_id>", endpoint="download", build_only=True
)

from musicapp import routes