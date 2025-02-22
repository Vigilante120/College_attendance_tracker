from main import db, User, app
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()

    new_user = User(email='admin@gmail.com',
                    password=generate_password_hash('pass',
                                                    method='pbkdf2:sha256'))
    db.session.add(new_user)
    db.session.commit()

print('User added successfully')
