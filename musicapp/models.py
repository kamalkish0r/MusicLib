from musicapp import db, login_manager, app
# from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    songs = db.relationship('Song', backref='owner', lazy=True)

    def __repr__(self) -> str:
        return f"User('{self.username}', '{self.email}')"

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'].encode('utf-8'), expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'].encode('utf-8'))
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)


class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    artist = db.Column(db.String(50), nullable=False)
    album = db.Column(db.String(50))
    filename = db.Column(db.String(150), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self) -> str:
        return f"Song('{self.title}', '{self.artist}', '{self.album}', '{self.filename}', '{self.owner_id}')"
