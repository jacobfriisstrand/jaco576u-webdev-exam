from flask import request, make_response, render_template
from functools import wraps
import mysql.connector
import re
import os
import uuid
import time

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from icecream import ic
ic.configureOutput(prefix=f'***** | ', includeContext=True)

UNSPLASH_ACCESS_KEY = 'tKI4eDQ1J-kv_dEhpC1gRN_JNM7DPUsPT0CskyGgnj4'
ADMIN_ROLE_PK = "16fd2706-8baf-433b-82eb-8c7fada847da"
CUSTOMER_ROLE_PK = "c56a4180-65aa-42ec-a945-5fd21dec0538"
PARTNER_ROLE_PK = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
RESTAURANT_ROLE_PK = "9f8c8d22-5a67-4b6c-89d7-58f8b8cb4e15"

SENDER_EMAIL = "webdevexam72@gmail.com"
PASSWORD = "yprb pvwr rmkt axuh"

from constants import price_levels, cuisine_types

# form to get data from input fields
# args to get data from the url
# values to get data from the url and from the form

class CustomException(Exception):
    def __init__(self, message, code):
        super().__init__(message)  # Initialize the base class with the message
        self.message = message  # Store additional information (e.g., error code)
        self.code = code  # Store additional information (e.g., error code)

def raise_custom_exception(error, status_code):
    raise CustomException(error, status_code)


##############################
def db():
    db = mysql.connector.connect(
        host="mysql",      # This should match your Docker service name
        user="root",       
        password="password",  # Ensure this matches your docker-compose.yml
        database="company"    # Ensure this database exists
    )
    cursor = db.cursor(dictionary=True)
    return db, cursor

##############################
def no_cache(view):
    @wraps(view)
    def no_cache_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return no_cache_view


##############################

def allow_origin(origin="*"):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Call the wrapped function
            response = make_response(f(*args, **kwargs))
            # Add Access-Control-Allow-Origin header to the response
            response.headers["Access-Control-Allow-Origin"] = origin
            # Optionally allow other methods and headers for full CORS support
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response
        return decorated_function
    return decorator


##############################
USER_NAME_MIN = 2
USER_NAME_MAX = 20
USER_NAME_REGEX = f"^.{{{USER_NAME_MIN},{USER_NAME_MAX}}}$"
REGEX_NAME = f"^.{{{USER_NAME_MIN},{USER_NAME_MAX}}}$"
def validate_user_name():
    error = f"name {USER_NAME_MIN} to {USER_NAME_MAX} characters"
    user_name = request.form.get("user_name", "").strip()
    if not re.match(USER_NAME_REGEX, user_name):
        toast = render_template("___toast.html", message=error)
        return f"""<template mix-target="#toast">{toast}</template>""", 400
    return user_name

##############################
USER_LAST_NAME_MIN = 2
USER_LAST_NAME_MAX = 20
USER_LAST_NAME_REGEX = f"^.{{{USER_LAST_NAME_MIN},{USER_LAST_NAME_MAX}}}$"
REGEX_LAST_NAME = f"^.{{{USER_LAST_NAME_MIN},{USER_LAST_NAME_MAX}}}$"
def validate_user_last_name():
    error = f"last name {USER_LAST_NAME_MIN} to {USER_LAST_NAME_MAX} characters"
    user_last_name = request.form.get("user_last_name", "").strip()
    if not re.match(USER_LAST_NAME_REGEX, user_last_name):
        toast = render_template("___toast.html", message=error)
        return f"""<template mix-target="#toast">{toast}</template>""", 400
    return user_last_name

##############################
REGEX_EMAIL = "^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$"
def validate_email():
    error = "Email invalid"
    email = request.form.get("email", "").strip()
    if not re.match(REGEX_EMAIL, email):
        toast = render_template("___toast.html", message=error)
        return f"""<template mix-target="#toast">{toast}</template>""", 400
    return email

##############################
PASSWORD_MIN = 8
PASSWORD_MAX = 50
REGEX_PASSWORD = f"^.{{{PASSWORD_MIN},{PASSWORD_MAX}}}$"
def validate_password():
    error = f"password {PASSWORD_MIN} to {PASSWORD_MAX} characters"
    password = request.form.get("password", "").strip()
    if not re.match(REGEX_PASSWORD, password):
        toast = render_template("___toast.html", message=error)
        return f"""<template mix-target="#toast">{toast}</template>""", 400
    return password

##############################
RESTAURANT_NAME_MIN = 2
RESTAURANT_NAME_MAX = 50
RESTAURANT_NAME_REGEX = f"^.{{{RESTAURANT_NAME_MIN},{RESTAURANT_NAME_MAX}}}$"
def validate_restaurant_name():
    error = f"restaurant name {RESTAURANT_NAME_MIN} to {RESTAURANT_NAME_MAX} characters"
    restaurant_name = request.form.get("restaurant_name", "").strip()
    if not re.match(RESTAURANT_NAME_REGEX, restaurant_name):
        toast = render_template("___toast.html", message=error)
        return f"""<template mix-target="#toast">{toast}</template>""", 400
    return restaurant_name

##############################
ADDRESS_MIN = 2
ADDRESS_MAX = 100
ADDRESS_REGEX = f"^.{{{ADDRESS_MIN},{ADDRESS_MAX}}}$"
def validate_address():
    error = f"Address {ADDRESS_MIN} to {ADDRESS_MAX} characters"
    restaurant_address = request.form.get("restaurant_address", "").strip()
    if not re.match(ADDRESS_REGEX, restaurant_address):
        toast = render_template("___toast.html", message=error)
        return f"""<template mix-target="#toast">{toast}</template>""", 400
    return restaurant_address

##############################
REGEX_UUID4 = "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
def validate_uuid4(uuid4 = ""):
    error = f"invalid uuid4"
    if not uuid4:
        uuid4 = request.values.get("uuid4", "").strip()
    if not re.match(REGEX_UUID4, uuid4):
        toast = render_template("___toast.html", message=error)
        return f"""<template mix-target="#toast">{toast}</template>""", 400
    return uuid4

##############################
UPLOAD_ITEM_FOLDER = './static/dishes'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'webp'}

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_upload(file):
    if not file or file.filename == '':
        toast = render_template("___toast.html", message="No file uploaded")
        return f"""<template mix-target="#toast">{toast}</template>""", 400
 
    if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in ALLOWED_EXTENSIONS:
        toast = render_template("___toast.html", message="File type is not allowed")
        return f"""<template mix-target="#toast">{toast}</template>""", 400
 
    # Generate a secure filename
    unique_filename = f"{uuid.uuid4()}.{file.filename.rsplit('.', 1)[1].lower()}"
    return unique_filename

##############################
def _get_email_template(title, content):
    """Helper function to generate consistently styled email template"""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: system-ui, -apple-system, sans-serif;
                background-color: #f3f4f6;
                margin: 0;
                padding: 0;
                color: #1f2937;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background: #ffffff;
                border-radius: 0.5rem;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }}
            .header {{
                background-color: #0484C7;
                padding: 1.25rem;
                text-align: center;
                color: white;
                font-size: 1.5rem;
                font-weight: 600;
            }}
            .content {{
                padding: 1.25rem;
                text-align: center;
            }}
            .content p {{
                font-size: 1rem;
                margin: 1.25rem 0;
                line-height: 1.5;
            }}
            .footer {{
                text-align: center;
                padding: 0.75rem;
                font-size: 0.875rem;
                color: #6b7280;
                background-color: #f9fafb;
            }}
            .button {{
                display: inline-block;
                padding: 0.75rem 1.5rem;
                background-color: #0484C7;
                color: white;
                font-size: 1rem;
                text-decoration: none;
                border-radius: 0.375rem;
                margin-top: 1.25rem;
                transition: background-color 0.2s;
            }}
            .button:hover {{
                background-color: #0484C7;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 1rem 0;
            }}
            th, td {{
                padding: 0.75rem;
                text-align: left;
                border-bottom: 1px solid #e5e7eb;
            }}
            th {{
                background-color: #f9fafb;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                {title}
            </div>
            <div class="content">
                {content}
            </div>
            <div class="footer">
                &copy; {time.strftime('%Y')} KEALT. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

def send_verify_email(email, user_verification_key=None, role=None):
    try:
        if not role or (role not in ["customer", "partner", "restaurant"]):
            raise ValueError("Invalid role")
        
        if not user_verification_key:
            raise ValueError("User verification key is required")

        verification_link = f"http://127.0.0.1/verify/{user_verification_key}"
        
        content = f"""
            <p>Welcome to KEALT!</p>
            <p>Please verify your account by clicking the button below:</p>
            <a href="{verification_link}" class="button">Verify Account</a>
        """
        
        body = _get_email_template("Account Verification - KEALT", content)

        message = MIMEMultipart()
        message["From"] = "KEALT"
        message["To"] = email
        message["Subject"] = "Please verify your account"
        message.attach(MIMEText(body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, PASSWORD)
            server.sendmail(SENDER_EMAIL, email, message.as_string())

        return "email sent"
    except Exception as ex:
        ic(ex)
        raise_custom_exception("Cannot send verification email", 500)

def send_checkout_email(user_email, user_name, cart):
    try:
        cart_items_html = "<table>"
        cart_items_html += "<tr><th>Item</th><th>Price</th></tr>"
        total = 0
        
        for item in cart:
            cart_items_html += f"""
            <tr>
                <td>Dish: {item.get('item_title', 'Unknown Item')} <br> Restaurant: {item.get('item_restaurant', '')}</td>
                <td>{float(item.get('item_price', 0)):.2f} DKK</td>
            </tr>
            """
            total += float(item.get('item_price', 0))
        
        cart_items_html += f"""
        <tr>
            <td><strong>Total</strong></td>
            <td><strong>{total:.2f} DKK</strong></td>
        </tr>
        </table>
        """

        content = f"""
            <p>Dear {user_name},</p>
            <p>Thank you for your order. Here are the details:</p>
            {cart_items_html}
            <p>Bon appetit!</p>
        """
        
        body = _get_email_template("Order Confirmation - KEALT", content)

        message = MIMEMultipart()
        message["From"] = "KEALT"
        message["To"] = user_email
        message["Subject"] = "Your Order Confirmation"
        message.attach(MIMEText(body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, PASSWORD)
            server.sendmail(SENDER_EMAIL, user_email, message.as_string())

        return "email sent"
    except Exception as ex:
        ic(ex)
        raise_custom_exception("cannot send checkout email", 500)

def send_reset_password_email(email, reset_key):
    try:
        reset_url = f"http://127.0.0.1/reset-password/{reset_key}"
        
        content = f"""
            <p>You have requested to reset your password.</p>
            <p>Click the button below to set a new password:</p>
            <a href="{reset_url}" class="button">Reset Password</a>
            <p>This link will expire in 30 minutes.</p>
            <p>If you didn't request this, please ignore this email.</p>
        """
        
        body = _get_email_template("Reset Your Password - KEALT", content)

        message = MIMEMultipart()
        message["From"] = "KEALT"
        message["To"] = email
        message["Subject"] = "Reset Your Password"
        message.attach(MIMEText(body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, PASSWORD)
            server.sendmail(SENDER_EMAIL, email, message.as_string())

        return True
    except Exception as ex:
        ic(ex)
        return False

def send_account_deletion_email(email):
    try:
        content = f"""
            <p>Your account has been successfully deleted.</p>
            <p>If you did not request this action, please contact support immediately.</p>
        """
        
        body = _get_email_template("Account Deletion - KEALT", content)

        message = MIMEMultipart()
        message["From"] = "KEALT"
        message["To"] = email
        message["Subject"] = "Account Deletion Confirmation"
        message.attach(MIMEText(body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, PASSWORD)
            server.sendmail(SENDER_EMAIL, email, message.as_string())

        return True
    except Exception as ex:
        ic(ex)
        raise_custom_exception("Cannot send deletion confirmation email", 500)

def send_user_blocked_email(to_email, user_name):
    try:
        content = f"""
            <p>Dear {user_name},</p>
            <p>Your account has been temporarily suspended for not complying with our Terms and Conditions.</p>
            <p>To dispute this decision or request a review of your account status, please reach out to our support team.</p>
        """
        
        body = _get_email_template("Account Blocked - KEALT", content)

        message = MIMEMultipart()
        message["From"] = "KEALT"
        message["To"] = to_email
        message["Subject"] = "Your account has been blocked"
        message.attach(MIMEText(body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, message.as_string())

        return "email sent"
    except Exception as ex:
        ic(ex)
        raise_custom_exception("cannot send email", 500)

def send_item_blocked_email(to_email, user_name, item_title):
    try:
        content = f"""
            <p>Dear {user_name},</p>
            <p>Your item "{item_title}" has been blocked for not complying with our Terms and Conditions.</p>
            <p>This means the item is no longer visible to customers and cannot be purchased.</p>
            <p>To dispute this decision or request a review of your item's status, please reach out to our support team.</p>
        """
        
        body = _get_email_template("Item Blocked - KEALT", content)

        message = MIMEMultipart()
        message["From"] = "KEALT"
        message["To"] = to_email
        message["Subject"] = "Your Item Has Been Blocked"
        message.attach(MIMEText(body, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, message.as_string())

        return "email sent"
    except Exception as ex:
        ic(ex)
        raise_custom_exception("cannot send email", 500)

def validate_item_title():
    """Validate item title from form data"""
    title = request.form.get("item_title", "").strip()
    if not title:
        raise CustomException("Item title is required", 400)
    if len(title) < 2:
        raise CustomException("Item title must be at least 2 characters", 400)
    if len(title) > 50:
        raise CustomException("Item title must be less than 50 characters", 400)
    return title

def validate_item_description():
    """Validate item description from form data"""
    desc = request.form.get("item_desc", "").strip()
    if not desc:
        raise CustomException("Item description is required", 400)
    if len(desc) < 10:
        raise CustomException("Item description must be at least 10 characters", 400)
    if len(desc) > 255:
        raise CustomException("Item description must be less than 255 characters", 400)
    return desc

def validate_item_price():
    """Validate item price from form data"""
    try:
        price = float(request.form.get("item_price", "0").strip())
        if price <= 0:
            raise CustomException("Price must be greater than 0", 400)
        if price > 999.99:
            raise CustomException("Price must be less than 1000", 400)
        return price
    except ValueError:
        raise CustomException("Invalid price format", 400)



