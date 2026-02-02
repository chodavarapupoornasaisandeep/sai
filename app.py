from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import os
from werkzeug.utils import secure_filename

# ================= APP CONFIG =================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret")


UPLOAD_FOLDER = os.path.join('static', 'resumes')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= DATABASE =================
db = mysql.connector.connect(
    host=os.getenv("MYSQLHOST"),
    user=os.getenv("MYSQLUSER"),
    password=os.getenv("MYSQLPASSWORD"),
    database=os.getenv("MYSQLDATABASE"),
    port=int(os.getenv("MYSQLPORT", 3306)),
    auth_plugin="mysql_native_password"
)

cursor = db.cursor(dictionary=True)



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
        cursor.execute(
            "SELECT student_id, name FROM students WHERE email=%s AND password=%s",
            (request.form['email'], request.form['password'])
        )
        student = cursor.fetchone()

        if student:
            session['student_id'] = student['student_id']
            session['student_name'] = student['name']
            return redirect(url_for('dashboard'))

        return render_template('login.html', message="Invalid email or password")

    return render_template('login.html')

# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        cursor.execute(
            """
            INSERT INTO students (name, email, password, branch, cgpa)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (
                request.form['name'],
                request.form['email'],
                request.form['password'],
                request.form['branch'],
                request.form['cgpa']
            )
        )
        db.commit()
        return render_template('message.html',
                               message="Registration successful! Please login.",
                               back_url="/login")

    return render_template('register.html')

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    cursor.execute(
        "SELECT student_id, name, email, cgpa FROM students WHERE student_id=%s",
        (session['student_id'],)
    )
    student = cursor.fetchone()

    cursor.execute("""
        SELECT j.job_id, j.role, j.job_type, j.min_cgpa,
               c.company_name, c.location
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
    """)
    jobs = cursor.fetchall()

    return render_template('dashboard.html', student=student, jobs=jobs)

# ================= APPLY JOB =================
@app.route('/apply', methods=['POST'])
def apply_job():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    job_id = request.form['job_id']
    student_id = session['student_id']

    cursor.execute(
        "SELECT 1 FROM applications WHERE student_id=%s AND job_id=%s",
        (student_id, job_id)
    )
    if cursor.fetchone():
        return render_template('message.html',
                               message="You already applied for this job.",
                               back_url="/dashboard")

    cursor.execute(
        """
        INSERT INTO applications (student_id, job_id, status, apply_date)
        VALUES (%s,%s,'Applied',CURDATE())
        """,
        (student_id, job_id)
    )
    db.commit()

    return render_template('message.html',
                           message="Job applied successfully!",
                           back_url="/dashboard")

# ================= PROFILE (RESUME + PROJECTS) =================
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    # Resume upload
    if request.method == 'POST' and 'resume' in request.files:
        file = request.files['resume']
        if file and file.filename.lower().endswith('.pdf'):
            filename = secure_filename(f"student_{session['student_id']}.pdf")
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)

            cursor.execute(
                "UPDATE students SET resume_path=%s WHERE student_id=%s",
                (path, session['student_id'])
            )
            db.commit()

    cursor.execute(
        "SELECT name, email, cgpa, resume_path FROM students WHERE student_id=%s",
        (session['student_id'],)
    )
    student = cursor.fetchone()

    cursor.execute(
        "SELECT title, description, project_link FROM projects WHERE student_id=%s",
        (session['student_id'],)
    )
    projects = cursor.fetchall()

    return render_template('profile.html', student=student, projects=projects)

# ================= ADD PROJECT =================
@app.route('/add-project', methods=['GET', 'POST'])
def add_project():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        cursor.execute(
            """
            INSERT INTO projects (student_id, title, description, project_link)
            VALUES (%s,%s,%s,%s)
            """,
            (
                session['student_id'],
                request.form['title'],
                request.form['description'],
                request.form['link']
            )
        )
        db.commit()
        return redirect(url_for('profile'))

    return render_template('add_project.html')

# ================= MY APPLICATIONS =================
@app.route('/my-applications')
def my_applications():
    if 'student_id' not in session:
        return redirect(url_for('login'))

    cursor.execute("""
        SELECT a.application_id, j.role, c.company_name,
               a.status, a.apply_date
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies c ON j.company_id = c.company_id
        WHERE a.student_id=%s
        ORDER BY a.apply_date DESC
    """, (session['student_id'],))

    return render_template('my_applications.html',
                           applications=cursor.fetchall())

# ================= ADMIN LOGIN =================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        cursor.execute(
            "SELECT admin_id FROM admin WHERE username=%s AND password=%s",
            (request.form['username'], request.form['password'])
        )
        admin = cursor.fetchone()

        if admin:
            session['admin_id'] = admin['admin_id']
            return redirect(url_for('admin_dashboard'))

        return render_template('admin_login.html', message="Invalid credentials")

    return render_template('admin_login.html')

# ================= ADMIN DASHBOARD =================
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    cursor.execute("""
        SELECT a.application_id, a.student_id,
               s.name AS student_name, s.email, s.resume_path,
               j.role, c.company_name, a.status
        FROM applications a
        JOIN students s ON a.student_id = s.student_id
        JOIN jobs j ON a.job_id = j.job_id
        JOIN companies c ON j.company_id = c.company_id
        ORDER BY a.application_id DESC
    """)
    applications = cursor.fetchall()

    return render_template('admin_dashboard.html', applications=applications)

# ================= ADMIN VIEW STUDENT PROFILE =================
@app.route('/admin/student/<int:student_id>')
def admin_view_student(student_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    cursor.execute("""
        SELECT student_id, name, email, branch, cgpa, resume_path
        FROM students WHERE student_id=%s
    """, (student_id,))
    student = cursor.fetchone()

    cursor.execute("""
        SELECT title, description, project_link, created_at
        FROM projects
        WHERE student_id=%s
        ORDER BY created_at DESC
    """, (student_id,))
    projects = cursor.fetchall()

    return render_template('admin_student_profile.html',
                           student=student,
                           projects=projects)

# ================= UPDATE STATUS =================
@app.route('/admin/update-status', methods=['POST'])
def update_status():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    cursor.execute(
        "UPDATE applications SET status=%s WHERE application_id=%s",
        (request.form['status'], request.form['app_id'])
    )
    db.commit()

    return redirect(url_for('admin_dashboard'))

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ================= RUN =================
if __name__ == "__main__":
    app.run()
