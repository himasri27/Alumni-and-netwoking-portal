# Alumni and Networking Portal - Running Instructions

1. **Install Python 3.x** if not already installed.
2. **Navigate to the project directory:**
   ```sh
   cd alumni_portal
   ```
3. **(Optional but recommended) Create a virtual environment:**
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. **Install required packages:**
   ```sh
   pip install flask
   ```
5. **Initialize the database:**
   - The database will be created automatically on first run.
   - If you want to manually create it, run:
   ```sh
   python app.py
   ```
   (This will create `database.db` if it does not exist.)
6. **Run the Flask app:**
   ```sh
   python app.py
   ```
7. **Open your browser and go to:**
   [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

- To stop the server, press `Ctrl+C` in the terminal.
- All data is stored in `database.db` (SQLite).
- For any issues, check the terminal for error messages.

---

## Admin Panel (Management)

1. **Access the admin login page:**
   - Visit: `http://127.0.0.1:5000/admin/login`

2. **Create an admin user (manual step):**
   - Run a Python shell in the project directory:
     ```sh
     python
     ```
   - Then run:
     ```py
     import sqlite3
     from werkzeug.security import generate_password_hash

     db = sqlite3.connect('database.db')
     db.execute(
         'INSERT INTO admins (username, password) VALUES (?, ?)',
         ('admin', generate_password_hash('YourStrongPassword'))
     )
     db.commit()
     db.close()
     ```
   - Replace `admin` and `YourStrongPassword` with your desired credentials.

3. **Approve new registrations:**
   - New users are created with **pending approval**.
   - Log in as an admin and approve them via the admin dashboard.
