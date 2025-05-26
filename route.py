from decimal import Decimal
import decimal
import os,random
from flask import jsonify, render_template, request, redirect, send_file, url_for, session, flash, send_from_directory
from app import app, mysql
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb
import MySQLdb.cursors
from transformers import AutoModelForCausalLM, AutoTokenizer
from datetime import datetime, date
from flask_mail import Mail, Message
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont



# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '' //add
app.config['MAIL_PASSWORD'] = '' //add
app.config['MAIL_DEFAULT_SENDER'] = '' //add
mail = Mail(app)

# Specify the folder where uploaded images will be stored
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
pdfmetrics.registerFont(TTFont('DejaVuSans', 'static/fonts/DejaVuSans.ttf'))

# tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-small")
# model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-small")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('index.html')


#  Road Side assistance

@app.route('/roadside_assistance')
def roadside_assistance():
    if 'customer_id' not in session:
        return redirect(url_for('login'))
    
    customer_id = session['customer_id']
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch customer's vehicles that are not in pending, accepted, or in-progress service
    cur.execute("""
        SELECT v.* 
        FROM vehicle v
        LEFT JOIN service_request sr ON v.vehicle_id = sr.vehicle_id AND sr.status IN ('pending', 'accepted', 'in-progress')
        WHERE v.customer_id = %s AND sr.service_id IS NULL
    """, (customer_id,))
    vehicles = cur.fetchall()
    
    cur.close()
    
    return render_template('roadside_assistance.html', vehicles=vehicles)

@app.route('/request_assistance', methods=['POST'])
def request_assistance():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'})
    
    customer_id = session['customer_id']
    vehicle_id = request.form.get('vehicle_id')
    description = request.form.get('issue')
    location = request.form.get('location')
    
    if not all([vehicle_id, description, location]):
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            INSERT INTO service_request (customer_id, vehicle_id, description, location, status, created_on)
            VALUES (%s, %s, %s, %s, 'pending', NOW())
        """, (customer_id, vehicle_id, description, location))
        mysql.connection.commit()
        
        return jsonify({'success': True, 'message': 'Assistance request sent successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cur.close()

#customer register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if email already exists
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM customer WHERE email = %s", (email,))
        existing_user = cur.fetchone()
        
        if existing_user:
            flash('Email already exists. Please use a different email.', 'error')
            return render_template('customer_register.html')
        
        # If email doesn't exist, proceed with registration
        cur.execute("INSERT INTO customer(name, email, password) VALUES (%s, %s, %s)", (username, email, password))
        mysql.connection.commit()
        cur.close()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('home'))
    
    return render_template('customer_register.html')


#customer Login
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
        return redirect(url_for('customer_dashboard'))
    else:
        return "Invalid credentials", 401

#customer Dashboard    
@app.route('/customer/dashboard')
def customer_dashboard():
    if 'customer_id' not in session:
        return redirect(url_for('login'))

    customer_id = session['customer_id']
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch customer's vehicles with in_service status, next service date, and current service status
    cur.execute("""
        SELECT v.*, 
               CASE WHEN sr_active.status IN ('pending', 'in-progress') THEN TRUE ELSE FALSE END as in_service,
               sr_active.status as status,
               sr_completed.next_service_date
        FROM vehicle v
        LEFT JOIN service_request sr_active ON v.vehicle_id = sr_active.vehicle_id 
            AND sr_active.status IN ('pending', 'in-progress')
        LEFT JOIN (
            SELECT vehicle_id, MAX(created_on) as last_completed_date, next_service_date
            FROM service_request
            WHERE status = 'completed' AND next_service_date IS NOT NULL
            GROUP BY vehicle_id
        ) sr_completed ON v.vehicle_id = sr_completed.vehicle_id
        WHERE v.customer_id = %s
    """, (customer_id,))
    vehicles = cur.fetchall()

    # Calculate days until next service
    today = date.today()
    for vehicle in vehicles:
        if vehicle['next_service_date']:
            days_until = (vehicle['next_service_date'] - today).days
            vehicle['days_until_next_service'] = max(days_until, 0)
        else:
            vehicle['days_until_next_service'] = None

        # Check if vehicle image exists
        image_path = os.path.join(app.static_folder, 'uploads', os.path.basename(vehicle['vehicle_image']))
        if not os.path.exists(image_path):
            vehicle['vehicle_image'] = 'default_vehicle.jpg'  # Use a default image if the file doesn't exist

    # Fetch service history
    cur.execute("""
        SELECT sr.*, v.make as vehicle_make, v.model as vehicle_model
        FROM service_request sr
        JOIN vehicle v ON sr.vehicle_id = v.vehicle_id
        WHERE sr.customer_id = %s
        ORDER BY sr.created_on DESC
    """, (customer_id,))
    service_history = cur.fetchall()

    # Fetch invoices
    cur.execute("""
    SELECT i.*, CONCAT(v.make, ' ', v.model) AS vehicle_name
    FROM invoice i
    JOIN service_request sr ON i.service_id = sr.service_id
    JOIN vehicle v ON sr.vehicle_id = v.vehicle_id
    WHERE sr.customer_id = %s
    ORDER BY i.invoice_date DESC
    """, (customer_id,))
    invoices = cur.fetchall()

    cur.close()

    # Convert datetime objects to strings to avoid serialization issues
    for vehicle in vehicles:
        if vehicle['next_service_date']:
            vehicle['next_service_date'] = vehicle['next_service_date'].strftime('%Y-%m-%d')
    
    for service in service_history:
        if service['created_on']:
            service['created_on'] = service['created_on'].strftime('%Y-%m-%d %H:%M:%S')
    
    for invoice in invoices:
        if invoice['invoice_date']:
            invoice['invoice_date'] = invoice['invoice_date'].strftime('%Y-%m-%d')

    return render_template('customer_dashboard.html', vehicles=vehicles, service_history=service_history, invoices=invoices)

# Accept parts
@app.route('/customer/service_details/<int:service_id>')
def get_service_details(service_id):
    if 'customer_id' not in session:
        return jsonify({'error': 'Not authorized'}), 401

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Fetch service details
        cur.execute("""
            SELECT * FROM service_request
            WHERE service_id = %s AND customer_id = %s
        """, (service_id, session['customer_id']))
        service = cur.fetchone()

        if not service:
            return jsonify({'error': 'Service not found'}), 404

        # Fetch added parts
        cur.execute("""
            SELECT cost_id, part_name, part_cost, description, status
            FROM service_cost
            WHERE service_id = %s
        """, (service_id,))
        parts = cur.fetchall()

        # Convert datetime objects to strings
        service['created_on'] = service['created_on'].strftime('%Y-%m-%d %H:%M:%S')
        if service['updated_on']:
            service['updated_on'] = service['updated_on'].strftime('%Y-%m-%d %H:%M:%S')

        # Convert Decimal objects to floats for JSON serialization
        for part in parts:
            part['part_cost'] = float(part['part_cost'])

        return jsonify({**service, 'parts': parts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()

@app.route('/customer/update_part_status', methods=['POST'])
def update_part_status():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'})

    data = request.json
    part_id = data.get('part_id')
    status = data.get('status')

    if not part_id or status not in ['accepted', 'rejected']:
        return jsonify({'success': False, 'message': 'Invalid data'})

    cur = mysql.connection.cursor()
    try:
        # Update the part status
        cur.execute("""
            UPDATE service_cost
            SET status = %s
            WHERE cost_id = %s AND service_id IN (
                SELECT service_id FROM service_request WHERE customer_id = %s
            )
        """, (status, part_id, session['customer_id']))

        if cur.rowcount == 0:
            return jsonify({'success': False, 'message': 'Part not found or not authorized'})

        # If accepted, add the part cost to the invoice
        if status == 'accepted':
            cur.execute("""
                UPDATE invoice i
                JOIN service_cost sc ON i.service_id = sc.service_id
                SET i.total_amount = i.total_amount + sc.part_cost
                WHERE sc.cost_id = %s
            """, (part_id,))

        mysql.connection.commit()

        # Fetch the service_id for the updated part
        cur.execute("SELECT service_id FROM service_cost WHERE cost_id = %s", (part_id,))
        service_id = cur.fetchone()[0]

        return jsonify({'success': True, 'message': f'Part status updated to {status}', 'service_id': service_id})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cur.close()

#parts and labour cost
@app.route('/get_service_cost/<int:service_id>')
def get_service_cost(service_id):
    if 'customer_id' not in session:
        return jsonify({'error': 'Not authorized'}), 401

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT sc.part_name, sc.part_cost, sc.description,
               i.total_amount as invoice_total
        FROM service_cost sc
        LEFT JOIN invoice i ON sc.service_id = i.service_id
        WHERE sc.service_id = %s AND sc.status = 'accepted'
    """, (service_id,))
    cost_details = cur.fetchall()
    cur.close()

    if cost_details:
        # Convert decimal values to floats for JSON serialization
        for cost in cost_details:
            for key, value in cost.items():
                if isinstance(value, decimal.Decimal):
                    cost[key] = float(value)
        return jsonify(cost_details)
    else:
        return jsonify({'error': 'Cost details not found'}), 404

@app.route('/customer/add_vehicle', methods=['POST'])
def add_vehicle():
    if 'customer_id' not in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        make = request.form['make']
        model = request.form['model']
        engine_type = request.form['engine_type']
        reg_no = request.form['reg_no']
        customer_id = session['customer_id']
        created_on = datetime.now()

        if 'vehicle_image' not in request.files:
            flash('No file part', 'error')
            return redirect(url_for('customer_dashboard'))

        file = request.files['vehicle_image']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(url_for('customer_dashboard'))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO vehicle (customer_id, make, model, engine_type, reg_no, created_on, vehicle_image)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (customer_id, make, model, engine_type, reg_no, created_on, filename))
        mysql.connection.commit()
        cur.close()

        flash('Vehicle added successfully', 'success')
        
    else:
        flash('Invalid file type', 'error')

    return redirect(url_for('customer_dashboard'))

@app.route('/customer/book_service', methods=['POST'])
def book_service():
    if 'customer_id' not in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        customer_id = session['customer_id']
        vehicle_id = request.form['vehicle_id']
        description = request.form['description']
        status = 'pending'
        created_on = datetime.now()
        updated_on = created_on
        assignment_status = 'unassigned'

        cur = mysql.connection.cursor()
        try:
            # Find an available mechanic
            cur.execute("SELECT mechanic_id FROM mechanic WHERE status = 'available' LIMIT 1")
            available_mechanic = cur.fetchone()

            if available_mechanic:
                mechanic_id = available_mechanic[0]
                # Update mechanic status to busy
                cur.execute("UPDATE mechanic SET status = 'busy' WHERE mechanic_id = %s", (mechanic_id,))
                assignment_status = 'assigned'
            else:
                mechanic_id = None  # No available mechanic

            # Insert service request
            cur.execute("""
                INSERT INTO service_request 
                (customer_id, mechanic_id, vehicle_id, status, created_on, updated_on, description, assignment_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (customer_id, mechanic_id, vehicle_id, status, created_on, updated_on, description, assignment_status))

            mysql.connection.commit()

            if mechanic_id:
                flash('Service request submitted successfully and assigned to a mechanic', 'success')
            else:
                flash('Service request submitted successfully. A mechanic will be assigned soon.', 'success')

        except MySQLdb.Error as e:
            mysql.connection.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        finally:
            cur.close()

    return redirect(url_for('customer_dashboard'))

def assign_mechanic():
    cur = mysql.connection.cursor()
    
    # Find an available mechanic
    cur.execute("SELECT mechanic_id FROM mechanic WHERE status = 'available' LIMIT 1")
    available_mechanic = cur.fetchone()

    if available_mechanic:
        mechanic_id = available_mechanic[0]
        
        # Find the oldest unassigned service request
        cur.execute("""
            SELECT service_id 
            FROM service_request 
            WHERE assignment_status = 'unassigned' 
            ORDER BY created_on ASC 
            LIMIT 1
        """)
        unassigned_service = cur.fetchone()
        
        if unassigned_service:
            service_id = unassigned_service[0]
            
            # Assign the mechanic to the service request
            cur.execute("""
                UPDATE service_request 
                SET mechanic_id = %s, assignment_status = 'assigned' 
                WHERE service_id = %s
            """, (mechanic_id, service_id))
            
            # Update mechanic status to busy
            cur.execute("UPDATE mechanic SET status = 'busy' WHERE mechanic_id = %s", (mechanic_id,))
            
            mysql.connection.commit()

    cur.close()

@app.route('/customer/logout')
def customer_logout():
    session.pop('customer_id', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('home'))

# Customer Reports
@app.route('/customer/generate_report', methods=['POST'])
def generate_customer_report():
    if 'customer_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'})

    customer_id = session['customer_id']
    vehicle_id = request.form.get('vehicle_id')
    report_type = request.form.get('report_type')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Query services based on report type
        if report_type == 'all':
            status_condition = ""
        elif report_type == 'completed':
            status_condition = "AND sr.status = 'completed'"
        elif report_type == 'pending':
            status_condition = "AND sr.status != 'completed'"
        else:
            return jsonify({'success': False, 'message': 'Invalid report type'})

        # Query services with mechanic name and invoice total
        cur.execute(f"""
            SELECT sr.service_id, sr.created_on, sr.description, sr.status,
                   v.make, v.model, v.reg_no, m.name as mechanic_name,
                   i.total_amount as invoice_total
            FROM service_request sr
            JOIN vehicle v ON sr.vehicle_id = v.vehicle_id
            LEFT JOIN mechanic m ON sr.mechanic_id = m.mechanic_id
            LEFT JOIN invoice i ON sr.service_id = i.service_id
            WHERE sr.customer_id = %s AND sr.vehicle_id = %s
            AND DATE(sr.created_on) BETWEEN %s AND %s
            {status_condition}
            ORDER BY sr.created_on DESC
        """, (customer_id, vehicle_id, start_date, end_date))
        services = cur.fetchall()

        # Query vehicle details
        cur.execute("""
            SELECT make, model, reg_no
            FROM vehicle
            WHERE vehicle_id = %s AND customer_id = %s
        """, (vehicle_id, customer_id))
        vehicle = cur.fetchone()

        cur.close()

        # Generate PDF report
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        elements = []

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Center', alignment=1))

        # Add report title and vehicle details
        elements.append(Paragraph("CarServ - Customer Service Report", styles['Center']))
        elements.append(Spacer(1, 0.25*inch))
        elements.append(Paragraph(f"Vehicle: {vehicle['make']} {vehicle['model']} ({vehicle['reg_no']})", styles['Normal']))
        elements.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
        elements.append(Paragraph(f"Report Type: {report_type.capitalize()} Services", styles['Normal']))
        elements.append(Spacer(1, 0.25*inch))

        # Services table
        if services:
            data = [['Service ID', 'Date', 'Description', 'Status', 'Mechanic', 'Invoice Total']]
            for service in services:
                data.append([
                    str(service['service_id']),
                    service['created_on'].strftime('%Y-%m-%d'),
                    service['description'],
                    service['status'].capitalize(),
                    service['mechanic_name'] or 'N/A',
                    f"₹{service['invoice_total']:.2f}" if service['invoice_total'] else 'N/A'
                ])
            
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BOX', (0, 0), (-1, -1), 2, colors.black),
            ]))
            elements.append(table)

            # Calculate and display total invoice amount
            total_invoice_amount = sum(service['invoice_total'] or 0 for service in services)
            elements.append(Spacer(1, 0.25*inch))
            elements.append(Paragraph(f"Total Invoice Amount: ₹{total_invoice_amount:.2f}", styles['Normal']))
        else:
            elements.append(Paragraph("No services found for the selected criteria.", styles['Normal']))

        doc.build(elements)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'customer_service_report_{start_date}_{end_date}.pdf',
            mimetype='application/pdf'
        )

    except MySQLdb.Error as e:
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'An unexpected error occurred: {str(e)}'})


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
                flash('Admin logged in successfully.', 'admin_success')
                return redirect(url_for('admin_dashboard'))
            else:
                print("Password check failed")
                flash('Invalid password.', 'error')
        else:
            print(f"No admin found with username: {username}")
            flash('Admin not found with this username.', 'login_error')
    
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
    cur.execute("SELECT COUNT(*) FROM invoice WHERE payment_status = 'PENDING'")
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

#admin service page update
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

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO mechanic (name, username, password, status)
            VALUES (%s, %s, %s, %s)
        """, (name, username, password, status))
        mysql.connection.commit()
        cur.close()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Mechanic added successfully'})
        else:
            flash('Mechanic added successfully', 'success')
            return redirect(url_for('admin_mechanics'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT mechanic_id, name, username, status FROM mechanic ")
    mechanics_data = cur.fetchall()
    cur.close()

    mechanics = [
        {
            'id': mechanic[0],
            'name': mechanic[1],
            'username': mechanic[2],
            'status': mechanic[3],
        }
        for mechanic in mechanics_data
    ]

    return render_template('admin_mechanics.html', mechanics=mechanics)

#admin invoices here 
@app.route('/admin/invoices')
def admin_invoices():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT i.invoice_id, i.service_id, c.name, i.total_amount, i.payment_status, i.invoice_date
        FROM invoice i
        JOIN service_request sr ON i.service_id = sr.service_id
        JOIN customer c ON sr.customer_id = c.customer_id
        ORDER BY i.invoice_date DESC
    """)
    invoices = cur.fetchall()
    
    cur.execute("""
        SELECT sr.service_id, CONCAT(c.name, ' - ', v.make, ' ', v.model)
        FROM service_request sr
        JOIN customer c ON sr.customer_id = c.customer_id
        JOIN vehicle v ON sr.vehicle_id = v.vehicle_id
        WHERE sr.status = 'completed' AND sr.service_id NOT IN (SELECT service_id FROM invoice)
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
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute("""
                INSERT INTO invoice (service_id, total_amount, payment_status, invoice_date)
                VALUES (%s, %s, %s, %s)
            """, (service_id, total_amount, payment_status, current_time))
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
    # specialization = request.form['specialization']
    status = request.form['status']

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE mechanic
        SET name = %s, username = %s,status = %s
        WHERE mechanic_id = %s
    """, (name, username, status, mechanic_id))
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

#send email remainder
@app.route('/admin/send_invoice_reminder/<int:invoice_id>', methods=['POST'])
def send_invoice_reminder(invoice_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            SELECT c.email, c.name, i.total_amount, i.invoice_date
            FROM invoice i
            JOIN service_request sr ON i.service_id = sr.service_id
            JOIN customer c ON sr.customer_id = c.customer_id
            WHERE i.invoice_id = %s
        """, (invoice_id,))
        invoice_data = cur.fetchone()
        
        if not invoice_data:
            return jsonify({'success': False, 'message': 'Invoice not found'})
        
        customer_email, customer_name, total_amount, invoice_date = invoice_data
        
        msg = Message("Invoice Reminder", recipients=[customer_email])
        msg.body = f"""
        Dear {customer_name},

        This is a friendly reminder about your outstanding invoice:

        Invoice ID: {invoice_id}
        Amount Due: ₹{total_amount:.2f}
        Invoice Date: {invoice_date.strftime('%Y-%m-%d')}

        Please make the payment at your earliest convenience.

        Thank you for your business!

        Best regards,
        CarServ Team
        """
        
        mail.send(msg)
        
        cur.close()
        return jsonify({'success': True, 'message': 'Reminder sent successfully'})
    except Exception as e:
        cur.close()
        return jsonify({'success': False, 'message': str(e)})

# Admin Reports
@app.route('/admin/reports')
def admin_reports():
    return render_template('admin_report.html')

# Generate report

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 9)
        self.drawRightString(letter[0] - 0.5*inch, 0.5*inch, f"Page {self._pageNumber} of {page_count}")

@app.route('/admin/generate_report', methods=['POST'])
def generate_report():
    if 'admin_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'})

    report_type = request.form.get('report_type')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    report_category = request.form.get('report_category')

    today = datetime.now().date()
    if report_type == 'daily':
        start_date = end_date = today
    elif report_type == 'weekly':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif report_type == 'monthly':
        start_date = today.replace(day=1)
        end_date = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    elif report_type == 'custom':
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        return jsonify({'success': False, 'message': 'Invalid report type'})

    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        summary = {}

        if report_category == 'services':
            # Query completed services and total count
            cur.execute("""
                SELECT sr.service_id, sr.created_on, sr.description, c.name as customer_name, 
                       v.make, v.model, m.name as mechanic_name
                FROM service_request sr
                JOIN customer c ON sr.customer_id = c.customer_id
                JOIN vehicle v ON sr.vehicle_id = v.vehicle_id
                LEFT JOIN mechanic m ON sr.mechanic_id = m.mechanic_id
                WHERE sr.status = 'completed' AND DATE(sr.created_on) BETWEEN %s AND %s
                ORDER BY sr.created_on DESC
            """, (start_date, end_date))
            data = cur.fetchall()

            cur.execute("""
                SELECT COUNT(*) as total_services
                FROM service_request
                WHERE status = 'completed' AND DATE(created_on) BETWEEN %s AND %s
            """, (start_date, end_date))
            summary['total_services'] = cur.fetchone()['total_services']

            report_title = "Completed Services Report"
            headers = ['Service ID', 'Date', 'description', 'customer', 'make','model','mechanic']

        elif report_category == 'customers':
            # Query customer activity and totals
            cur.execute("""
                SELECT c.name as customer_name, COUNT(sr.service_id) as services_requested,
                       SUM(i.total_amount) as total_spent
                FROM customer c
                LEFT JOIN service_request sr ON c.customer_id = sr.customer_id
                LEFT JOIN invoice i ON sr.service_id = i.service_id
                WHERE DATE(sr.created_on) BETWEEN %s AND %s
                GROUP BY c.customer_id
                ORDER BY total_spent DESC
            """, (start_date, end_date))
            data = cur.fetchall()

            cur.execute("""
                SELECT COUNT(DISTINCT customer_id) as total_customers
                FROM customer
            """)
            summary['total_customers'] = cur.fetchone()['total_customers']

            cur.execute("""
                SELECT SUM(i.total_amount) as total_spent
                FROM invoice i
                JOIN service_request sr ON i.service_id = sr.service_id
                WHERE DATE(sr.created_on) BETWEEN %s AND %s
            """, (start_date, end_date))
            summary['total_spent'] = cur.fetchone()['total_spent']

            report_title = "Customer Activity Report"
            headers = ['Customer Name', 'Services Requested', 'Total Spent']

        elif report_category == 'invoices':
            # Query invoices and totals
            cur.execute("""
                SELECT i.invoice_id, i.service_id, i.total_amount, i.payment_status, i.invoice_date,
                       c.name as customer_name
                FROM invoice i
                JOIN service_request sr ON i.service_id = sr.service_id
                JOIN customer c ON sr.customer_id = c.customer_id
                WHERE DATE(i.invoice_date) BETWEEN %s AND %s
                ORDER BY i.invoice_date DESC
            """, (start_date, end_date))
            data = cur.fetchall()

            cur.execute("""
                SELECT SUM(total_amount) as total_amount, COUNT(*) as total_invoices
                FROM invoice
                WHERE DATE(invoice_date) BETWEEN %s AND %s
            """, (start_date, end_date))
            totals = cur.fetchone()
            summary['total_amount'] = totals['total_amount']
            summary['total_invoices'] = totals['total_invoices']

            report_title = "Invoices Report"
            headers = ['Invoice ID', 'Service ID', 'Amount' , 'status', 'Date', 'Customer']

        cur.close()

        # Generate PDF report
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        elements = []

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Center', alignment=1))
        styles.add(ParagraphStyle(name='Right', alignment=2))

        # Add company name and report title
        elements.append(Paragraph("CarServ", styles['Center']))
        elements.append(Spacer(1, 0.25*inch))
        elements.append(Paragraph(report_title, styles['Center']))
        elements.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Center']))
        elements.append(Spacer(1, 0.25*inch))

        # Add summary section
        for key, value in summary.items():
            elements.append(Paragraph(f"{key.replace('_', ' ').title()}: {value}", styles['Normal']))

        elements.append(Spacer(1, 0.25*inch))

        # Data table
        table_data = [headers]
        for item in data:
            row = [str(item.get(key, 'N/A')) for key in item]
            table_data.append(row)

        data_table = Table(table_data, repeatRows=1)
        data_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
        ]))
        elements.append(data_table)

        doc.build(elements, canvasmaker=NumberedCanvas)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'CarServ_{report_category}_report_{start_date}_{end_date}.pdf',
            mimetype='application/pdf'
        )

    except MySQLdb.Error as e:
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'An unexpected error occurred: {str(e)}'})




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
        
        flash('Invalid username or password', 'mech_error')
    
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

#mechanic add part
@app.route('/mechanic/add_part', methods=['POST'])
def add_part():
    if 'mechanic_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'})

    service_id = request.form.get('serviceId')
    part_name = request.form.get('partName')
    part_cost = request.form.get('partCost')
    description = request.form.get('partDescription')

    if not all([service_id, part_name, part_cost, description]):
        return jsonify({'success': False, 'message': 'Missing required fields'})

    try:
        part_cost = float(part_cost)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid part cost'})

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            INSERT INTO service_cost (service_id, part_name, part_cost, description, status)
            VALUES (%s, %s, %s, %s, 'pending')
        """, (service_id, part_name, part_cost, description))
        mysql.connection.commit()
        return jsonify({'success': True, 'message': 'Part added successfully'})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cur.close()

#Mechanic view part
@app.route('/mechanic/view_parts/<int:service_id>')
def view_parts(service_id):
    if 'mechanic_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'})

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cur.execute("""
            SELECT part_name, part_cost, description, status
            FROM service_cost
            WHERE service_id = %s AND status IN ('accepted', 'rejected')
            ORDER BY status, part_name
        """, (service_id,))
        parts = cur.fetchall()

        return jsonify({'success': True, 'parts': parts})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cur.close()

@app.route('/mechanic/invoices')
def mechanic_invoices():
    if 'mechanic_id' not in session:
        return redirect(url_for('mechanic_login'))

    cur = mysql.connection.cursor()
    cur.execute("""
    SELECT i.invoice_id, i.service_id, c.name as customer_name, 
           CONCAT(v.make, ' ', v.model) as vehicle_name, 
           i.total_amount, i.payment_status
    FROM invoice i
    JOIN service_request sr ON i.service_id = sr.service_id
    JOIN customer c ON sr.customer_id = c.customer_id
    JOIN vehicle v ON sr.vehicle_id = v.vehicle_id
    WHERE sr.mechanic_id = %s
    ORDER BY i.invoice_date DESC
    """, (session['mechanic_id'],))
    invoice_tuples = cur.fetchall()

    # Fetch completed services for the invoice creation form
    cur.execute("""
        SELECT sr.service_id, v.make, v.model
        FROM service_request sr
        JOIN vehicle v ON sr.vehicle_id = v.vehicle_id
        WHERE sr.mechanic_id = %s AND sr.status = 'Completed' AND sr.service_id NOT IN (SELECT service_id FROM invoice)
    """, (session['mechanic_id'],))
    completed_services = cur.fetchall()

    cur.close()

    # Convert tuples to dictionaries
    invoices = []
    for invoice in invoice_tuples:
        invoices.append({
            'invoice_id': invoice[0],
            'service_id': invoice[1],
            'customer_name': invoice[2],
            'vehicle_name': invoice[3],
            'total_amount': invoice[4],
            'status': invoice[5]  # Note: This is actually 'payment_status' in the query
        })    

    return render_template('mechanic_invoices.html', invoices=invoices, completed_services=completed_services)

@app.route('/mechanic/create_mechanic_invoice', methods=['POST'])
def create_mechanic_invoice():
    if 'mechanic_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'})

    service_id = request.form.get('service_id')
    payment_status = request.form.get('payment_status')
    description = request.form.get('description')
    
    if not all([service_id, payment_status, description]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    try:
        service_id = int(service_id)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid service ID'})
    
    cur = mysql.connection.cursor()
    try:
        # Calculate the total amount of all 'accepted' parts
        cur.execute("""
            SELECT COALESCE(SUM(part_cost), 0) as total_parts_cost
            FROM service_cost
            WHERE service_id = %s AND status = 'accepted'
        """, (service_id,))
        total_parts_cost = cur.fetchone()[0]

        

        # Calculate the total amount
        total_amount = float(total_parts_cost) 

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Update or insert into invoice table
        cur.execute("""
            INSERT INTO invoice (service_id, total_amount, payment_status, invoice_date, description)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            total_amount = VALUES(total_amount),
            payment_status = VALUES(payment_status),
            invoice_date = VALUES(invoice_date),
            description = VALUES(description)
        """, (service_id, total_amount, payment_status, current_time, description))
        
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True, 'message': 'Invoice created successfully'})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/mechanic/update_service_status/<int:service_id>', methods=['GET', 'POST'])
def update_service_status(service_id):
    if 'mechanic_id' not in session:
        return redirect(url_for('mechanic_login'))
    
    mechanic_id = session['mechanic_id']
    
    if request.method == 'POST':
        new_status = request.form['status']
        next_service_date = request.form['next_service_date']
        
        cur = mysql.connection.cursor()
        try:
            # Update service request status and next service date
            cur.execute("UPDATE service_request SET status = %s, next_service_date = %s WHERE service_id = %s", 
                        (new_status, next_service_date, service_id))
            
            # If the new status is 'completed', update mechanic status to 'available'
            if new_status == 'completed':
                cur.execute("UPDATE mechanic SET status = 'available' WHERE mechanic_id = %s", (mechanic_id,))
                
                # Assign the next unassigned service to this mechanic
                cur.execute("""
                    UPDATE service_request 
                    SET mechanic_id = %s, assignment_status = 'assigned' 
                    WHERE assignment_status = 'unassigned' 
                    ORDER BY created_on ASC 
                    LIMIT 1
                """, (mechanic_id,))
                
                # If a new service was assigned, set the mechanic status back to 'busy'
                if cur.rowcount > 0:
                    cur.execute("UPDATE mechanic SET status = 'busy' WHERE mechanic_id = %s", (mechanic_id,))
            
            mysql.connection.commit()
            flash('Service status and next service date updated successfully', 'success')
        except MySQLdb.Error as e:
            mysql.connection.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        finally:
            cur.close()
        
        return redirect(url_for('mechanic_services'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM service_request WHERE service_id = %s", (service_id,))
    service = cur.fetchone()
    cur.close()
    
    return render_template('mechanic_update_service_status.html', service=service)
    
# Mechanic Road side assistance
@app.route('/mechanic/assistance_requests')
def mechanic_assistance_requests():
    if 'mechanic_id' not in session:
        return redirect(url_for('mechanic_login'))
    
    mechanic_id = session['mechanic_id']
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch pending requests and accepted requests for the current mechanic
    cur.execute("""
        SELECT sr.*, v.make, v.model, v.reg_no, c.name as customer_name
        FROM service_request sr
        JOIN vehicle v ON sr.vehicle_id = v.vehicle_id
        JOIN customer c ON sr.customer_id = c.customer_id
        WHERE (sr.status = 'pending' OR (sr.status = 'accepted' AND sr.mechanic_id = %s))
            AND sr.location IS NOT NULL
        ORDER BY sr.created_on DESC
    """, (mechanic_id,))
    assistance_requests = cur.fetchall()
    
    cur.close()
    
    return render_template('mechanic_assistance_requests.html', assistance_requests=assistance_requests)

@app.route('/mechanic/accept_assistance/<int:service_id>', methods=['POST'])
def accept_assistance(service_id):
    if 'mechanic_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'})
    
    mechanic_id = session['mechanic_id']
    cur = mysql.connection.cursor()
    
    try:
        # Start a transaction
        cur.execute("START TRANSACTION")
        
        # Check if the request is still pending
        cur.execute("""
            SELECT status FROM service_request
            WHERE service_id = %s FOR UPDATE
        """, (service_id,))
        result = cur.fetchone()
        
        if not result or result[0] != 'pending':
            cur.execute("ROLLBACK")
            return jsonify({'success': False, 'message': 'Request no longer available'})
        
        # Update service_request table
        cur.execute("""
            UPDATE service_request
            SET status = 'accepted', mechanic_id = %s
            WHERE service_id = %s AND status = 'pending'
        """, (mechanic_id, service_id))
        
        if cur.rowcount == 0:
            # Rollback the transaction if no rows were updated
            cur.execute("ROLLBACK")
            return jsonify({'success': False, 'message': 'Request not found or already accepted'})
        
        # Update mechanic status to 'busy'
        cur.execute("""
            UPDATE mechanic
            SET status = 'busy'
            WHERE mechanic_id = %s
        """, (mechanic_id,))
        
        # Commit the transaction
        cur.execute("COMMIT")
        return jsonify({'success': True, 'message': 'Assistance request accepted and mechanic status updated to busy'})
    except Exception as e:
        # Rollback the transaction in case of any error
        cur.execute("ROLLBACK")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cur.close()

# Mechanic report
@app.route('/mechanic/reports')
def mechanic_reports():
    if 'mechanic_id' not in session:
        return redirect(url_for('mechanic_login'))
    return render_template('mechanic_report.html')

@app.route('/mechanic/generate_report', methods=['POST'])
def generate_mechanic_report():
    if 'mechanic_id' not in session:
        return jsonify({'success': False, 'message': 'Not authorized'})

    mechanic_id = session['mechanic_id']
    report_type = request.form.get('report_type')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    # Calculate date range based on report type
    today = datetime.now().date()
    if report_type == 'daily':
        start_date = end_date = today
    elif report_type == 'weekly':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif report_type == 'monthly':
        start_date = today.replace(day=1)
        end_date = (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    elif report_type == 'custom':
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        return jsonify({'success': False, 'message': 'Invalid report type'})

    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Query completed services for the mechanic
        cur.execute("""
            SELECT sr.service_id, sr.created_on, sr.description, c.name as customer_name, 
                   v.make, v.model
            FROM service_request sr
            JOIN customer c ON sr.customer_id = c.customer_id
            JOIN vehicle v ON sr.vehicle_id = v.vehicle_id
            WHERE sr.mechanic_id = %s AND sr.status = 'completed' AND DATE(sr.created_on) BETWEEN %s AND %s
            ORDER BY sr.created_on DESC
        """, (mechanic_id, start_date, end_date))
        services = cur.fetchall()

        # Query invoices for the mechanic's services
        cur.execute("""
            SELECT i.invoice_id, i.service_id, i.total_amount, i.payment_status, i.invoice_date
            FROM invoice i
            JOIN service_request sr ON i.service_id = sr.service_id
            WHERE sr.mechanic_id = %s AND DATE(i.invoice_date) BETWEEN %s AND %s
            ORDER BY i.invoice_date DESC
        """, (mechanic_id, start_date, end_date))
        invoices = cur.fetchall()

        cur.close()

        # Generate PDF report
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
        elements = []

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Center', alignment=1))
        styles.add(ParagraphStyle(name='Right', alignment=2))

        # Add company name and report title
        elements.append(Paragraph("CarServ", styles['Center']))
        elements.append(Spacer(1, 0.25*inch))
        elements.append(Paragraph(f"Mechanic Service Report", styles['Center']))
        elements.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Center']))
        elements.append(Spacer(1, 0.25*inch))

        # Services table
        elements.append(Paragraph("Completed Services", styles['Heading2']))
        service_data = [['Service ID', 'Date', 'Customer', 'Vehicle', 'Description']]
        for service in services:
            service_data.append([
                str(service['service_id']),
                service['created_on'].strftime('%Y-%m-%d'),
                service['customer_name'],
                f"{service['make']} {service['model']}",
                service['description']
            ])
        service_table = Table(service_data, repeatRows=1)
        service_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
        ]))
        elements.append(service_table)
        elements.append(Spacer(1, 0.25*inch))

        # Invoices table
        elements.append(Paragraph("Invoices", styles['Heading2']))
        invoice_data = [['Invoice ID', 'Service ID', 'Date', 'Amount', 'Status']]
        for invoice in invoices:
            invoice_data.append([
                str(invoice['invoice_id']),
                str(invoice['service_id']),
                invoice['invoice_date'].strftime('%Y-%m-%d'),
                f"₹{invoice['total_amount']:.2f}",
                invoice['payment_status']
            ])
        invoice_table = Table(invoice_data, repeatRows=1)
        invoice_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), 

 (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
        ]))
        elements.append(invoice_table)

        doc.build(elements)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'mechanic_service_report_{start_date}_{end_date}.pdf',
            mimetype='application/pdf'
        )

    except MySQLdb.Error as e:
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'An unexpected error occurred: {str(e)}'})




#customer payment

@app.route('/customer/payment/<int:invoice_id>', methods=['GET', 'POST'])
def payment(invoice_id):
    if 'customer_id' not in session:
        return redirect(url_for('login'))
    customer_id = session['customer_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT name, email FROM customer WHERE customer_id = %s", (customer_id,))
    invoice_info = cursor.fetchone()

    cursor.execute("""
        SELECT i.invoice_id, i.total_amount, v.make, v.model, v.reg_no
        FROM invoice i
        JOIN service_request sr ON i.service_id = sr.service_id
        JOIN vehicle v ON sr.vehicle_id = v.vehicle_id
        WHERE i.invoice_id = %s AND v.customer_id = %s
    """, (invoice_id, customer_id))

    invoice_info = cursor.fetchone()
    amount = invoice_info['total_amount']
    return render_template('customer_payment.html',invoice_info=invoice_info, amount=amount, invoice_id=invoice_id)


@app.route('/paymentdone/<int:invoice_id>', methods=['POST'])
def paymentdone(invoice_id):
    if 'customer_id' not in session:
        return redirect(url_for('login'))
     
    # Update the invoice status to 'paid' in the database
    cur = mysql.connection.cursor()
    cur.execute("UPDATE invoice SET payment_status = 'paid' WHERE invoice_id = %s", (invoice_id,))
    mysql.connection.commit()
    cur.close()

    flash("Payment successful! Thank you for your payment.", "success")
    return redirect(url_for('customer_dashboard'))
