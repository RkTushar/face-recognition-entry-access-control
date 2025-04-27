from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import sqlite3
import face_recognition
import numpy as np
from datetime import datetime
import csv

app = Flask(__name__)
app.secret_key = 'supersecretkey'

UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DATABASE = 'database/visitors.db'

# Admin Credentials
ADMIN_USERNAME = 'tushar'
ADMIN_PASSWORD = '123321'

def save_visitor_to_db(name, visit_date, encoding):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            visit_date TEXT,
            encoding BLOB
        )
    ''')
    c.execute('INSERT INTO visitors (name, visit_date, encoding) VALUES (?, ?, ?)',
              (name, visit_date, encoding.tobytes()))
    conn.commit()
    conn.close()

def log_access(name, status):
    if not os.path.exists('logs'):
        os.makedirs('logs')
    log_file = 'logs/access_log.csv'
    with open(log_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([name, now, status])

@app.route('/')
def home():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('✅ Logged in successfully!')
            return redirect(url_for('home'))
        else:
            flash('❌ Invalid username or password.')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('✅ Logged out successfully.')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        visitor_name = request.form['name']
        visit_date = request.form['visit_date']
        photo = request.files['photo']

        if photo:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], photo.filename)
            photo.save(filepath)

            # Face Encoding
            image = face_recognition.load_image_file(filepath)
            encodings = face_recognition.face_encodings(image)

            if len(encodings) == 0:
                flash('❌ No face detected in the uploaded photo.')
                return redirect(url_for('register'))

            encoding = encodings[0]
            save_visitor_to_db(visitor_name, visit_date, encoding)

            flash(f'✅ Visitor {visitor_name} registered successfully!')
        else:
            flash('❌ No photo uploaded.')

        return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/entry', methods=['GET', 'POST'])
def entry():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        photo = request.files['photo']

        if photo:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], photo.filename)
            photo.save(filepath)

            # Load registered visitors
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("SELECT name, visit_date, encoding FROM visitors")
            visitors = c.fetchall()
            conn.close()

            known_encodings = []
            known_names = []
            known_dates = []

            for name, visit_date, encoding_blob in visitors:
                known_encodings.append(np.frombuffer(encoding_blob, dtype=np.float64))
                known_names.append(name)
                known_dates.append(visit_date)

            # Process uploaded image
            image = face_recognition.load_image_file(filepath)
            encodings = face_recognition.face_encodings(image)

            if len(encodings) == 0:
                flash('❌ No face detected in the uploaded photo.')
                return redirect(url_for('entry'))

            uploaded_encoding = encodings[0]

            matches = face_recognition.compare_faces(known_encodings, uploaded_encoding)
            face_distances = face_recognition.face_distance(known_encodings, uploaded_encoding)
            best_match_index = np.argmin(face_distances) if len(face_distances) > 0 else None

            if best_match_index is not None and matches[best_match_index]:
                today = datetime.now().strftime("%Y-%m-%d")
                if known_dates[best_match_index] == today:
                    flash(f"✅ Access Granted for {known_names[best_match_index]}")
                    log_access(known_names[best_match_index], "Access Granted")
                else:
                    flash(f"❌ Access Denied (Wrong Visit Date) for {known_names[best_match_index]}")
                    log_access(known_names[best_match_index], "Access Denied - Wrong Date")
            else:
                flash('❌ Face Not Recognized.')
                log_access('Unknown', "Face Not Recognized")

            return redirect(url_for('entry'))

    return render_template('entry.html')

@app.route('/logs')
def logs():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    log_entries = []

    if os.path.exists('logs/access_log.csv'):
        with open('logs/access_log.csv', mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                log_entries.append({
                    'name': row[0],
                    'timestamp': row[1],
                    'status': row[2]
                })

    return render_template('logs.html', logs=log_entries)

@app.route('/visitors')
def visitors():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT id, name, visit_date FROM visitors")
    visitors = c.fetchall()
    conn.close()

    # Remove duplicates (show each visitor name only once)
    unique_visitors = {}
    for visitor in visitors:
        visitor_id, name, visit_date = visitor
        if name not in unique_visitors:
            unique_visitors[name] = {
                'id': visitor_id,
                'name': name,
                'visit_date': visit_date
            }

    return render_template('visitors.html', visitors=unique_visitors.values())

@app.route('/edit/<int:visitor_id>', methods=['GET', 'POST'])
def edit_visitor(visitor_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    if request.method == 'POST':
        new_name = request.form['name']
        new_visit_date = request.form['visit_date']
        c.execute('UPDATE visitors SET name = ?, visit_date = ? WHERE id = ?', (new_name, new_visit_date, visitor_id))
        conn.commit()
        conn.close()
        flash('✅ Visitor updated successfully!')
        return redirect(url_for('visitors'))

    c.execute('SELECT name, visit_date FROM visitors WHERE id = ?', (visitor_id,))
    visitor = c.fetchone()
    conn.close()

    if visitor:
        return render_template('edit_visitor.html', visitor_id=visitor_id, name=visitor[0], visit_date=visitor[1])
    else:
        flash('❌ Visitor not found.')
        return redirect(url_for('visitors'))

@app.route('/add-photo/<int:visitor_id>', methods=['GET', 'POST'])
def add_photo(visitor_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT name, visit_date FROM visitors WHERE id = ?', (visitor_id,))
    visitor = c.fetchone()
    conn.close()

    if not visitor:
        flash('❌ Visitor not found.')
        return redirect(url_for('visitors'))

    name, visit_date = visitor

    if request.method == 'POST':
        photo = request.files['photo']

        if photo:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], photo.filename)
            photo.save(filepath)

            # Face Encoding
            image = face_recognition.load_image_file(filepath)
            encodings = face_recognition.face_encodings(image)

            if len(encodings) == 0:
                flash('❌ No face detected in the uploaded photo.')
                return redirect(url_for('add_photo', visitor_id=visitor_id))

            encoding = encodings[0]

            # Save new face encoding for the same visitor
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute('INSERT INTO visitors (name, visit_date, encoding) VALUES (?, ?, ?)',
                      (name, visit_date, encoding.tobytes()))
            conn.commit()
            conn.close()

            flash('✅ Additional photo added successfully!')
            return redirect(url_for('visitors'))

    return render_template('add_photo.html', visitor_id=visitor_id, name=name)


if __name__ == "__main__":
    app.run(debug=True)
