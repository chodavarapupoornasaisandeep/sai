from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import os
from werkzeug.utils import secure_filename

# ================= APP CONFIG =================
app = Flask(__name__)
app.secret_key = "super_secret_key_change_later"

# ================= FOLDERS =================
STUDENT_PHOTO_FOLDER = os.path.join('static', 'student_photos')
ADMIN_PHOTO_FOLDER = os.path.join('static', 'admin_photos')
RESUME_FOLDER = os.path.join('static', 'resumes')

os.makedirs(STUDENT_PHOTO_FOLDER, exist_ok=True)
os.makedirs(ADMIN_PHOTO_FOLDER, exist_ok=True)
os.makedirs(RESUME_FOLDER, exist_ok=True)

app.config['STUDENT_PHOTO_FOLDER'] = STUDENT_PHOTO_FOLDER
app.config['ADMIN_PHOTO_FOLDER'] = ADMIN_PHOTO_FOLDER
app.config['RESUME_FOLDER'] = RESUME_FOLDER

# ================= DATABASE =================
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="SAI@02042007",
    database="placement_portal"
)

# ================= HOME =================
@app.route('/')
def home():
    return redirect(url_for('login'))

# ================= STUDENT LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'student_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM students WHERE email=%s AND password=%s",
            (email, password)
        )
        student = cursor.fetchone()
        cursor.close()

        if student:
            session['student_id'] = student['student_id']
            session['student_name'] = student['name']
            return redirect(url_for('dashboard'))

        return render_template('login.html', message="Invalid credentials")

    return render_template('login.html')

# ================= STUDENT DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT name, email, cgpa, photo_path
        FROM students WHERE student_id=%s
    """, (session['student_id'],))
    student = cursor.fetchone()

    cursor.execute("""
        SELECT j.job_id, j.role, j.job_type, j.min_cgpa,
               c.company_name, c.location
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
    """)
    jobs = cursor.fetchall()

    cursor.close()

    return render_template('dashboard.html', student=student, jobs=jobs)

# ================= STUDENT PHOTO UPLOAD =================
@app.route('/student/upload-photo', methods=['POST'])
def student_upload_photo():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    photo = request.files.get('photo')
    if photo and photo.filename.lower().endswith(('.jpg', '.png', '.jpeg')):
        filename = secure_filename(f"student_{session['student_id']}.jpg")
        path = os.path.join(app.config['STUDENT_PHOTO_FOLDER'], filename)
        photo.save(path)

        cursor = db.cursor()
        cursor.execute(
            "UPDATE students SET photo_path=%s WHERE student_id=%s",
            (path, session['student_id'])
        )
        db.commit()
        cursor.close()

    return redirect(url_for('dashboard'))
# ================= STUDENT PROFILE =================
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    cursor = db.cursor(dictionary=True)

    # Upload photo
    if request.method == 'POST' and 'photo' in request.files:
        photo = request.files['photo']
        if photo and photo.filename.lower().endswith(('.jpg', '.png', '.jpeg')):
            filename = secure_filename(f"student_{session['student_id']}.jpg")
            path = os.path.join(app.config['STUDENT_PHOTO_FOLDER'], filename)
            photo.save(path)

            cursor.execute(
                "UPDATE students SET photo_path=%s WHERE student_id=%s",
                (path, session['student_id'])
            )
            db.commit()

    cursor.execute("""
        SELECT name, email, cgpa, photo_path
        FROM students WHERE student_id=%s
    """, (session['student_id'],))
    student = cursor.fetchone()

    cursor.close()

    return render_template('profile.html', student=student)


# ================= MY APPLICATIONS =================
@app.route('/my-applications')
def my_applications():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT j.role, c.company_name, a.status, a.apply_date
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies c ON j.company_id = c.company_id
        WHERE a.student_id=%s
        ORDER BY a.apply_date DESC
    """, (session['student_id'],))

    applications = cursor.fetchall()
    cursor.close()

    return render_template('my_applications.html', applications=applications)


# ================= APPLY JOB =================
@app.route('/apply', methods=['POST'])
def apply_job():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    cursor = db.cursor(dictionary=True, buffered=True)
    cursor.execute(
        "SELECT * FROM applications WHERE student_id=%s AND job_id=%s",
        (session['student_id'], request.form['job_id'])
    )

    if cursor.fetchone():
        cursor.close()
        return redirect(url_for('dashboard'))

    cursor.execute("""
        INSERT INTO applications (student_id, job_id, status, apply_date)
        VALUES (%s,%s,'Applied',CURDATE())
    """, (session['student_id'], request.form['job_id']))

    db.commit()
    cursor.close()
    return redirect(url_for('dashboard'))

# ================= ADMIN LOGIN =================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, c.company_name
            FROM admin a
            LEFT JOIN companies c ON a.company_id = c.company_id
            WHERE a.username=%s AND a.password=%s
        """, (username, password))

        admin = cursor.fetchone()
        cursor.close()

        if not admin:
            return render_template('admin_login.html', message="Invalid credentials")

        session['admin_id'] = admin['admin_id']
        session['admin_name'] = admin['username']
        session['company_id'] = admin['company_id']
        session['company_name'] = admin['company_name']
        session['admin_role'] = admin['role']
        session['admin_photo'] = admin['photo_path']

        return redirect(url_for('admin_dashboard'))

    return render_template('admin_login.html')
# ================= ADMIN DASHBOARD =================
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    cursor = db.cursor(dictionary=True)

    # Fetch admin info
    cursor.execute("""
        SELECT username, role, photo_path
        FROM admin
        WHERE admin_id = %s
    """, (session['admin_id'],))
    admin = cursor.fetchone()

    # 🔒 FETCH ONLY THIS ADMIN'S COMPANY APPLICATIONS
    cursor.execute("""
        SELECT 
            a.application_id,
            a.student_id,
            s.name AS student_name,
            s.email AS student_email,
            j.role,
            a.status
        FROM applications a
        JOIN students s ON a.student_id = s.student_id
        JOIN jobs j ON a.job_id = j.job_id
        WHERE j.company_id = %s
        ORDER BY a.application_id DESC
    """, (session['company_id'],))

    applications = cursor.fetchall()
    cursor.close()

    return render_template(
        'admin_dashboard.html',
        admin=admin,
        admin_name=admin['username'],
        admin_role=admin['role'],
        company_name=session['company_name'],
        applications=applications
    )

# ================= ADMIN PROFILE =================
@app.route('/admin/profile')
def admin_profile():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT username, role, photo_path
        FROM admin
        WHERE admin_id = %s
    """, (session['admin_id'],))
    admin = cursor.fetchone()
    cursor.close()

    return render_template(
        'admin_profile.html',
        admin=admin,
        company_name=session.get('company_name')
    )

# ================= ADMIN PHOTO UPLOAD =================
@app.route('/admin/upload-photo', methods=['POST'])
def admin_upload_photo():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    photo = request.files.get('photo')
    if photo and photo.filename.lower().endswith(('.jpg', '.png', '.jpeg')):
        filename = secure_filename(f"admin_{session['admin_id']}.jpg")
        path = os.path.join(app.config['ADMIN_PHOTO_FOLDER'], filename)
        photo.save(path)

        cursor = db.cursor()
        cursor.execute(
            "UPDATE admin SET photo_path=%s WHERE admin_id=%s",
            (path, session['admin_id'])
        )
        db.commit()
        cursor.close()

        session['admin_photo'] = path

    return redirect(url_for('admin_dashboard'))

# ================= UPDATE STATUS =================
@app.route('/admin/update-status', methods=['POST'])
def update_status():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    cursor = db.cursor()
    cursor.execute(
        "UPDATE applications SET status=%s WHERE application_id=%s",
        (request.form['status'], request.form['app_id'])
    )
    db.commit()
    cursor.close()

    return redirect(url_for('admin_dashboard'))

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)
