from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from .models import User
from . import db
from datetime import datetime, timedelta
from .models import Book, IssuedBook, Section,Feedback,BookRequest
import smtplib
from email.mime.text import MIMEText
from config import MAIL_USERNAME, MAIL_PASSWORD, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_RECEIVER

main = Blueprint('main', __name__)

# Landing page
@main.route('/')
def home():
    if 'user_id' in session:
        if session.get('role') == 'user':
            return redirect(url_for('main.user_dashboard'))
        elif session.get('role') == 'librarian':
            return redirect(url_for('main.librarian_dashboard'))
    return render_template('home.html')


# Register page for user
@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already taken.", "info")
            return redirect(url_for('main.register'))
        
        # Create new user
        new_user = User(username=username, password=password, role='user')
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please login.", "info")
        return redirect(url_for('main.user_login'))

    return render_template('register.html')

# User login
@main.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password, role='user').first()
        if user:
            session['user_id'] = user.id
            session['role'] = 'user'
            session['username'] = user.username 
            flash(f"Welcome back, {user.username}!", "info")


            return redirect(url_for('main.user_dashboard'))
        else:
            flash("Invalid credentials", "info")
    return render_template('user_login.html')

@main.route('/logout')
def logout():
    session.clear()  # ✅ Clears everything in the session
    flash('You have been logged out.', "success")
    return redirect(url_for('main.home'))


# Librarian login
@main.route('/librarian_login', methods=['GET', 'POST'])
def librarian_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        librarian = User.query.filter_by(username=username, password=password, role='librarian').first()
        if librarian:
            session['user_id'] = librarian.id
            session['role'] = 'librarian'
            session['username'] = librarian.username
            flash(f"Welcome back, {librarian.username}!", "success")
            return redirect(url_for('main.librarian_dashboard'))
        else:
            flash("Invalid credentials", "info")
    return render_template('librarian_login.html')

@main.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('main.user_login'))

    user_id = session['user_id']
    issued_books = IssuedBook.query.filter_by(user_id=user_id).all()
    all_sections = Section.query.all()

    # Filters (optional search logic from earlier)
    search = request.args.get('search', '').strip().lower()
    section_id = request.args.get('section', '')
    author = request.args.get('author', '').strip().lower()

    query = Book.query
    if search:
        query = query.filter(Book.name.ilike(f"%{search}%"))
    if author:
        query = query.filter(Book.author.ilike(f"%{author}%"))
    if section_id:
        try:
            query = query.filter(Book.section_id == int(section_id))
        except ValueError:
            pass

    books = query.all()

    # ✅ Get all requests made by the current user
    user_requests = BookRequest.query.filter_by(user_id=user_id).all()
    return render_template(
        'user_dashboard.html',
        books=books,
        issued_books=issued_books,
        all_sections=all_sections,
        user_requests=user_requests
    )


@main.route('/librarian_dashboard')
def librarian_dashboard():
    if 'user_id' not in session or session.get('role') != 'librarian':
        return redirect(url_for('main.librarian_login'))

    books = Book.query.all()
    sections = Section.query.all()
    return render_template('librarian_dashboard.html', books=books, sections=sections)

# @main.route('/request_book/<int:book_id>', methods=['POST'])
# def request_book(book_id):
#     if 'user_id' not in session or session.get('role') != 'user':
#         return redirect(url_for('main.user_login'))

#     user_id = session['user_id']

#     # Check limit
#     current_issued = IssuedBook.query.filter_by(user_id=user_id).count()
#     if current_issued >= 5:
#         flash("Limit reached: you can only request 5 books.")
#         return redirect(url_for('main.user_dashboard'))

#     # Check if already issued
#     already_issued = IssuedBook.query.filter_by(user_id=user_id, book_id=book_id).first()
#     if already_issued:
#         flash("You have already requested this book.")
#         return redirect(url_for('main.user_dashboard'))

#     # Issue the book
#     new_issue = IssuedBook(
#         user_id=user_id,
#         book_id=book_id,
#         date_issued=datetime.utcnow(),
#         return_date=datetime.utcnow() + timedelta(days=7)
#     )
#     db.session.add(new_issue)
#     db.session.commit()
#     flash("Book issued successfully.")
#     return redirect(url_for('main.user_dashboard'))
@main.route('/request_book/<int:book_id>', methods=['POST'])
def request_book(book_id):
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('main.user_login'))

    user_id = session['user_id']

    # Check if already requested
    existing_request = BookRequest.query.filter_by(user_id=user_id, book_id=book_id).first()
    if existing_request:
        flash(f"You already requested this book. Status: {existing_request.status}", "info")
        return redirect(url_for('main.user_dashboard'))

    request_entry = BookRequest(user_id=user_id, book_id=book_id, status='pending')
    db.session.add(request_entry)
    db.session.commit()

    flash("Book request submitted for approval.", "info")
    return redirect(url_for('main.user_dashboard'))


@main.route('/return_book/<int:book_id>', methods=['POST'])
def return_book(book_id):
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('main.user_login'))

    user_id = session['user_id']
    issued = IssuedBook.query.filter_by(user_id=user_id, book_id=book_id).first()
    if issued:
        db.session.delete(issued)
        db.session.commit()
        flash("Book returned successfully.", "success")
    return redirect(url_for('main.user_dashboard'))
@main.route('/add_section', methods=['POST'])
def add_section():
    if 'user_id' not in session or session.get('role') != 'librarian':
        return redirect(url_for('main.librarian_login'))

    name = request.form['name']
    desc = request.form.get('description', '')
    new_sec = Section(name=name, description=desc)
    db.session.add(new_sec)
    db.session.commit()
    flash("Section added.", "success")
    return redirect(url_for('main.librarian_dashboard'))

@main.route('/edit_section/<int:section_id>', methods=['GET', 'POST'])
def edit_section(section_id):
    if 'user_id' not in session or session.get('role') != 'librarian':
        return redirect(url_for('main.librarian_login'))

    section = Section.query.get_or_404(section_id)

    if request.method == 'POST':
        new_name = request.form['name']
        section.name = new_name
        db.session.commit()
        flash('Section updated successfully!', "success")
        return redirect(url_for('main.librarian_dashboard'))

    return render_template('edit_section.html', section=section)


@main.route('/delete_section/<int:section_id>', methods=['POST'])
def delete_section(section_id):
    if 'user_id' not in session or session.get('role') != 'librarian':
        return redirect(url_for('main.librarian_login'))

    section = Section.query.get_or_404(section_id)

    # ❌ Prevent deletion if the section still contains books
    if section.books:
        flash("❌ Cannot delete section — books are still assigned to it. Please reassign or delete those books first.", "danger")
        return redirect(url_for('main.librarian_dashboard'))

    db.session.delete(section)
    db.session.commit()
    flash('✅ Section deleted successfully.', "success")
    return redirect(url_for('main.librarian_dashboard'))



@main.route('/add_book', methods=['POST'])
def add_book():
    if 'user_id' not in session or session.get('role') != 'librarian':
        return redirect(url_for('main.librarian_login'))

    name = request.form['name']
    author = request.form.get('author', '')
    content = request.form['content']
    section_id = request.form.get('section_id')

    new_book = Book(name=name, author=author, content=content, section_id=section_id)
    db.session.add(new_book)
    db.session.commit()
    flash("Book added.", "success")
    return redirect(url_for('main.librarian_dashboard'))

@main.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    if 'user_id' not in session or session.get('role') != 'librarian':
        return redirect(url_for('main.librarian_login'))

    book = Book.query.get_or_404(book_id)
    sections = Section.query.all()

    if request.method == 'POST':
        book.name = request.form['name']
        book.author = request.form.get('author', '')
        book.content = request.form['content']
        book.section_id = request.form['section_id']
        db.session.commit()
        flash("Book updated successfully.", "success")
        return redirect(url_for('main.librarian_dashboard'))

    return render_template('edit_book.html', book=book, sections=sections)
@main.route('/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    if 'user_id' not in session or session.get('role') != 'librarian':
        return redirect(url_for('main.librarian_login'))

    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash("Book deleted.", "success")
    return redirect(url_for('main.librarian_dashboard'))

@main.route('/librarian_stats')
def librarian_stats():
    if 'user_id' not in session or session.get('role') != 'librarian':
        return redirect(url_for('main.librarian_login'))

    # Pie chart: Books per section
    section_counts = db.session.query(Section.name, db.func.count(Book.id)) \
                        .join(Book).group_by(Section.id).all()

    section_data = {
        'labels': [sec[0] for sec in section_counts],
        'data': [sec[1] for sec in section_counts]
    }

    # Bar chart: Books issued per user
    issued_counts = db.session.query(User.username, db.func.count(IssuedBook.id)) \
                        .join(IssuedBook).group_by(User.id).all()

    issued_data = {
        'labels': [user[0] for user in issued_counts],
        'data': [user[1] for user in issued_counts]
    }
    print("Section Data:", section_data)
    print("Issued Data:", issued_data)


    return render_template('librarian_stats.html', section_data=section_data, issued_data=issued_data)

@main.route('/user_stats')
def user_stats():
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('main.user_login'))

    user_id = session['user_id']

    # Count how many books user has read per section
    section_data_query = db.session.query(Section.name, db.func.count(IssuedBook.id)) \
    .select_from(Book) \
    .join(Section, Book.section_id == Section.id) \
    .join(IssuedBook, IssuedBook.book_id == Book.id) \
    .filter(IssuedBook.user_id == user_id) \
    .group_by(Section.name).all()


    section_data = {
        'labels': [row[0] for row in section_data_query],
        'data': [row[1] for row in section_data_query]
    }

    return render_template('user_stats.html', section_data=section_data)

@main.route('/submit_feedback/<int:book_id>', methods=['POST'])
def submit_feedback(book_id):
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('main.user_login'))

    user_id = session['user_id']
    content = request.form.get('feedback')

    if content:
        feedback = Feedback(user_id=user_id, book_id=book_id, content=content)
        db.session.add(feedback)
        db.session.commit()
        flash("Feedback submitted!", "success")
    else:
        flash("Feedback cannot be empty.","info")

    return redirect(url_for('main.user_dashboard'))

@main.route('/book_requests')
def book_requests():
    if 'user_id' not in session or session.get('role') != 'librarian':
        return redirect(url_for('main.librarian_login'))

    pending = BookRequest.query.filter_by(status='pending').all()
    return render_template('book_requests.html', requests=pending)


@main.route('/process_request/<int:request_id>/<action>', methods=['POST'])
def process_request(request_id, action):
    if 'user_id' not in session or session.get('role') != 'librarian':
        return redirect(url_for('main.librarian_login'))

    req = BookRequest.query.get_or_404(request_id)

    if action == 'approve':
        # Create IssuedBook record
        issued = IssuedBook(
            user_id=req.user_id,
            book_id=req.book_id,
            date_issued=datetime.utcnow(),
            return_date=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(issued)
        req.status = 'approved'
        flash(f"Approved and issued: {req.book.name}", "success")
    elif action == 'reject':
        req.status = 'rejected'
        flash(f"Rejected request for: {req.book.name}", "info")

    db.session.commit()
    return redirect(url_for('main.book_requests'))

@main.route('/cancel_request/<int:request_id>', methods=['POST'])
def cancel_request(request_id):
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('main.user_login'))

    req = BookRequest.query.get_or_404(request_id)

    # Only allow canceling if the request belongs to the user and is pending
    if req.user_id != session['user_id']:
        flash("Unauthorized request.", "danger")
    elif req.status != 'pending':
        flash("Only pending requests can be canceled.", "info")
    else:
        db.session.delete(req)
        db.session.commit()
        flash("Request canceled.", "info")

    return redirect(url_for('main.user_dashboard'))

@main.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('main.home'))

    user = User.query.get_or_404(session['user_id'])

    if request.method == 'POST':
        user.full_name = request.form['full_name']
        user.gender = request.form['gender']
        user.email = request.form['email']
        user.phone = request.form['phone']
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for('main.profile'))

    return render_template('profile.html', user=user)

@main.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('main.home'))

    user_id = session['user_id']
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        current = request.form['current_password']
        new = request.form['new_password']

        if user.password != current:
            flash("Current password is incorrect.", "danger")
        else:
            user.password = new
            db.session.commit()
            flash("Password changed successfully.", "success")
            return redirect(url_for('main.profile'))

    return render_template('change_password.html')
    


@main.route('/contact', methods=['POST'])
def contact():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']

    # ✉️ Email to Admin
    admin_subject = f"New Support Message from {name}"
    admin_body = f"Sender: {name}\nEmail: {email}\n\nMessage:\n{message}"

    admin_msg = MIMEText(admin_body)
    admin_msg['Subject'] = admin_subject
    admin_msg['From'] = MAIL_USERNAME
    admin_msg['To'] = MAIL_RECEIVER

    # 📩 Email to User
    user_subject = "📬 MyLibrary Support — We've received your message!"
    user_body = f"""
Hi {name},

Thank you for reaching out to MyLibrary Support. We've received your message and will get back to you as soon as possible!

📝 Here’s a copy of what you sent us:
-----------------------------------
{message}
-----------------------------------

Regards,  
📚 MyLibrary Team
"""

    user_msg = MIMEText(user_body)
    user_msg['Subject'] = user_subject
    user_msg['From'] = MAIL_USERNAME
    user_msg['To'] = email

    try:
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
        if MAIL_USE_TLS:
            server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)

        # Send both emails
        server.sendmail(MAIL_USERNAME, MAIL_RECEIVER, admin_msg.as_string())
        server.sendmail(MAIL_USERNAME, email, user_msg.as_string())
        server.quit()

        flash("✅ Message sent! We've emailed you a confirmation too.", "success")

    except Exception as e:
        print("Mail error:", e)
        flash("❌ Message failed to send. Please try again later.", "danger")

    return redirect(url_for('main.home'))

