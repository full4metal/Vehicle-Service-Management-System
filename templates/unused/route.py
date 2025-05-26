import os
from flask import jsonify, render_template, request, redirect, url_for, session, flash
from app import app, mysql
from werkzeug.utils import secure_filename
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Specify the folder where uploaded images will be stored
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/main')
def main():
    # Check if user is logged in
    if 'customer_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

    customer_id = session['customer_id']  # Retrieve customer_id from session

    # Fetch vehicles for the current customer
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM vehicle WHERE customer_id = %s", (customer_id,))
    vehicles = cur.fetchall()
    cur.close()

    return render_template('customer_main.html', vehicles=vehicles)


#cusotmer register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO customer(name, email, password) VALUES (%s, %s, %s)", (username, email, password))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('home'))
    return render_template('customer_register.html')


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM customer WHERE name = %s AND password = %s", (username, password))
    user = cur.fetchone()
    cur.close()
    
    if user:
        session['user'] = username  # Store username in session
        session['customer_id'] = user[0]  # Assuming user[0] is the customer_id
        return redirect(url_for('main'))
    else:
        return "Invalid credentials", 401


@app.route('/logout')
def logout():
    session.pop('user', None)  # Remove user from session
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    return render_template('customer_dashboard.html')

@app.route('/vehicle')
def vehicle():
    return render_template('customer_vehicle.html')

@app.route('/add_vehicle', methods=['GET', 'POST'])
def add_vehicle():
    if request.method == 'POST':
        # Get form data
        make = request.form['make']
        model = request.form['model']
        engine_type = request.form['engine_type']
        reg_no = request.form['reg_no']
        created_on = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Check if user is logged in
        if 'customer_id' not in session:
            return redirect(url_for('login'))  # Redirect to login if not authenticated

        customer_id = session['customer_id']  # Retrieve customer_id from session

        # Handling file upload for vehicle image
        if 'vehicle_image' not in request.files:
            return "No file part"
        file = request.files['vehicle_image']
        if file.filename == '':
            return "No selected file"
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

        # Insert the vehicle details into the database
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO vehicle (customer_id, make, model, engine_type, reg_no, created_on, vehicle_image) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (customer_id, make, model, engine_type, reg_no, created_on, filename))
        mysql.connection.commit()
        cur.close()

        return redirect(url_for('vehicle'))
    
    return render_template('customer_vehicle.html')

#book service 
@app.route('/book_service', methods=['GET', 'POST'])
def book_service():
    if 'customer_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        customer_id = session['customer_id']
        vehicle_id = request.form['vehicle_id']
        description = request.form['description']
        status = 'pending'
        created_on = datetime.now()
        updated_on = created_on

        cur = mysql.connection.cursor()
        
        # Find an available mechanic
        cur.execute("SELECT mechanic_id FROM mechanic WHERE status = 'available' LIMIT 1")
        available_mechanic = cur.fetchone()

        if available_mechanic:
            mechanic_id = available_mechanic[0]
            # Update mechanic status to busy
            cur.execute("UPDATE mechanic SET status = 'busy' WHERE mechanic_id = %s", (mechanic_id,))
        else:
            mechanic_id = None  # No available mechanic

        # Insert service request
        cur.execute("""
            INSERT INTO service_request (customer_id, mechanic_id, vehicle_id, status, created_on, updated_on, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (customer_id, mechanic_id, vehicle_id, status, created_on, updated_on, description))

        mysql.connection.commit()
        cur.close()

        if mechanic_id:
            flash('Service request submitted successfully and assigned to a mechanic', 'success')
        else:
            flash('Service request submitted successfully. A mechanic will be assigned soon.', 'success')

        return redirect(url_for('book_service'))

    # Fetch vehicles for the current customer
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM vehicle WHERE customer_id = %s", (session['customer_id'],))
    vehicles = cur.fetchall()
    cur.close()

    return render_template('customer_service.html', vehicles=vehicles)

#ADMIN REGISTER
@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        
        # Validate the form data (basic validation)
        if not name or not email or not password:
            message = "All fields are required"
            return render_template('admin_reg.html', message=message)
        
        # Check if the admin email already exists
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admin WHERE email = %s", [email])
        admin = cur.fetchone()
        
        if admin:
            message = "Admin with this email already exists"
            return render_template('admin_reg.html', message=message)
        
        # Hash the password for security
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        # Insert new admin into the database
        cur.execute("INSERT INTO admin (username, email, password) VALUES (%s, %s, %s)", (name, email, hashed_password))
        mysql.connection.commit()
        cur.close()

        print(f"Registered admin: {name}, {email}, Hashed password: {hashed_password}")
        
        message = "Admin registered successfully"
        return redirect(url_for('admin_login'))  # Redirect to login page after successful registration
    
    return render_template('admin_reg.html')

#ADMIN LOGIN
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username'].strip()  # Trim whitespace
        password = request.form['password']
        
        # Query the database for the admin with the given username
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admin WHERE username = %s", (username,))
        admin = cur.fetchone()  # Fetch one admin
        cur.close()
        
        if admin:
            print(f"Admin found: {admin}")
            print(f"Hashed password from database: {admin[3]}")
            print(f"Password entered: {password}")
            
            # Check the password
            if check_password_hash(admin[3], password):
                session['admin_id'] = admin[0]
                session['admin_username'] = admin[1]
                flash('Admin logged in successfully.', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                print("Password check failed")
                flash('Invalid password.', 'error')
        else:
            print(f"No admin found with username: {username}")
            flash('Admin not found with this username.', 'error')
    
    return render_template('admin_login.html')


@app.route('/admin_logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    flash('Admin logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin_base')
def admin_base():
    return render_template('admin_base.html')

#MAIN ADMIN DASHBOARD PAGE
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))
        
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM service_request WHERE status = 'pending'")
    total_services = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM mechanic WHERE status = 'available'")
    active_mechanics = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM invoice WHERE payment_status = 'pending'")
    pending_invoices = cur.fetchone()[0]
    cur.close()

    quick_stats = {
        'total_services': total_services,
        'active_mechanics': active_mechanics,
        'pending_invoices': pending_invoices
    }
    return render_template('admin_dashboard.html', stats=quick_stats)

#admin service page
@app.route('/admin_services')
def admin_services():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT sr.service_id, sr.status, sr.created_on, sr.description,
               c.name as customer_name, v.make, v.model, m.name as mechanic_name,
               sr.mechanic_id
        FROM service_request sr
        JOIN customer c ON sr.customer_id = c.customer_id
        JOIN vehicle v ON sr.vehicle_id = v.vehicle_id
        LEFT JOIN mechanic m ON sr.mechanic_id = m.mechanic_id
        ORDER BY sr.created_on DESC
    """)
    services_data = cur.fetchall()
    
    # Fetch all mechanics for the dropdown in the edit form
    cur.execute("SELECT mechanic_id, name FROM mechanic")
    mechanics = cur.fetchall()
    
    cur.close()

    # Convert tuple results to dictionaries
    column_names = ['service_id', 'status', 'created_on', 'description', 'customer_name', 'make', 'model', 'mechanic_name', 'mechanic_id']
    services = [dict(zip(column_names, service)) for service in services_data]

    return render_template('admin_services.html', services=services, mechanics=mechanics)

#admin serice page update
@app.route('/update_service/<int:service_id>', methods=['POST'])
def update_service(service_id):
    if 'admin_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'}), 401

    mechanic_id = request.form.get('mechanic_id')
    status = request.form.get('status')

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE service_request
        SET mechanic_id = %s, status = %s
        WHERE service_id = %s
    """, (mechanic_id, status, service_id))
    mysql.connection.commit()
    cur.close()

    return jsonify({'success': True, 'message': 'Service updated successfully'})

#admin service page delete
@app.route('/admin_delete_service/<int:service_id>', methods=['POST'])
def admin_delete_service(service_id):
    if 'admin_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'}), 401

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM service_request WHERE service_id = %s", (service_id,))
    mysql.connection.commit()
    cur.close()

    return jsonify({'success': True, 'message': 'Service deleted successfully'})

#ADMIN MECHANICS
@app.route('/admin_mechanics', methods=['GET', 'POST'])
def admin_mechanics():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        status = request.form['status']
        specialization = request.form['specialization']

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO mechanic (name, username, password, status, specialization)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, username, password, status, specialization))
        mysql.connection.commit()
        cur.close()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Mechanic added successfully'})
        else:
            flash('Mechanic added successfully', 'success')
            return redirect(url_for('admin_mechanics'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT mechanic_id, name, username, status, specialization FROM mechanic ORDER BY name")
    mechanics_data = cur.fetchall()
    cur.close()

    mechanics = [
        {
            'id': mechanic[0],
            'name': mechanic[1],
            'username': mechanic[2],
            'status': mechanic[3],
            'specialization': mechanic[4]
        }
        for mechanic in mechanics_data
    ]

    return render_template('admin_mechanics.html', mechanics=mechanics)

#admin invoices here 
@app.route('/admin/invoices')
def admin_invoices():
    cur = mysql.connection.cursor()
    
    # Fetch all invoices
    cur.execute("""
        SELECT i.invoice_id, i.service_id, c.name as customer_name, i.total_amount, i.payment_status
        FROM invoice i
        JOIN service_request sr ON i.service_id = sr.service_id
        JOIN customer c ON sr.customer_id = c.customer_id
        ORDER BY i.invoice_id DESC
    """)
    invoices = cur.fetchall()
    
    # Fetch completed services without invoices
    cur.execute("""
        SELECT sr.service_id, c.name as customer_name
        FROM service_request sr
        JOIN customer c ON sr.customer_id = c.customer_id
        LEFT JOIN invoice i ON sr.service_id = i.service_id
        WHERE sr.status = 'completed' AND i.invoice_id IS NULL
    """)
    completed_services = cur.fetchall()
    
    cur.close()
    
    return render_template('admin_invoices.html', invoices=invoices, completed_services=completed_services)

@app.route('/admin/create_invoice', methods=['POST'])
def create_invoice():
    if request.method == 'POST':
        service_id = request.form.get('service_id')
        total_amount = request.form.get('total_amount')
        payment_status = request.form.get('payment_status')
        
        if not service_id or not total_amount or not payment_status:
            return jsonify({'success': False, 'message': 'All fields are required'})
        
        try:
            service_id = int(service_id)
            total_amount = float(total_amount)
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid service ID or total amount'})
        
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO invoice (service_id, total_amount, payment_status)
                VALUES (%s, %s, %s)
            """, (service_id, total_amount, payment_status))
            mysql.connection.commit()
            cur.close()
            return jsonify({'success': True, 'message': 'Invoice created successfully'})
        except Exception as e:
            mysql.connection.rollback()
            cur.close()
            return jsonify({'success': False, 'message': str(e)})



@app.route('/admin/delete_invoice/<int:invoice_id>', methods=['DELETE'])
def delete_invoice(invoice_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM invoice WHERE invoice_id = %s", (invoice_id,))
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True, 'message': 'Invoice deleted successfully'})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'success': False, 'message': str(e)})


#ADMIN ADD MECHANIC AND EDIT
@app.route('/update_mechanic/<int:mechanic_id>', methods=['POST'])
def update_mechanic(mechanic_id):
    if 'admin_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'}), 401

    name = request.form['name']
    username = request.form['username']
    specialization = request.form['specialization']
    status = request.form['status']

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE mechanic
        SET name = %s, username = %s, specialization = %s, status = %s
        WHERE mechanic_id = %s
    """, (name, username, specialization, status, mechanic_id))
    mysql.connection.commit()
    cur.close()

    return jsonify({'success': True, 'message': 'Mechanic updated successfully'})

@app.route('/delete_mechanic/<int:mechanic_id>', methods=['POST'])
def delete_mechanic(mechanic_id):
    if 'admin_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'}), 401

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM mechanic WHERE mechanic_id = %s", (mechanic_id,))
    mysql.connection.commit()
    cur.close()

    return jsonify({'success': True, 'message': 'Mechanic deleted successfully'})

#MECHANIC login
@app.route('/mechanic/login', methods=['GET', 'POST'])
def mechanic_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT mechanic_id, name, password FROM mechanic WHERE username = %s", (username,))
        mechanic = cur.fetchone()
        cur.close()
        
        if mechanic:
            mechanic_id, name, hashed_password = mechanic
            if check_password_hash(hashed_password, password):
                session['mechanic_id'] = mechanic_id
                session['mechanic_name'] = name
                flash('Logged in successfully!', 'success')
                return redirect(url_for('mechanic_dashboard'))
        
        flash('Invalid username or password', 'error')
    
    return render_template('mechanic_login.html')

@app.route('/mechanic/logout')
def mechanic_logout():
    session.pop('mechanic_id', None)
    session.pop('mechanic_name', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('mechanic_login'))

@app.route('/mechanic/dashboard')
def mechanic_dashboard():
    if 'mechanic_id' not in session:
        return redirect(url_for('mechanic_login'))
    
    mechanic_id = session['mechanic_id']
    cur = mysql.connection.cursor()
    
    # Get assigned services count
    cur.execute("SELECT COUNT(*) FROM service_request WHERE mechanic_id = %s AND status != 'completed'", (mechanic_id,))
    assigned_services = cur.fetchone()[0]
    
    # Get completed services count
    cur.execute("SELECT COUNT(*) FROM service_request WHERE mechanic_id = %s AND status = 'completed'", (mechanic_id,))
    completed_services = cur.fetchone()[0]
    
    # Get current status
    cur.execute("SELECT status FROM mechanic WHERE mechanic_id = %s", (mechanic_id,))
    current_status = cur.fetchone()[0]
    
    cur.close()
    
    return render_template('mechanic_dashboard.html', 
                           mechanic_name=session['mechanic_name'],
                           assigned_services=assigned_services,
                           completed_services=completed_services,
                           current_status=current_status)

@app.route('/mechanic/services')
def mechanic_services():
    if 'mechanic_id' not in session:
        return redirect(url_for('mechanic_login'))
    
    mechanic_id = session['mechanic_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT sr.service_id, v.make as vehicle_make, v.model as vehicle_model, 
               sr.description, sr.status
        FROM service_request sr
        JOIN vehicle v ON sr.vehicle_id = v.vehicle_id
        WHERE sr.mechanic_id = %s AND sr.status != 'completed'
        ORDER BY sr.created_on DESC
    """, (mechanic_id,))
    services = cur.fetchall()
    cur.close()
    
    # Convert tuple results to dictionaries
    services_list = []
    for service in services:
        services_list.append({
            'service_id': service[0],
            'vehicle_make': service[1],
            'vehicle_model': service[2],
            'description': service[3],
            'status': service[4]
        })
    
    return render_template('mechanic_services.html', services=services_list)

@app.route('/mechanic/invoices')
def mechanic_invoices():
    if 'mechanic_id' not in session:
        return redirect(url_for('mechanic_login'))
    
    mechanic_id = session['mechanic_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT i.invoice_id, i.service_id, sc.total_cost as total_amount, i.payment_status as status
        FROM invoice i
        JOIN service_request sr ON i.service_id = sr.service_id
        JOIN service_cost sc ON i.service_id = sc.service_id
        WHERE sr.mechanic_id = %s
        ORDER BY i.invoice_date DESC
    """, (mechanic_id,))
    invoices = cur.fetchall()
    cur.close()
    
    return render_template('mechanic_invoices.html', invoices=invoices)

@app.route('/mechanic/update_service_status/<int:service_id>', methods=['GET', 'POST'])
def update_service_status(service_id):
    if 'mechanic_id' not in session:
        return redirect(url_for('mechanic_login'))
    
    if request.method == 'POST':
        new_status = request.form['status']
        cur = mysql.connection.cursor()
        cur.execute("UPDATE service_request SET status = %s WHERE service_id = %s", (new_status, service_id))
        mysql.connection.commit()
        cur.close()
        flash('Service status updated successfully', 'success')
        return redirect(url_for('mechanic_services'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM service_request WHERE service_id = %s", (service_id,))
    service = cur.fetchone()
    cur.close()
    
    return render_template('mechanic_update_service_status.html', service=service)

@app.route('/mechanic/view_invoice/<int:invoice_id>')
def view_invoice_details(invoice_id):
    if 'mechanic_id' not in session:
        return redirect(url_for('mechanic_login'))
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT i.*, sc.*, sr.description as service_description
        FROM invoice i
        JOIN service_cost sc ON i.service_id = sc.service_id
        JOIN service_request sr ON i.service_id = sr.service_id
        WHERE i.invoice_id = %s
    """, (invoice_id,))
    invoice = cur.fetchone()
    cur.close()
    
    return render_template('view_invoice_details.html', invoice=invoice)