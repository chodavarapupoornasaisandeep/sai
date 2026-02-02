import mysql.connector
import random

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="SAI@02042007",
    database="placement_portal"
)

cursor = db.cursor()

# Fetch valid student IDs
cursor.execute("SELECT student_id FROM students")
students = [row[0] for row in cursor.fetchall()]

# Fetch valid job IDs
cursor.execute("SELECT job_id FROM jobs")
jobs = [row[0] for row in cursor.fetchall()]

print("Students found:", len(students))
print("Jobs found:", len(jobs))

# Safety check
if not students or not jobs:
    print("ERROR: Students or Jobs table is empty")
    exit()

for _ in range(800):
    cursor.execute(
        """
        INSERT INTO applications (student_id, job_id, status, apply_date)
        VALUES (%s, %s, %s, CURDATE())
        """,
        (
            random.choice(students),
            random.choice(jobs),
            random.choice(['Applied', 'Shortlisted', 'Rejected'])
        )
    )

db.commit()
print("800 applications inserted successfully")
