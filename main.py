from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap5
from datetime import datetime,date
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.types import Enum
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
load_dotenv()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', '').replace(
    'postgres://', 'postgresql://', 1  # Required for newer SQLAlchemy versions
)

db = SQLAlchemy(app)
Bootstrap5(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# User model for authentication
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)


# Student model
class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    student_class = db.Column(db.String(100), nullable=False)


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    roll_no = db.Column(db.String(50), db.ForeignKey('student.roll_no'), nullable=False)
    status = db.Column(Enum('Present', 'Absent', 'Late', name='attendance_status'), nullable=False, default='Absent')
    # attendance table is linked to Student with the roll number as foreign key
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    __table_args__ = (db.UniqueConstraint('roll_no', 'date', name='unique_roll_date'),)


# Teacher model (optional for future use)
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100), nullable=False)


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin'))
        else:
            flash('Login Failed. PLease Check your email and password')
    return render_template('login.html')


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/view-student-details")
@login_required
def view_student_details():
    students = Student.query.all()
    return render_template("view_students.html", students=students)


@app.route("/admin")
@login_required
def admin():
    return render_template("admin.html")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('home'))


@app.route('/add_teacher', methods=['GET', 'POST'])
@login_required
def add_teacher():
    if request.method == 'POST':
        name = request.form.get('name')
        subject = request.form.get('subject')
        new_teacher = Teacher(name=name, subject=subject)
        db.session.add(new_teacher)
        db.session.commit()
        flash('Teacher added successfully')
        return redirect(url_for('admin'))
    return render_template('add_teacher.html')


@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        student_class = request.form.get('student_class')

        # Validate and convert roll number
        try:
            roll_no = int(request.form.get('roll_no'))
        except ValueError:
            flash('Roll number must be a valid integer.')
            return redirect(url_for('add_student'))

        # Check for duplicate roll number or email
        existing_student = Student.query.filter(
            (Student.roll_no == roll_no) | (Student.email == email)
        ).first()
        if existing_student:
            flash('A student with this roll number or email already exists.')
            return redirect(url_for('add_student'))

        # Add new student to database
        try:
            new_student = Student(name=name, email=email, student_class=student_class, roll_no=roll_no)
            db.session.add(new_student)
            db.session.commit()
            flash('Student added successfully.')
        except IntegrityError as e:
            db.session.rollback()
            flash(f'Failed to add student: {str(e)}')

        return redirect(url_for('admin'))

    return render_template('add_student.html')


@app.route('/view_students', methods=["GET"])
@login_required
def view_students():
    students = Student.query.all()
    return render_template('view_students.html', students=students)


@app.route('/view_teachers', methods=["GET"])
@login_required
def view_teachers():
    teachers = Teacher.query.all()
    return render_template("view_teachers.html", teachers=teachers)


@app.route("/take_attendance", methods=["GET", "POST"])
@login_required
def take_attendance():
    if request.method == "GET":
        students = Student.query.all()
        today_date = date.today()
        return render_template("take_attendance.html", students=students, today_date=today_date)

    elif request.method == "POST":
        try:
            # Process attendance submission
            attendance_data = request.form
            attendance_date = datetime.strptime(attendance_data["date"], "%Y-%m-%d").date()

            for roll_no, status in attendance_data.items():
                if roll_no != "date":  # Skip the date field
                    existing_record = Attendance.query.filter_by(roll_no=roll_no, date=attendance_date).first()
                    if existing_record:
                        existing_record.status = status
                    else:
                        new_record = Attendance(
                            roll_no=roll_no,
                            date=attendance_date,
                            status=status
                        )
                        db.session.add(new_record)

            db.session.commit()
            flash("Attendance successfully recorded!", "success")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")

        return redirect(url_for("admin"))


@app.route("/view_attendance", methods=["GET", "POST"])
@login_required
def view_attendance():
    if request.method == "GET":
        # Fetch distinct dates with recorded attendance
        available_dates = db.session.query(Attendance.date).distinct().all()
        # Convert tuples to a list of date strings
        available_dates = [record.date.strftime("%Y-%m-%d") for record in available_dates]

        return render_template("view_attendance.html", available_dates=available_dates)

    elif request.method == "POST":
        selected_date = request.form.get("date")  # Get selected date from form
        try:
            # Convert the date string to a Python date object
            selected_date_obj = datetime.strptime(selected_date, "%Y-%m-%d").date()

            # Query attendance records for the selected date
            attendance_records = db.session.query(Attendance, Student).join(
                Student, Attendance.roll_no == Student.roll_no
            ).filter(Attendance.date == selected_date_obj).all()

            return render_template(
                "view_attendance.html",
                available_dates=[record.date.strftime("%Y-%m-%d") for record in db.session.query(Attendance.date).distinct().all()],
                attendance_records=[
                    {"roll_no": record.Attendance.roll_no,
                     "name": record.Student.name,
                     "status": record.Attendance.status}
                    for record in attendance_records
                ],
                selected_date=selected_date_obj,
            )

        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
            return redirect(url_for("view_attendance"))


if __name__ == "__main__":
    app.run(debug=True)
