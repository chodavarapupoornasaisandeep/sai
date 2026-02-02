import mysql.connector
import random

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="SAI@02042007",      # put your MySQL password if any
    database="placement_portal"
)
cursor = db.cursor()

branches = ['CSE', 'DS', 'ECE', 'EEE']
skills = ['Python', 'Java', 'SQL', 'DBMS', 'AI', 'ML']

for i in range(1, 401):
    cursor.execute(
        "INSERT INTO students (name,email,password,branch,cgpa,skills) VALUES (%s,%s,%s,%s,%s,%s)",
        (
            f'Student{i}',
            f'student{i}@gmail.com',
            '123',
            random.choice(branches),
            round(random.uniform(6.0, 9.5), 2),
            random.choice(skills)
        )
    )

db.commit()
print("400 students inserted successfully")
