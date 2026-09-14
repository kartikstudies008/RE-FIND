from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField,
    TextAreaField, SelectField, DateField, TimeField
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
from app.models import User
from config import Config

CATEGORY_CHOICES = [(cat, cat) for cat in Config.CATEGORIES]


class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message="Name is required."),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters.")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Please enter a valid email address.")
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(message="Phone number is required."),
        Length(min=8, max=20, message="Please enter a valid phone number.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=6, message="Password must be at least 6 characters long.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Create Account')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Please enter a valid email address.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required.")
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class ProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message="Name is required."),
        Length(min=2, max=100)
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(message="Phone number is required."),
        Length(min=8, max=20)
    ])
    email = StringField('Email Address', render_kw={'readonly': True})
    submit = SubmitField('Update Profile')


class ItemForm(FlaskForm):
    item_name = StringField('Item Name', validators=[
        DataRequired(message="Item name is required."),
        Length(max=150)
    ])
    category = SelectField('Category', choices=CATEGORY_CHOICES, validators=[
        DataRequired(message="Please select a category.")
    ])
    description = TextAreaField('Description & Identifying Features', validators=[
        DataRequired(message="Please describe the item in detail."),
        Length(min=10, message="Please provide at least 10 characters to ensure accurate AI matching.")
    ])
    color = StringField('Primary Color', validators=[
        Optional(),
        Length(max=60)
    ])
    brand = StringField('Brand / Make', validators=[
        Optional(),
        Length(max=80)
    ])
    location = StringField('Location', validators=[
        DataRequired(message="Location is required."),
        Length(max=250)
    ])
    date = DateField('Date', validators=[
        DataRequired(message="Date is required.")
    ])
    time = TimeField('Approximate Time', validators=[
        Optional()
    ])
    image = FileField('Item Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Only JPG, JPEG, PNG, and WEBP image files are allowed.')
    ])
    submit = SubmitField('Submit Report')


class ReportListingForm(FlaskForm):
    reason = TextAreaField('Reason for Reporting', validators=[
        DataRequired(message="Please provide a reason for flagging this listing."),
        Length(min=10, max=500)
    ])
    submit = SubmitField('Submit Report')


class ContactMessageForm(FlaskForm):
    subject = StringField('Subject', validators=[
        DataRequired(message="Subject is required."),
        Length(max=150)
    ])
    message = TextAreaField('Message', validators=[
        DataRequired(message="Message content is required."),
        Length(min=10, max=1000)
    ])
    submit = SubmitField('Send Message')
