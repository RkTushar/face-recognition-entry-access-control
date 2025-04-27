import cv2
import face_recognition
import os
import sqlite3
from datetime import datetime

def capture_from_webcam(visitor_name, visit_date):
    cap = cv2.VideoCapture(0)
    print("[INFO] Starting webcam. Please look at the camera...")
    ret, frame = cap.read()
    if ret:
        img_path = f'images/{visitor_name}_{visit_date}.jpg'
        cv2.imwrite(img_path, frame)
        print(f"[INFO] Image captured and saved as {img_path}")
    else:
        print("[ERROR] Failed to capture image from webcam.")
        img_path = None
    cap.release()
    return img_path

def upload_image_file():
    img_path = input("Enter the path of the visitor's image file: ")
    if os.path.exists(img_path):
        print(f"[INFO] Using uploaded image: {img_path}")
        return img_path
    else:
        print("[ERROR] Image file not found!")
        return None

def register_visitor(visitor_name, visit_date, img_path):
    image = face_recognition.load_image_file(img_path)
    encodings = face_recognition.face_encodings(image)
    if len(encodings) == 0:
        print("[ERROR] No face found in the image.")
        return
    encoding = encodings[0]
    
    # Connect to SQLite database
    conn = sqlite3.connect('database/visitors.db')
    c = conn.cursor()

    # Create table if it does not exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            visit_date TEXT,
            encoding BLOB
        )
    ''')

    # Insert visitor data
    c.execute('INSERT INTO visitors (name, visit_date, encoding) VALUES (?, ?, ?)',
              (visitor_name, visit_date, encoding.tobytes()))
    
    conn.commit()
    conn.close()

    print(f"[SUCCESS] Visitor '{visitor_name}' registered successfully for {visit_date}!")

def main():
    print("------ Museum Visitor Registration ------")
    visitor_name = input("Enter visitor's full name: ")
    visit_date = input("Enter visit date (YYYY-MM-DD): ")
    
    print("\nChoose registration method:")
    print("1. Capture photo from webcam")
    print("2. Upload an existing image file")
    choice = input("Enter choice (1 or 2): ")

    img_path = None
    if choice == "1":
        img_path = capture_from_webcam(visitor_name, visit_date)
    elif choice == "2":
        img_path = upload_image_file()
    else:
        print("[ERROR] Invalid choice.")
    
    if img_path:
        register_visitor(visitor_name, visit_date, img_path)
    else:
        print("[ERROR] Registration failed.")

if __name__ == "__main__":
    main()
