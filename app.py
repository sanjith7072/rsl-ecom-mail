from flask import Flask, request, jsonify,render_template
from pymongo import MongoClient
from werkzeug.utils import secure_filename
import os
from firebase_admin import storage
import firebase_admin
from firebase_admin import credentials
from flask_cors import CORS
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)
CORS(app)

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client['driver']
collection = db['driver/investor']

# Configure the upload folder
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Firebase Admin SDK
cred = credentials.Certificate(r"C:\Users\sanju\Downloads\python-crud.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'python-crud-c3a60.appspot.com'
})

# Email configuration
smtp_server = 'smtp.gmail.com'  # Replace with your SMTP server (e.g., smtp.gmail.com for Gmail)
smtp_port = 587  # Replace with the appropriate SMTP port
sender_email = 'sanjusanjith2001@gmail.com'  # Replace with your email address
sender_password = 'zfiw lhuy rkqj zuqh'  # Replace with your email password or app-specific password

def allowed_file(filename):
    # Add any file extension checks here if needed
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'jpg', 'jpeg', 'png'}

@app.route("/add", methods=["POST"])
def add_employee():
    if request.method == "POST":
        # Get JSON data
        data = request.form
        name = data.get("name")
        email = data.get("email")
        country_code = data.get("country_code")
        mobile_number = data.get("mobile_number")
        vehicle_name = data.get("vehicle_name")

        # Check if Passport and Driver's License files are in the request
        if 'passport' not in request.files or 'driver_license' not in request.files:
            return "Passport and Driver's License files are required", 400

        passport = request.files['passport']
        driver_license = request.files['driver_license']

        # Validate and save the files
        if passport and allowed_file(passport.filename) and driver_license and allowed_file(driver_license.filename):
            passport_filename = secure_filename(passport.filename)
            driver_license_filename = secure_filename(driver_license.filename)

            # Save the files to the upload folder
            passport.save(os.path.join(app.config['UPLOAD_FOLDER'], passport_filename))
            driver_license.save(os.path.join(app.config['UPLOAD_FOLDER'], driver_license_filename))

            # Upload the passport and driver_license images to Firebase Storage
            passport_public_url = upload_image_to_storage(os.path.join(app.config['UPLOAD_FOLDER'], passport_filename), f"images/{passport_filename}")
            driver_license_public_url = upload_image_to_storage(os.path.join(app.config['UPLOAD_FOLDER'], driver_license_filename), f"images/{driver_license_filename}")

            # Delete the local copies of the uploaded files
            delete_local_files(os.path.join(app.config['UPLOAD_FOLDER'], passport_filename), os.path.join(app.config['UPLOAD_FOLDER'], driver_license_filename))

            # Insert the new employee into MongoDB with file paths
            employee = {
                "name": name,
                "email": email,
                "country_code": country_code,
                "mobile_number": mobile_number,
                "vehicle_name": vehicle_name,
                "passport_filename": passport_filename,
                "driver_license_filename": driver_license_filename
            }

            # Insert the employee data into MongoDB
            collection.insert_one(employee)

            # Send the email
            send_email(name, email, country_code, mobile_number, vehicle_name)

            return "Employee data and files uploaded successfully"
        else:
            return "Invalid file types for Passport and/or Driver's License", 400

# Function to send an email with employee data
def send_email(name, email, country_code, mobile_number, vehicle_name):
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Start TLS encryption for security
        server.login(sender_email, sender_password)  # Login to your email account

        # Render the HTML template with employee data
        html_template = render_template('index.html', 
                                         name=name, 
                                         email=email, 
                                         country_code=country_code, 
                                         mobile_number=mobile_number, 
                                         vehicle_name=vehicle_name)

        # Create a message container for sending the email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email  # Use the employee's email as the recipient
        msg['Subject'] = 'Thank you for applying'

        # Attach the HTML template as the email body
        msg.attach(MIMEText(html_template, 'html'))

        # Send the email
        server.sendmail(sender_email, email, msg.as_string())

        print('Email sent successfully')
    except Exception as e:
        print(f'Error sending email: {str(e)}')
    finally:
        server.quit()  # Close the SMTP connection

# Function to upload an image to Firebase Storage
def upload_image_to_storage(file_path, destination_path):
    try:
        # Get a reference to the Firebase Storage bucket
        bucket = storage.bucket()

        # Upload the image to Firebase Storage
        blob = bucket.blob(destination_path)
        blob.upload_from_filename(file_path)

        # Make the image publicly accessible (optional)
        blob.make_public()

        # Get the public URL of the uploaded image
        public_url = blob.public_url
        return public_url

    except Exception as e:
        # Handle any potential errors
        print("Error uploading image:", str(e))
        return None

# Function to delete local files
def delete_local_files(*file_paths):
    for file_path in file_paths:
        if os.path.exists(file_path):
            os.remove(file_path)

# READ ALL
@app.route("/get", methods=["GET"])
def get():
    if request.method == "GET":
        employees = list(collection.find({}))
        # Convert ObjectId to strings for JSON serialization
        for employee in employees:
            employee["_id"] = str(employee["_id"])
        return jsonify(employees)

if __name__ == "__main__":
    app.run(host='192.168.0.61', port=3000, debug=True)
