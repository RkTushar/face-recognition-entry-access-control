from flask import Flask, render_template, request, redirect, url_for, flash
import os
import sqlite3
import face_recognition
import numpy as np
from datetime import datetime
import csv


app = Flask(__name__)  # Create app object here
app.secret_key = 'supersecretkey'

UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DATABASE = 'database/visitors.db'

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

@app.route('/')
def home():
    return "<h1>Welcome to Museum Face Access System</h1><p><a href='/register'>Register Visitor</a> | <a href='/entry'>Entry Check</a> | <a href='/logs'>View Logs</a></p>"

@app.route('/register', methods=['GET', 'POST'])
def register():
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
                else:
                    flash(f"❌ Access Denied (Wrong Visit Date) for {known_names[best_match_index]}")
            else:
                flash('❌ Face Not Recognized.')

            return redirect(url_for('entry'))

    return render_template('entry.html')

@app.route('/logs')
def logs():
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


if __name__ == "__main__":
    app.run(debug=True)
