from flask import Flask, render_template, request, redirect, url_for, flash
import os
import sqlite3
import face_recognition
from datetime import datetime

app = Flask(__name__)
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

            # Save to database
            save_visitor_to_db(visitor_name, visit_date, encoding)

            flash(f'✅ Visitor {visitor_name} registered successfully!')
        else:
            flash('❌ No photo uploaded.')

        return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/entry')
def entry():
    return "<h2>Entry Check (Coming Soon)</h2>"

@app.route('/logs')
def logs():
    return "<h2>Access Logs (Coming Soon)</h2>"

if __name__ == "__main__":
    app.run(debug=True)
