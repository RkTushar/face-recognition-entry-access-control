import cv2
import face_recognition
import sqlite3
import numpy as np
import csv
from datetime import datetime

def load_registered_visitors():
    conn = sqlite3.connect('database/visitors.db')
    c = conn.cursor()
    c.execute("SELECT name, visit_date, encoding FROM visitors")
    data = c.fetchall()
    conn.close()

    visitors = []
    for name, visit_date, encoding_blob in data:
        encoding = np.frombuffer(encoding_blob, dtype=np.float64)
        visitors.append((name, visit_date, encoding))
    return visitors

def log_access(name, status):
    log_file = 'logs/access_log.csv'
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([name, now, status])

def recognize_and_check():
    print("[INFO] Loading registered visitors...")
    visitors = load_registered_visitors()
    if not visitors:
        print("[ERROR] No registered visitors found.")
        return

    known_encodings = [v[2] for v in visitors]
    known_names = [v[0] for v in visitors]
    known_dates = [v[1] for v in visitors]

    print("[INFO] Starting webcam for visitor verification...")
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to grab frame from webcam.")
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for face_encoding, face_location in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(known_encodings, face_encoding)
            name = "Unknown"
            status = "Access Denied"

            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            best_match_index = np.argmin(face_distances) if len(face_distances) > 0 else None

            if best_match_index is not None and matches[best_match_index]:
                today_date = datetime.now().strftime("%Y-%m-%d")
                if known_dates[best_match_index] == today_date:
                    name = known_names[best_match_index]
                    status = "Access Granted ✅"
                else:
                    name = known_names[best_match_index]
                    status = "Access Denied (Wrong Date)"

            top, right, bottom, left = face_location
            color = (0, 255, 0) if "Granted" in status else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.putText(frame, f"{name}: {status}", (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            log_access(name, status)

        cv2.imshow('Museum Entry Access', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    recognize_and_check()
