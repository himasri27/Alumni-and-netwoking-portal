# Photo Upload Feature - Implementation Summary

## Overview
Profile photo upload feature has been successfully added to the Alumni & Networking Portal. Users can now upload a profile photo during registration, and the photo is displayed in the alumni directory and on individual user profiles.

---

## Changes Made

### 1. Database Schema (`schema.sql`)
**Added:** `photo TEXT` column to the `users` table
- Stores the filename of the uploaded image
- Nullable (existing users won't be affected)

```sql
CREATE TABLE IF NOT EXISTS users (
    ...
    approved INTEGER NOT NULL DEFAULT 0,
    photo TEXT
);
```

### 2. Flask Backend (`app.py`)

#### New Imports
```python
from werkzeug.utils import secure_filename
```

#### File Upload Configuration
- **Upload Folder:** `static/uploads`
- **Allowed Extensions:** `jpg`, `jpeg`, `png`
- **Max File Size:** 5MB
- **Auto-creates uploads folder** if it doesn't exist

```python
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
```

#### Helper Functions
```python
def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload_file(file):
    """Save uploaded file and return its filename, or None if invalid.
    
    Returns:
        The saved filename (string) or None if the file is invalid/not provided.
    """
    # Securely saves file with timestamp prefix to avoid collisions
```

#### Updated Database Initialization
- `init_db()` now adds `photo` column to existing tables (safe migration)
- Runs once per app instance (not on every request)

#### Updated `/register` Route
- Accepts file upload via `request.files['photo']`
- Validates file type (only JPG/PNG allowed)
- Shows error flash message if invalid file type uploaded
- Saves filename to database on successful registration
- Handles cases where no photo is provided

```python
@app.route('/register', methods=['GET', 'POST'])
def register():
    # ... existing code ...
    
    # Handle file upload
    photo = None
    if 'photo' in request.files:
        photo_file = request.files['photo']
        photo = save_upload_file(photo_file)
        if photo_file and photo_file.filename and not photo:
            flash('Invalid image format. Please upload JPG or PNG.', 'danger')
            return redirect(url_for('register'))
    
    # ... database insertion with photo ...
    db.execute('INSERT INTO users (..., photo) VALUES (..., ?)', 
               (..., photo))
```

---

### 3. Frontend Templates

#### `register.html`
**Updated Form:**
- Added `enctype="multipart/form-data"` to allow file uploads
- Added file input field for photo upload:
  ```html
  <label>Profile Photo (JPG, PNG - optional):
    <input type="file" name="photo" accept=".jpg,.jpeg,.png">
  </label>
  ```
- Photo upload is optional (user can register without photo)

#### `index.html` - Directory View
**Added Photo Column:**
- First column now displays user photos (50x50 pixels)
- Shows "No photo" placeholder for users without photos

```html
<table>
    <tr><th>Photo</th><th>Name</th>...</tr>
    {% for alum in alumni %}
    <tr>
        <td>
            {% if alum.photo %}
                <img src="{{ url_for('static', filename='uploads/' + alum.photo) }}" 
                     width="50" height="50" alt="Profile">
            {% else %}
                <span style="color: #999;">No photo</span>
            {% endif %}
        </td>
        ...
    </tr>
    {% endfor %}
</table>
```

#### `index.html` - Profile View
**Added Profile Photo:**
- Displays larger photo (150x150 pixels) at the top of profile
- Shows with rounded corners styling

```html
{% if profile.photo %}
    <img src="{{ url_for('static', filename='uploads/' + profile.photo) }}" 
         width="150" height="150" alt="Profile Photo" 
         style="border-radius: 5px; margin-bottom: 20px;">
{% endif %}
```

#### `admin_dashboard.html`
**Updated User Table:**
- Added Photo column (40x40 pixels) for quick thumbnail view
- Shows "—" placeholder for users without photos
- Helps admins identify users visually

---

## Folder Structure

```
alumni_portal/
├── app.py
├── schema.sql
├── static/
│   ├── style.css
│   ├── script.js
│   └── uploads/          ← NEW: Stores uploaded photos
├── templates/
│   ├── register.html     ← UPDATED
│   ├── index.html        ← UPDATED
│   ├── admin_dashboard.html ← UPDATED
│   ├── login.html
│   ├── dashboard.html
│   └── admin_login.html
└── database.db
```

---

## Features & Safety

✅ **Image Validation**
- Only JPG, JPEG, PNG files allowed
- File size limit: 5MB
- Uses `secure_filename()` to prevent directory traversal attacks
- Generates unique filenames with timestamps to prevent collisions

✅ **User Experience**
- Photo upload is optional (users can register without photo)
- Clear error messages for invalid file types
- Graceful handling when no photo provided
- Smooth integration with existing registration flow

✅ **Database Safety**
- Migration adds `photo` column safely using `ALTER TABLE`
- Existing users unaffected (NULL photos for old users)
- Filename stored as TEXT for flexibility

✅ **File System Safety**
- Auto-creates `uploads` folder if missing
- Files saved to `static/uploads` (web-accessible)
- Unique filenames prevent overwrites

---

## Testing Checklist

- [ ] Register user WITHOUT photo → Should work, no photo shown
- [ ] Register user WITH photo (JPG) → Should display in directory & profile
- [ ] Register user WITH photo (PNG) → Should display in directory & profile
- [ ] Register user WITH invalid file (PDF, DOC) → Should show error message
- [ ] Login as admin → See photos in admin dashboard
- [ ] Click profile from directory → See large photo on profile page
- [ ] Directory table → See photo thumbnails before names

---

## Example Usage

1. **Register with Photo:**
   - Go to `/register`
   - Fill form
   - Upload JPG/PNG file
   - Click Register
   - Photo saved to `static/uploads/[timestamp]_[filename].jpg`

2. **View in Directory:**
   - Go to `/directory`
   - See photo in table (50x50)
   - Click user name or "View" link

3. **View on Profile:**
   - Click profile link from directory
   - See larger photo (150x150) with rounded corners
   - See user details

---

## Future Enhancements (Optional)

- Profile photo cropping/resizing
- Delete/edit photo from user dashboard
- Drag-and-drop upload interface
- Image compression before storage
- Automatic thumbnail generation
