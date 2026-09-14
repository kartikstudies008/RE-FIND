from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='USER')  # 'USER', 'ADMIN'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    items = db.relationship('Item', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    reports = db.relationship('Report', backref='reporter', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'ADMIN'

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    type = db.Column(db.String(20), nullable=False, index=True)  # 'lost', 'found'
    item_name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(60), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    color = db.Column(db.String(60), nullable=True)
    brand = db.Column(db.String(80), nullable=True)
    location = db.Column(db.String(255), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.Time, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active', index=True)  # 'active', 'matched', 'resolved'
    is_flagged = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships to matches
    lost_matches = db.relationship(
        'Match',
        foreign_keys='Match.lost_item_id',
        backref='lost_item',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    found_matches = db.relationship(
        'Match',
        foreign_keys='Match.found_item_id',
        backref='found_item',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    reports = db.relationship('Report', backref='item', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def image_url(self):
        if self.image_path:
            return f"/static/uploads/{self.image_path}"
        # Fallback category based or default placeholder
        return "/static/images/placeholder.svg"

    def __repr__(self):
        return f"<Item #{self.id} {self.type.upper()}: {self.item_name} [{self.status}]>"


class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    lost_item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False)
    found_item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False)
    match_score = db.Column(db.Float, nullable=False, index=True)
    category_score = db.Column(db.Float, nullable=False, default=0.0)
    location_score = db.Column(db.Float, nullable=False, default=0.0)
    date_score = db.Column(db.Float, nullable=False, default=0.0)
    color_score = db.Column(db.Float, nullable=False, default=0.0)
    brand_score = db.Column(db.Float, nullable=False, default=0.0)
    description_score = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), nullable=False, default='suggested', index=True)  # 'suggested', 'accepted', 'rejected'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('lost_item_id', 'found_item_id', name='uq_lost_found_pair'),
    )

    @property
    def confidence_label(self):
        if self.match_score >= 80:
            return "Very Strong Match"
        elif self.match_score >= 60:
            return "Strong Match"
        elif self.match_score >= 40:
            return "Possible Match"
        else:
            return "Weak Match"

    @property
    def badge_class(self):
        if self.match_score >= 80:
            return "badge-very-strong"
        elif self.match_score >= 60:
            return "badge-strong"
        elif self.match_score >= 40:
            return "badge-possible"
        else:
            return "badge-weak"

    def __repr__(self):
        return f"<Match Lost#{self.lost_item_id} <-> Found#{self.found_item_id} ({self.match_score}%)>"


class Report(db.Model):
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False)
    reported_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'reviewed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Report #{self.id} for Item#{self.item_id}>"


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Notification #{self.id} for User#{self.user_id}>"
