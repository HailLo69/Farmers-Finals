from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import timedelta, datetime
from functools import wraps
from flask_login import current_user
 
import os
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# === Configuration ===
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/farmers finals'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.permanent_session_lifetime = timedelta(minutes=30)

# Upload config
UPLOAD_FOLDER = 'uploads/technical_resources'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create the folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# === Initialize extensions ===
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# === Models ===
class TechnicalResource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_on = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, nullable=True)  # Link to User if needed

# === Utility Functions ===
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    if file and allowed_file(file.filename):
        unique_filename = str(uuid.uuid4()) + "_" + secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        return unique_filename
    return None

# === Create tables ===
with app.app_context():
    db.create_all()

class Users(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('farmer', 'technician', 'admin'), nullable=False)

    farmer_profile = db.relationship('Farmers', back_populates='user', uselist=False, cascade="all, delete-orphan")
    ''' technician = db.relationship('Technician', backref='user', uselist=False)'''
    technician = db.relationship(
    'Technician',
    backref='user',
    uselist=False,
    foreign_keys='Technician.user_id'
)


class Farmers(db.Model):
    __tablename__ = 'farmers'
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    location = db.Column(db.String(150))

    user = db.relationship('Users', back_populates='farmer_profile')
    crops = db.relationship('Crops', back_populates='farmer', cascade="all, delete-orphan")
    training_attendance = db.relationship('TrainingAttendance', backref='farmer', cascade="all, delete-orphan")
    expert_requests = db.relationship('ExpertRequest', back_populates='farmer', cascade="all, delete-orphan")

class Crops(db.Model):
    __tablename__ = 'crops'
    crop_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.farmer_id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    planting_date = db.Column(db.Date, nullable=False)

    farmer = db.relationship('Farmers', back_populates='crops')
    progress_records = db.relationship('CropProgress', back_populates='crop', cascade="all, delete-orphan")
    expert_requests = db.relationship('ExpertRequest', back_populates='crop')  # <-- fixed here


class CropProgress(db.Model):
    __tablename__ = 'crop_progress'
    progress_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    crop_id = db.Column(db.Integer, db.ForeignKey('crops.crop_id', ondelete='CASCADE'), nullable=False)
    stage = db.Column(db.String(100), nullable=False)
    health_status = db.Column(db.String(100), nullable=False)
    issues = db.Column(db.Text)
    date_reported = db.Column(db.Date, nullable=False)

    crop = db.relationship('Crops', back_populates='progress_records')

class ExpertRequest(db.Model):
    __tablename__ = 'expert_requests'
    request_id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.farmer_id'))
    crop_id = db.Column(db.Integer, db.ForeignKey('crops.crop_id'))
    problem = db.Column(db.Text, nullable=False)
    date_submitted = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(20), default='open')
    advice_given = db.Column(db.Text, nullable=True)
    date_responded = db.Column(db.Date, nullable=True)
    assigned_technician_id = db.Column(db.Integer, db.ForeignKey('technicians.technician_id'), nullable=True)

    # Add this relationship to link back to Farmers
    farmer = db.relationship('Farmers', back_populates='expert_requests')

    # Also, if you want, link back to Crops (you had back_populates on Crops side)
    crop = db.relationship('Crops', back_populates='expert_requests')

class TrainingAttendance(db.Model):
    __tablename__ = 'trainingattendance'
    attendance_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('farmers.farmer_id', ondelete='CASCADE'), nullable=False)
    attended = db.Column(db.Boolean, default=False)
    feedback = db.Column(db.Text)

class Technician(db.Model):
    __tablename__ = 'technicians'
    technician_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    name = db.Column(db.String(100))
    expertise = db.Column(db.String(255))

    training_sessions = db.relationship('TrainingSession', back_populates='trainer')

class TrainingSession(db.Model):
    __tablename__ = 'TrainingSessions'
    session_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    description = db.Column(db.Text)
    scheduled_date = db.Column(db.DateTime)

    trainer_id = db.Column(db.Integer, db.ForeignKey('technicians.technician_id'))  # Add FK
    trainer = db.relationship('Technician', back_populates='training_sessions')
    

from flask import url_for

# === Decorators ===

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login to access this page.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapped(*args, **kwargs):
            if session.get('role') not in roles:
                flash(f"Access denied: Requires role(s) {', '.join(roles)}.", "error")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return wrapped
    return decorator

# === Routes ===

@app.route('/')
def home():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'farmer':
            return redirect(url_for('farmer_dashboard'))
        elif role == 'technician':
            return redirect(url_for('technician_dashboard'))
        elif role == 'admin':
            return render_template('admin_dashboard.html', name=session.get('name'))
        else:
            flash("Unknown role, please login again.", "error")
            return redirect(url_for('logout'))
    return redirect(url_for('login'))

# --- Authentication ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']
        user = Users.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            session.permanent = True
            session['user_id'] = user.user_id
            session['name'] = user.name
            session['role'] = user.role
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(url_for('home'))
        flash("Invalid email or password", "error")
    return render_template('login_signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['name']
    email = request.form['email'].lower()
    password = request.form['password']
    role = request.form['role']

    if Users.query.filter_by(email=email).first():
        flash("Email already registered.", "error")
        return redirect(url_for('login'))

    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = Users(name=name, email=email, password_hash=pw_hash, role=role)
    db.session.add(new_user)
    db.session.commit()

    flash("Signup successful! Please login.", "success")
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

# --- Farmer Module ---

@app.route('/farmer/dashboard')
@role_required('farmer')
def farmer_dashboard():
    farmer_profile = Farmers.query.filter_by(farmer_id=session['user_id']).first()
    location = farmer_profile.location if farmer_profile else ''
    return render_template('Farmer/farmers.html', name=session['name'], farmer_id=session['user_id'], location=location)

@app.route('/farmer/profile', methods=['GET', 'POST'])
@role_required('farmer')
def farmer_profile():
    farmer_id = session['user_id']

    if request.method == 'POST':
        location = request.form.get('location')
        farmer_profile = Farmers.query.get(farmer_id)
        if farmer_profile:
            farmer_profile.location = location
            flash("Profile updated successfully!", "success")
        else:
            db.session.add(Farmers(farmer_id=farmer_id, location=location))
            flash("Profile created successfully!", "success")
        db.session.commit()
        return redirect(url_for('add_crop'))

    # GET: Show current profile info
    farmer_profile = Farmers.query.get(farmer_id)
    location = farmer_profile.location if farmer_profile else ''
    return render_template('Farmer/profile.html', location=location)

@app.route('/farmer/add_crop', methods=['GET', 'POST'])
@role_required('farmer')
def add_crop():
    if request.method == 'POST':
        name = request.form['name']
        planting_date_str = request.form['planting_date']
        try:
            planting_date = datetime.strptime(planting_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format.", "error")
            return redirect(url_for('add_crop'))

        new_crop = Crops(farmer_id=session['user_id'], name=name, planting_date=planting_date)
        db.session.add(new_crop)
        db.session.commit()
        flash("Crop added successfully!", "success")
        return redirect(url_for('crop_progress'))

    return render_template('Farmer/crops.html')

@app.route('/farmer/update_profile', methods=['POST'])
@role_required('farmer')
def update_farmer_profile():
    farmer_id = session['user_id']
    location = request.form.get('location')
    farmer = Farmers.query.get(farmer_id)

    if farmer:
        farmer.location = location
        db.session.commit()
        flash("Location updated successfully!", "success")
    else:
        flash("Farmer profile not found.", "error")

    return redirect(url_for('farmer_dashboard'))


@app.route('/farmer/crops')
@role_required('farmer')
def crop_list():
    crops = Crops.query.filter_by(farmer_id=session['user_id']).all()
    return render_template('Farmer/crop_list.html', crops=crops, name=session['name'])

@app.route('/farmer/cropprogress', methods=['GET', 'POST'])
@role_required('farmer')
def crop_progress():
    farmer_id = session['user_id']

    if request.method == 'POST':
        crop_id = request.form.get('crop_id')
        stage = request.form.get('stage')
        health_status = request.form.get('health_status')
        issues = request.form.get('issues')
        date_reported = datetime.today().date()

        if not crop_id or not stage or not health_status:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for('crop_progress'))

        new_progress = CropProgress(
            crop_id=crop_id,
            stage=stage,
            health_status=health_status,
            issues=issues,
            date_reported=date_reported
        )
        db.session.add(new_progress)
        db.session.commit()
        flash("Crop progress updated.", "success")
        return redirect(url_for('crop_progress'))

    crops = Crops.query.filter_by(farmer_id=farmer_id).all()
    return render_template('Farmer/cropprogress.html', crops=crops)

@app.route('/farmer/training_attendance')
@role_required('farmer')
def training_attendance():
    farmer_id = session['user_id']
    attendance_records = TrainingAttendance.query.filter_by(farmer_id=farmer_id).all()
    return render_template('Farmer/training_attendance.html', records=attendance_records)


# --- Expert Request ---

@app.route('/farmer/expert_request', methods=['GET', 'POST'])
@role_required('farmer')
def submit_expert_request():
    farmer_id = session['user_id']

    if request.method == 'POST':
        crop_id = request.form.get('crop_id') or None
        problem = request.form.get('problem', '').strip()

        if not problem:
            flash("Please describe the problem.", "error")
            return redirect(url_for('submit_expert_request'))

        new_request = ExpertRequest(  # <-- Fixed here
           farmer_id=farmer_id,
           crop_id=crop_id,
           problem=problem,
           date_submitted=datetime.today().date(),
           status='open'
        )

        db.session.add(new_request)
        db.session.commit()
        flash("Request submitted to expert.", "success")
        return redirect(url_for('farmer_dashboard'))

    crops = Crops.query.filter_by(farmer_id=farmer_id).all()
    return render_template('Farmer/expert_request.html', crops=crops)

# --- Technician Module ---

@app.route('/technician/dashboard')
@role_required('technician')
def technician_dashboard():
    user_id = session['user_id']
    technician = Technician.query.filter_by(user_id=user_id).first()  # Corrected here

    expert_requests = []
    if technician:
        expert_requests = ExpertRequest.query.filter_by(
            assigned_technician_id=technician.technician_id
        ).all()

    user = Users.query.get(user_id)

    return render_template(
        'Technician/technicians.html',
        name=user.name if user else 'Technician',
        technician_id=technician.technician_id if technician else None,
        expertise=technician.expertise if technician else None,
        requests=expert_requests
    )

@app.route('/technician/update_profile', methods=['POST'])
@role_required('technician')
def update_technician_profile():
    expertise = request.form.get('expertise')
    technician = Technician.query.filter_by(user_id=session['user_id']).first()

    if technician:
        technician.expertise = expertise
        db.session.commit()
        flash("Technician profile updated successfully!", "success")
    else:
        flash("Technician profile not found.", "error")

    return redirect(url_for('technician_dashboard'))



@app.route('/technician/request/<int:request_id>')
@role_required('technician')
def view_expert_request(request_id):
    request_data = ExpertRequest.query.get_or_404(request_id)
    crop = request_data.crop
    farmer = request_data.farmer
    return render_template('Technician/request_detail.html', request=request_data, crop=crop, farmer=farmer)


@app.route('/technician/respond/<int:request_id>', methods=['POST'])
@role_required('technician')
def respond_to_request(request_id):
    # You used session['user_id'] here as technician_id, but this is actually user_id
    # You need to get the technician_id from the Technician table using user_id.
    
    user_id = session['user_id']
    technician = Technician.query.filter_by(user_id=user_id).first()
    if not technician:
        flash("Technician profile not found.", "error")
        return redirect(url_for('technician_dashboard'))

    advice = request.form.get('advice', '').strip()

    if not advice:
        flash("Please provide advice before submitting.", "error")
        return redirect(url_for('view_expert_request', request_id=request_id))

    request_record = ExpertRequest.query.get_or_404(request_id)
    request_record.advice_given = advice
    request_record.date_responded = datetime.today().date()
    request_record.status = 'closed'
    request_record.assigned_technician_id = technician.technician_id  # Use technician_id from db

    db.session.commit()
    flash("Response submitted successfully.", "success")
    return redirect(url_for('technician_dashboard'))


@app.route('/uploads/technical_resources/<filename>')
@login_required
def download_technical_resource(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/technician/resources')
@role_required('technician')
def technician_resources():
    resources = TechnicalResource.query.order_by(TechnicalResource.uploaded_by.desc()).all()
    return render_template('Technician/upload_resource.html', resources=resources)

@app.route('/technician/upload_resource', methods=['GET', 'POST'])
@role_required('technician')
def upload_resource():
    if request.method == 'POST':
        title = request.form.get('title')
        file = request.files.get('file')

        if not title or not file:
            flash("Please provide both a title and a file.", "error")
            return redirect(url_for('upload_resource'))

        filename = save_uploaded_file(file)
        if filename:
            new_resource = TechnicalResource(
                title=title,
                filename=filename,
                uploaded_by=session.get('user_id')
            )
            db.session.add(new_resource)
            db.session.commit()
            flash("Technical resource uploaded successfully!", "success")
            return redirect(url_for('technician_resources'))
        else:
            flash("Invalid file type. Allowed: pdf, docx, doc, txt", "error")

    return render_template('Technician/upload_resource.html')


@app.route('/technician/resources/download/<filename>')
@role_required('technician')
def download_resource(filename):
    # Serve the file from the upload directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


# Optional generic upload endpoint if you want to keep it
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('file')
        filename = save_uploaded_file(file)
        if filename:
            flash('File uploaded successfully.')
            # Save filename info in DB if you want
            return redirect(url_for('upload'))
        else:
            flash('Invalid file or no file selected.')
    return render_template('upload.html')

@app.route('/consultations', methods=['GET', 'POST'])
def consultations():
    if request.method == 'POST':
        request_id = request.args.get('request_id')
        # handle your form submission here
        return "Form submitted successfully!"

    else:
        request_id = request.args.get('request_id')
        
        # Sample mock data to simulate a consultation request
        mock_consultations = {
            '1': {
                'farmer_name': 'John Doe',
                'crop_name': 'Tomato',
                'problem': 'Leaves turning yellow',
                'date_submitted': '2025-05-20',
                'status': 'pending',
                'advice_given': ''
            },
            '2': {
                'farmer_name': 'Jane Smith',
                'crop_name': 'Corn',
                'problem': 'Stunted growth',
                'date_submitted': '2025-05-19',
                'status': 'responded',
                'advice_given': 'Use fertilizer X and increase watering frequency.'
            }
        }
        
        if request_id and request_id in mock_consultations:
            consultation = mock_consultations[request_id]
            return render_template('Technician/consultation_detail.html', consultation=consultation)
        else:
            # No request_id or not found, show all consultations in list
            return render_template('Technician/consultations.html', consultations=mock_consultations.values())


    
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/technician/resources', methods=['GET', 'POST'])
@role_required('technician')
def technician_resources_page():  # changed function name here
    # Your existing function body here
    if request.method == 'POST':
        title = request.form.get('title')
        file = request.files.get('file')

        if not title or not file:
            flash('Title and file are required.', 'error')
            return redirect(url_for('technician_resources'))

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        new_resource = TechnicalResource(
            title=title,
            file_url=url_for('uploaded_file', filename=filename),
            uploaded_on=datetime.utcnow()
        )
        db.session.add(new_resource)
        db.session.commit()

        flash('Resource uploaded successfully!', 'success')
        return redirect(url_for('technician_resources'))

    resources = TechnicalResource.query.order_by(TechnicalResource.uploaded_on.desc()).all()

    return render_template('Technician/technical_resources.html', resources=resources)


@app.route('/technician/trainingsessions/add', methods=['GET', 'POST'])
@role_required('technician')
def add_training_session():
    user_id = session['user_id']
    technician = Technician.query.filter_by(user_id=user_id).first()
    
    if request.method == 'POST':
        title = request.form['title']
        date = request.form['scheduled_date']
        location = request.form['location']
        description = request.form['description']
        
        new_session = TrainingSession(
            title=title,
            scheduled_date=datetime.strptime(date, '%Y-%m-%d'),
            location=location,
            description=description,
            trainer_id=technician.technician_id
        )
        db.session.add(new_session)
        db.session.commit()
        flash('Training session added successfully!', 'success')
        return render_template("Technician/trainingsessions.html", sessions=session)


    return render_template('Technician/add_session.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


