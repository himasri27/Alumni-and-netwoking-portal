import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a random secret key
DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database.db')

# --- File Upload Configuration ---
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create uploads folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- File Upload Helpers ---
def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload_file(file):
    """Save uploaded file and return its filename, or None if invalid.
    
    Args:
        file: A werkzeug.datastructures.FileStorage object from request.files
    
    Returns:
        The saved filename (string) or None if the file is invalid/not provided.
    """
    if not file or file.filename == '':
        return None  # No file provided

    if not allowed_file(file.filename):
        return None  # File type not allowed

    # Generate a safe filename
    original_filename = secure_filename(file.filename)
    # Add a timestamp to avoid collisions
    import time
    timestamp = int(time.time() * 1000)
    filename = f"{timestamp}_{original_filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(filepath)
        app.logger.info("Saved uploaded file: %s", filename)
        return filename
    except Exception as e:
        app.logger.error("Failed to save uploaded file: %s", e)
        return None

# --- Database Setup ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        app.logger.debug("Opening SQLite DB at %s (exists=%s)", DATABASE, os.path.exists(DATABASE))
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        # Ensure optional schema changes are applied without breaking existing data.
        try:
            db.execute('ALTER TABLE users ADD COLUMN approved INTEGER NOT NULL DEFAULT 0')
        except sqlite3.OperationalError:
            # Column already exists.
            pass
        try:
            db.execute('ALTER TABLE users ADD COLUMN photo TEXT')
        except sqlite3.OperationalError:
            # Column already exists.
            pass
        db.commit()
        # Ensure an admin user exists (default: admin / admin123)
        ensure_default_admin()


def get_admin(username):
    """Fetch an admin by username (case-insensitive)."""
    db = get_db()
    return db.execute('SELECT * FROM admins WHERE username = ? COLLATE NOCASE', (username,)).fetchone()


def create_admin(username, password):
    """Insert a new admin user with a hashed password."""
    db = get_db()
    hashed = generate_password_hash(password)
    try:
        db.execute('INSERT INTO admins (username, password) VALUES (?, ?)', (username, hashed))
        db.commit()
        app.logger.info("Created admin user '%s'", username)
    except sqlite3.IntegrityError:
        app.logger.debug("Admin user '%s' already exists.", username)


def ensure_default_admin():
    admin = get_admin('admin')
    if not admin:
        create_admin('admin', 'admin123')
    else:
        app.logger.debug('Default admin exists: %s', dict(admin))


def setup_app():
    """Initialize the database schema and default data.

    This is safe to call multiple times (it will only run once per process).
    """
    if app.config.get('DB_INITIALIZED'):
        return

    with app.app_context():
        init_db()

    app.config['DB_INITIALIZED'] = True


# Initialize at import time (for use with flask run) and again in main.
setup_app()


# --- Helpers ---
def admin_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Admin login required.', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        grad_year = request.form['grad_year']
        job = request.form['job']
        company = request.form['company']
        location = request.form['location']
        
        # Handle file upload
        photo = None
        if 'photo' in request.files:
            photo_file = request.files['photo']
            photo = save_upload_file(photo_file)
            print(f"DEBUG: Photo filename received: {photo_file.filename if photo_file else 'None'}")
            print(f"DEBUG: Photo saved as: {photo}")
            if photo_file and photo_file.filename and not photo:
                # File was provided but not saved (invalid type)
                flash('Invalid image format. Please upload JPG or PNG.', 'danger')
                return redirect(url_for('register'))
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if user:
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        
        # New registrations require admin approval before they can log in.
        db.execute('INSERT INTO users (name, email, password, grad_year, job, company, location, approved, photo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                   (name, email, generate_password_hash(password), grad_year, job, company, location, 0, photo))
        db.commit()
        flash('Registration successful! Your account is pending admin approval.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if user and check_password_hash(user['password'], password):
            # If the users table does not yet have approved column, default to approved.
            approved = user['approved'] if 'approved' in user.keys() else 1
            if not approved:
                flash('Your account is pending admin approval.', 'info')
                return redirect(url_for('login'))
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))

# --- Admin Routes ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        app.logger.debug("Admin login attempt: username=%s password=%s", username, password)

        admin = get_admin(username)
        app.logger.debug("Admin record found: %s", dict(admin) if admin else None)

        if admin and check_password_hash(admin['password'], password):
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials.', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    flash('Admin logged out.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_login_required
def admin_dashboard():
    db = get_db()
    users = db.execute('SELECT id, name, email, grad_year, job, company, location, approved FROM users').fetchall()
    posts = db.execute('''SELECT posts.id as post_id, posts.content, posts.timestamp,
                                 users.name as user_name
                          FROM posts
                          JOIN users ON posts.user_id = users.id
                          ORDER BY posts.timestamp DESC''').fetchall()
    return render_template('admin_dashboard.html', users=users, posts=posts)

@app.route('/admin/approve_user/<int:user_id>', methods=['POST'])
@admin_login_required
def admin_approve_user(user_id):
    db = get_db()
    db.execute('UPDATE users SET approved = 1 WHERE id = ?', (user_id,))
    db.commit()
    flash('User approved.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_login_required
def admin_delete_user(user_id):
    db = get_db()
    db.execute('DELETE FROM posts WHERE user_id = ?', (user_id,))
    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()
    flash('User deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_post/<int:post_id>', methods=['POST'])
@admin_login_required
def admin_delete_post(post_id):
    db = get_db()
    db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    db.commit()
    flash('Post deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    if request.method == 'POST':
        content = request.form['content']
        db.execute('INSERT INTO posts (user_id, content) VALUES (?, ?)', (session['user_id'], content))
        db.commit()
        flash('Post added!', 'success')
    posts = db.execute('''SELECT posts.content, posts.timestamp, users.name FROM posts JOIN users ON posts.user_id = users.id ORDER BY posts.timestamp DESC''').fetchall()
    return render_template('dashboard.html', posts=posts)

@app.route('/directory')
def directory():
    db = get_db()
    alumni = db.execute('SELECT id, name, email, grad_year, job, company, location, photo FROM users').fetchall()
    return render_template('index.html', alumni=alumni, show_directory=True)

@app.route('/profile/<int:user_id>')
def profile(user_id):
    db = get_db()
    user = db.execute('SELECT id, name, email, grad_year, job, company, location, photo FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('directory'))
    return render_template('index.html', profile=user, show_profile=True)

# --- Database Initialization Route (for first time setup) ---
@app.route('/initdb')
def initdb_route():
    setup_app()
    return 'Database initialized!'


if __name__ == '__main__':
    # Ensure database & schema are initialized on startup.
    setup_app()
    app.run(debug=True)
