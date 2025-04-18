from . import db
from datetime import datetime, timedelta

# Role-based User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'librarian'

    full_name = db.Column(db.String(150))
    gender = db.Column(db.String(10))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(15))

    issued_books = db.relationship('IssuedBook', backref='user', lazy=True)
    feedbacks = db.relationship('Feedback', backref='user', lazy=True)

# Sections (like genres or categories)
class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    books = db.relationship('Book', backref='section', lazy=True)

# Books in the library
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100))
    content = db.Column(db.Text, nullable=False)  # this will be just plain text or a path to PDF
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=True)
    issued_books = db.relationship('IssuedBook', backref='book', lazy=True)
    feedbacks = db.relationship('Feedback', backref='book', lazy=True)
    pdf_path = db.Column(db.String(300))       # Path to uploaded PDF
    cover_image = db.Column(db.String(300))    # Path to uploaded cover image

# Tracks which user has which book, and how long
class IssuedBook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    date_issued = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))  # default 7 days

# Feedback by users
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)

class BookRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending / approved / rejected
    date_requested = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='requests')
    book = db.relationship('Book', backref='requests')
