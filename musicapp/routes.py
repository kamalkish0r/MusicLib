import os
import secrets
from flask import render_template, url_for, flash, redirect, request, Response, make_response, send_file
from musicapp.models import User, Song
from musicapp.forms import RegistrationForm, LoginForm, UpdateAccountForm, SongForm, SearchForm
from musicapp import app, bcrypt, db
from flask_login import login_user, logout_user, current_user, login_required
from mutagen.mp3 import MP3
from werkzeug.exceptions import RequestEntityTooLarge
from sqlalchemy import or_


@app.route('/')
@app.route('/home')
@login_required
def home():
    songs = Song.query.filter_by(owner_id=current_user.id).all()
    return render_template('home.html', songs=songs)


@app.route('/collection')
@login_required
def collection():
    songs = Song.query.all()
    return render_template('collection.html', title='All Songs', songs=songs)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(
            form.password.data).decode('utf-8')
        user = User(username=form.username.data,
                    email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account Successfully Created! Please login to continue.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        flash('Login Failed! Please check email and password.', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('account.html', title='Account', form=form)


@app.errorhandler(RequestEntityTooLarge)
def handle_413_error(e):
    flash("File SIZE LIMIT EXCEEDED! Only files of size less than 20MB are allowed.", 'danger')
    return redirect(request.url)


def save_song(song):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(song.filename)
    song_filename = random_hex + f_ext
    song_path = os.path.join(app.root_path, 'static/uploads', song_filename)
    song.save(song_path)

    return song_filename


@app.route('/song/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = SongForm()
    if form.validate_on_submit():
        song_file = form.song.data
        # if not song_file.filename.endswith('.mp3'):
        #     flash('Only mp3 files are allowed!', 'danger')
        #     return redirect(url_for('upload'))

        audio = MP3(song_file)
        title = audio["TIT2"].text[0] if "TIT2" in audio else "Unknown Title"
        artist = audio["TPE1"].text[0] if "TPE1" in audio else "Unknown Artist"
        album = audio["TALB"].text[0] if "TALB" in audio else "Unknown Album"

        song_file = save_song(song_file)

        song = Song(title=title, artist=artist,
                    album=album, owner=current_user, filename=song_file)
        db.session.add(song)
        db.session.commit()

        flash(f'{title} has been uploaded!', 'success')
        return redirect(url_for('upload'))
    return render_template('upload_song.html', title='Upload Song', form=form)


@app.route('/get_audio')
@login_required
def get_audio(song_path):
    return send_file(song_path, mimetype="audio/mp3", as_attachment=True)


@app.route('/play/<int:song_id>')
@login_required
def song(song_id):
    song = Song.query.get_or_404(song_id)
    song_file = url_for('static', filename='uploads/' + song.filename)
    return render_template('song.html', title=song.title, song=song, music=song_file)


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form = SearchForm()
    if form.validate_on_submit():
        search_input_text = form.search_input_text
        results = Song.query.filter(
            or_(Song.title.contains(search_input_text),
                Song.artist.contains(search_input_text),
                Song.album.contains(search_input_text))).all()

        return render_template('search_results.html', results=results, search_input_text=search_input_text)
    return redirect(url_for('home'))
