import os
import secrets
from flask import render_template, url_for, flash, redirect, request, Response, make_response, send_file, abort, send_from_directory
from musicapp.models import User, Song
from musicapp.forms import RegistrationForm, LoginForm, UpdateAccountForm, SongForm, SearchForm, RequestResetForm, ResetPasswordForm, SongMetadataForm
from musicapp import app, bcrypt, db, mail
from flask_login import login_user, logout_user, current_user, login_required
from mutagen.mp3 import MP3
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from flask_mail import Message


@app.route('/')
@app.route('/home')
@login_required
def home():
    page = request.args.get('page', 1, type=int)
    songs = Song.query.filter_by(
        owner_id=current_user.id).paginate(page=page, per_page=12)
    return render_template('home.html', songs=songs)


@app.route('/collection')
@login_required
def collection():
    page = request.args.get('page', 1, type=int)
    songs = Song.query.paginate(page=page, per_page=12)
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
    file_name = secure_filename(song.filename)
    _, f_ext = os.path.splitext(file_name)
    song_filename = random_hex + '.mp3'
    song_path = os.path.join(
        app.root_path, app.config['UPLOAD_FOLDER'], song_filename)
    song.save(song_path)

    return song_filename


@app.route('/song/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = SongForm()
    if form.validate_on_submit():
        song_file = form.song.data
        audio = MP3(song_file)
        title = audio["TIT2"].text[0] if "TIT2" in audio else "Unknown Title"
        artist = audio["TPE1"].text[0] if "TPE1" in audio else "Unknown Artist"
        album = audio["TALB"].text[0] if "TALB" in audio else "Unknown Album"

        song_file = save_song(song_file)

        song = Song(title=title, artist=artist,
                    album=album, owner=current_user, filename=song_file)
        db.session.add(song)
        db.session.commit()

        return redirect(url_for('song_metadata', id=song.id))

    return render_template('upload_song.html', title='Upload Song', form=form)


@app.route('/song/upload/metadata/<int:id>', methods=['GET', 'POST'])
@login_required
def song_metadata(id):
    form = SongMetadataForm()
    song = Song.query.get_or_404(id)
    if song.owner != current_user:
        abort(403)

    if form.validate_on_submit():
        song.title = form.title.data
        song.artist = form.artist.data
        song.album = form.album.data
        db.session.commit()

        flash(f'Song `{form.title.data}` has been uploaded!', 'success')
        return redirect(url_for('upload'))
    elif request.method == 'GET':
        form.title.data = song.title
        form.artist.data = song.artist
        form.album.data = song.album
    return render_template('song_metadata.html', form=form)


@app.route('/get_audio')
@login_required
def get_audio(song_path):
    return send_file(song_path, mimetype="audio/mp3", as_attachment=True)


@app.route('/play/<int:song_id>')
@login_required
def song(song_id):
    song = Song.query.get_or_404(song_id)
    song_file = url_for('static', filename='uploads/' + song.filename)
    return render_template('song.html', song=song, music=song_file)


@app.route('/song/delete/<int:song_id>', methods=['POST'])
@login_required
def delete(song_id):
    song = Song.query.get_or_404(song_id)
    if song.owner != current_user:
        abort(403)
    song_title = song.title
    db.session.delete(song)
    db.session.commit()
    flash(f'Song `{song_title}` has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route('/song/download/<int:song_id>', methods=['GET'])
@login_required
def download(song_id):
    song = Song.query.get_or_404(song_id)
    song_path = os.path.join(app.config['UPLOAD_FOLDER'], song.filename)
    if not os.path.exists(song_path):
        flash("Song file not found on server", "error")
        return redirect(url_for('index'))
    try:
        audio = MP3(song_path)
        title = audio["TIT2"].text[0] if "TIT2" in audio else song.title
        artist = audio["TPE1"].text[0] if "TPE1" in audio else song.artist
        album = audio["TALB"].text[0] if "TALB" in audio else song.album
    except Exception as e:
        flash(f"Error reading metadata: {e}", "error")
        title, artist, album = song.title, song.artist, song.album

    response = send_file(song_path, as_attachment=True,
                         attachment_filename=f'{title}.mp3', mimetype='audio/mpeg')

    response.headers['Content-Type'] = 'audio/mpeg'
    response.headers['Content-Disposition'] = f'attachment; filename="{title}.mp3"'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Redirect'] = f'/download/{song.filename}'

    return response
    song = Song.query.get_or_404(song_id)
    song_path = os.path.join(app.config['UPLOAD_FOLDER'], song.filename)

    # Set response headers for file download
    headers = {
        'Content-Type': 'audio/mpeg',
        'Content-Disposition': f'attachment; filename="{song.title}.mp3"'
    }

    # Read the song file and create a Response object with the file data
    with open(song_path, 'rb') as f:
        file_data = f.read()
        response = make_response(file_data)

    # Set response headers and return response
    response.headers = headers
    return response


@app.context_processor
def layout():
    form = SearchForm()
    return dict(form=form)


@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form = SearchForm()
    if form.validate_on_submit():
        search_input_text = form.search_input_text.data
        results = Song.query.filter(
            or_(Song.title.ilike('%{}%'.format(search_input_text)),
                Song.artist.ilike('%{}%'.format(search_input_text)),
                Song.album.ilike('%{}%'.format(search_input_text)))).all()

        if results:
            return render_template('search_results.html', songs=results, search_input_text=search_input_text, form=form)
        else:
            flash('No results found!', 'danger')
    return render_template('search.html', form=form)


def send_password_reset_email(user):
    token = user.get_reset_token()
    msg = Message(subject='Music Lib Password Reset Request',
                  recipients=[user.email], sender='noreply@demo.com')
    msg.body = f'''To reset your password, please go to the following link :
    {url_for('reset_password', token=token, _external=True)}

    If you did not make this request then simply ignore this mail.
    '''


@app.route('/reset_password', methods=['GET', 'POST'])
def password_reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_password_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect('url_for')
    return render_template('password_reset_request.html', title="Reset Password", form=form)


@app.route('/reset_password/<string:token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    user = User.verify_reset_token(token)
    if user is None:
        flash('Token is invalid or expired!', 'warning')
        return redirect(url_for('password_reset_request'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(
            form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('Your password has been updated! Please login to continue.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', title="Reset Password", form=form)
