from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key for production


# Predefined admin credentials
PREDEFINED_ADMINS = {
    'admin1@gmail.com': 'admin@321',
    'admin2@gmail.com': 'admin@321',
}

# Database connection function
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/insure')
def insure():
    return render_template('insure.html')

# Home route
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        middle_name = request.form.get('middle_name', '')
        last_name = request.form['last_name']
        email = request.form['email']
        account_type = request.form['account_type'].lower()  # Normalize to lowercase
        password = request.form['password']

        conn = get_db_connection()

        try:
            if account_type == 'advocate':
                conn.execute(
                    'INSERT INTO advocate (first_name, middle_name, last_name, email, account_type, password) VALUES (?, ?, ?, ?, ?, ?)',
                    (first_name, middle_name, last_name, email, account_type, password)
                )
                conn.commit()
                flash('Sign up successful! You can log in now.')
                return redirect(url_for('login'))

            elif account_type == 'client':
                conn.execute(
                    'INSERT INTO client (first_name, middle_name, last_name, email, account_type, password) VALUES (?, ?, ?, ?, ?, ?)',
                    (first_name, middle_name, last_name, email, account_type, password)
                )
                conn.commit()
                flash('Sign up successful! You can log in now.')
                return redirect(url_for('login'))

            else:
                flash('Invalid account type.')
                return redirect(url_for('signup'))

        except sqlite3.IntegrityError:
            flash('Email already exists!')
        finally:
            conn.close()

    return render_template('signup.html')

@app.route('/advocate_dashboard')
def advocate_dashboard():
    if 'user_email' not in session or session.get('user_type') != 'advocate':
        flash('Please log in as an advocate to access this page.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    advocate = conn.execute('SELECT * FROM advocate WHERE email = ?', (session['user_email'],)).fetchone()
    
    # Modify this query to select post_id as well
    posts = conn.execute('''
        SELECT client_posts.post_id, client_posts.case_title, client_posts.case_description,
               client_posts.reply_text, client.first_name, client.last_name
        FROM client_posts
        JOIN client ON client_posts.client_id = client.client_id
    ''').fetchall()
    conn.close()

    return render_template('advocate_dashboard.html', advocate=advocate, posts=posts)


@app.route('/edit_adv', methods=['GET', 'POST'])
def edit_adv():
    if 'user_email' not in session or session.get('user_type') != 'advocate':
        flash('Please log in to access this page.')
        return redirect(url_for('login'))

    user_email = session['user_email']

    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address1 = request.form['address1']
        address2 = request.form['address2']
        city = request.form['city']
        pincode = request.form['pincode']
        specialization = request.form['specialization']

        conn.execute('''
            UPDATE advocate
            SET first_name = ?, phone = ?, address_line = ?, address_line2 = ?, city = ?, pincode = ?, specialization = ?
            WHERE email = ?
        ''', (name, phone, address1, address2, city, pincode, specialization, user_email))

        conn.commit()
        conn.close()

        flash('Profile updated successfully.')
        return redirect(url_for('advocate_dashboard'))

    advocate = conn.execute('SELECT * FROM advocate WHERE email = ?', (user_email,)).fetchone()
    conn.close()

    return render_template('edit_adv.html', advocate=advocate)

from flask import request  # Make sure to import request if not already done

@app.route('/client_dashboard', methods=['GET'])
def client_dashboard():
    if 'user_email' not in session or session.get('user_type') != 'client':
        flash('Please log in as a client to access this page.')
        return redirect(url_for('login'))

    user_email = session['user_email']
    conn = get_db_connection()
    client = conn.execute('SELECT * FROM client WHERE email = ?', (user_email,)).fetchone()

    district = request.args.get('district', '')

    if district:
        advocates = conn.execute('SELECT * FROM lawyers WHERE district = ?', (district,)).fetchall()
    else:
        advocates = conn.execute('SELECT * FROM lawyers').fetchall()

    # Join client_posts with advocate to fetch the advocate's name for replies
    client_posts = conn.execute('''
        SELECT client_posts.post_id, client_posts.case_title, client_posts.case_description, 
               client_posts.reply_text, advocate.first_name AS adv_first_name, advocate.last_name AS adv_last_name
        FROM client_posts
        LEFT JOIN advocate ON client_posts.replied_by_adv_id = advocate.adv_id
        WHERE client_posts.client_id = ?
    ''', (client['client_id'],)).fetchall()

    conn.close()

    if client:
        return render_template('client_dashboard.html', client=client, advocates=advocates, client_posts=client_posts)
    else:
        flash('User not found')
        return redirect(url_for('login'))




@app.route('/edit_client', methods=['GET', 'POST'])
def edit_client():
    if 'user_email' not in session or session.get('user_type') != 'client':
        flash('Please log in to access this page.')
        return redirect(url_for('login'))

    user_email = session['user_email']
    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address1 = request.form['address1']
        address2 = request.form['address2']
        city = request.form['city']
        pincode = request.form['pincode']

        conn.execute('''
            UPDATE client
            SET first_name = ?, phone = ?, address_line = ?, address_line2 = ?, city = ?, pincode = ?
            WHERE email = ?
        ''', (name, phone, address1, address2, city, pincode, user_email))

        conn.commit()
        conn.close()

        flash('Profile updated successfully.')
        return redirect(url_for('client_dashboard'))

    client = conn.execute('SELECT * FROM client WHERE email = ?', (user_email,)).fetchone()
    conn.close()

    return render_template('edit_client.html', client=client)

@app.route('/create_post', methods=['POST'])
def create_post():
    if 'user_email' not in session or session.get('user_type') != 'client':
        flash('Please log in to post case details.')
        return redirect(url_for('login'))

    case_title = request.form['case_title']
    case_description = request.form['case_description']

    conn = get_db_connection()
    client = conn.execute('SELECT client_id FROM client WHERE email = ?', (session['user_email'],)).fetchone()

    if client:
        conn.execute('INSERT INTO client_posts (client_id, case_title, case_description) VALUES (?, ?, ?)',
                     (client['client_id'], case_title, case_description))
        conn.commit()
        flash('Case details posted successfully.')
    conn.close()

    return redirect(url_for('client_dashboard'))

@app.route('/reply_post/<int:post_id>', methods=['POST'])
def reply_post(post_id):
    if 'user_email' not in session or session.get('user_type') != 'advocate':
        flash('Please log in as an advocate to reply to posts.')
        return redirect(url_for('login'))

    reply_text = request.form['reply_text']
    
    conn = get_db_connection()
    advocate = conn.execute('SELECT adv_id FROM advocate WHERE email = ?', (session['user_email'],)).fetchone()

    # Update the client_posts table to store the reply and advocate ID
    conn.execute('''
        UPDATE client_posts 
        SET reply_text = ?, replied_by_adv_id = ?, reply_date = CURRENT_TIMESTAMP 
        WHERE post_id = ?
    ''', (reply_text, advocate['adv_id'], post_id))
    conn.commit()
    conn.close()

    flash('Reply sent successfully.')
    return redirect(url_for('advocate_dashboard'))



@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    if 'user_email' not in session or session.get('user_type') != 'advocate':
        flash('Please log in as an advocate to delete posts.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM client_posts WHERE post_id = ?', (post_id,))
    conn.commit()
    conn.close()

    flash('Post deleted successfully.')
    return redirect(url_for('advocate_dashboard'))

@app.route('/delete_client_post/<int:post_id>', methods=['POST'])
def delete_client_post(post_id):
    if 'user_email' not in session or session.get('user_type') != 'client':
        flash('Please log in as a client to access this page.')
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM client_posts WHERE post_id = ?', (post_id,))
    conn.commit()
    conn.close()

    flash('Post and associated reply (if any) have been deleted.')
    return redirect(url_for('client_dashboard'))




ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    conn = get_db_connection()
    
    if request.method == 'POST':
      
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        district = request.form['district']
        legal_area_focus = request.form['legal_area_focus']
        description = request.form['description']
        past_cases = request.form['past_cases']
        phone = request.form['phone']

        
        photo = request.files['photo']
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            upload_folder = os.path.join(app.static_folder, 'uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            file_path = os.path.join(upload_folder, filename)
            photo.save(file_path)
        else:
            filename = None

       
        conn.execute(
            '''INSERT INTO lawyers 
               (first_name, last_name, district, legal_area_focus, description, past_cases, phone, photo) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (first_name, last_name, district, legal_area_focus, description, past_cases, phone, filename)
        )
        conn.commit()
        conn.close()

        flash('Lawyer added successfully!')
        return redirect(url_for('admin_dashboard'))

    
    lawyers = conn.execute('SELECT * FROM lawyers').fetchall()
    conn.close()
    return render_template('admin_dashboard.html', lawyers=lawyers)




@app.route('/add_advocate', methods=['POST'])
def add_advocate():
    
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    phone = request.form['phone']
    district = request.form['district']
    legal_area_focus = request.form['legal_area_focus']
    description = request.form['description']
    past_cases = request.form['past_cases']
    photo = request.files['photo']

    # Save the data to the database or handle file uploads
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO lawyers (first_name, last_name, email, phone, district, legal_area_focus, description, past_cases, photo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (first_name, last_name, email, phone, district, legal_area_focus, description, past_cases, photo.filename)
    )
    conn.commit()
    conn.close()

    # Redirect back to the admin dashboard
    return redirect(url_for('admin_dashboard'))


    # Fetch all advocates
    lawyers = conn.execute('SELECT * FROM lawyers').fetchall()
    conn.close()
    print(lawyers)  # Check if it outputs existing data

    return render_template('admin_dashboard.html', lawyers=lawyers)

@app.route('/delete_lawyer/<int:lawyer_id>', methods=['POST'])
def delete_lawyer(lawyer_id):
    """Delete a lawyer by ID"""
    conn = get_db_connection()

    lawyer = conn.execute('SELECT photo FROM lawyers WHERE id = ?', (lawyer_id,)).fetchone()
    
    if lawyer:
        photo_path = os.path.join(app.static_folder, 'uploads', lawyer['photo'])
        if os.path.exists(photo_path):
            os.remove(photo_path)

        conn.execute('DELETE FROM lawyers WHERE id = ?', (lawyer_id,))
        conn.commit()
        flash('Lawyer deleted successfully.')
    else:
        flash('Lawyer not found.')

    conn.close()
    return redirect(url_for('admin_dashboard'))



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if email in PREDEFINED_ADMINS and PREDEFINED_ADMINS[email] == password:
            session['user_email'] = email
            session['user_type'] = 'admin'
            flash('Admin login successful!')
            return redirect(url_for('admin_dashboard'))
        
        conn = get_db_connection()
        client = conn.execute('SELECT * FROM client WHERE email = ? AND password = ?', (email, password)).fetchone()
        advocate = conn.execute('SELECT * FROM advocate WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()

        if client:
            session['user_email'] = client['email']
            session['user_type'] = 'client'
            flash('Client login successful!')
            return redirect(url_for('client_dashboard'))
        elif advocate:
            session['user_email'] = advocate['email']
            session['user_type'] = 'advocate'
            flash('Advocate login successful!')
            return redirect(url_for('advocate_dashboard'))
        else:
            flash('Invalid credentials. Please try again.')

    return render_template('login.html')



if __name__ == '__main__':
    app.run(debug=True)
