from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

# admin@gmail.com:pass

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
Bootstrap5(app)

# first a welcome page using index.html > options take attendance button
# add a login manager

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100), nullable=False)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    student_class = db.Column(db.String(100), nullable=False)


with app.app_context():
    db.create_all()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)


# class Attendance(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     email = db.Column(db.String(150), nullable=False)
#     date = db.Column(db.String(150), nullable=False)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


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


@app.route("/view-attendance")
def view_attendance():
    pass


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



if __name__ == "__main__":
    app.run(debug=True)
