from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Gamification
    points = db.Column(db.Integer, default=0)
    badges = db.Column(db.Text, default='[]')  # JSON array of badges
    theme_preference = db.Column(db.String(20), default='light')
    
    # Financial Profile
    phone = db.Column(db.String(20))
    occupation = db.Column(db.String(100))
    monthly_income = db.Column(db.Float)
    monthly_expenses = db.Column(db.Float)
    existing_loans = db.Column(db.Integer, default=0)
    pan_number = db.Column(db.String(10))
    aadhar_number = db.Column(db.String(12))
    is_admin = db.Column(db.Boolean, default=False)
    
    # Relationships
    predictions = db.relationship('Prediction', backref='user', lazy=True)
    credit_scores = db.relationship('CreditScoreHistory', backref='user', lazy=True)
    financial_tips = db.relationship('UserTip', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class OTP(db.Model):
    __tablename__ = 'otps'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    otp_type = db.Column(db.String(20), nullable=False)  # 'register' or 'login'
    
    def __repr__(self):
        return f'<OTP {self.email}>'


class Prediction(db.Model):
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    no_of_dependents = db.Column(db.Integer)
    education = db.Column(db.String(20))
    self_employed = db.Column(db.String(10))
    income_annum = db.Column(db.Float)
    loan_amount = db.Column(db.Float)
    loan_term = db.Column(db.Integer)
    cibil_score = db.Column(db.Integer)
    residential_assets_value = db.Column(db.Float)
    commercial_assets_value = db.Column(db.Float)
    luxury_assets_value = db.Column(db.Float)
    bank_asset_value = db.Column(db.Float)
    result = db.Column(db.String(50))
    probability = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Prediction {self.id} - {self.result}>'


class CreditScoreHistory(db.Model):
    __tablename__ = 'credit_score_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    cibil_score = db.Column(db.Integer, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    source = db.Column(db.String(50), default='manual')  # manual, prediction, api
    
    def __repr__(self):
        return f'<CreditScore {self.cibil_score} at {self.recorded_at}>'


class LoanProduct(db.Model):
    __tablename__ = 'loan_products'
    
    id = db.Column(db.Integer, primary_key=True)
    bank_name = db.Column(db.String(100), nullable=False)
    loan_type = db.Column(db.String(50), nullable=False)  # home, personal, auto, business
    interest_rate = db.Column(db.Float, nullable=False)
    processing_fee = db.Column(db.Float)
    min_amount = db.Column(db.Float)
    max_amount = db.Column(db.Float)
    min_tenure = db.Column(db.Integer)
    max_tenure = db.Column(db.Integer)
    min_cibil = db.Column(db.Integer)
    features = db.Column(db.Text)  # JSON array
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<LoanProduct {self.bank_name} - {self.loan_type}>'


class FinancialTip(db.Model):
    __tablename__ = 'financial_tips'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # credit, savings, investment, loan
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(10))
    priority = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<FinancialTip {self.title}>'


class UserTip(db.Model):
    __tablename__ = 'user_tips'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tip_id = db.Column(db.Integer, db.ForeignKey('financial_tips.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_helpful = db.Column(db.Boolean)
    
    def __repr__(self):
        return f'<UserTip {self.user_id} - {self.tip_id}>'


class PerformanceLog(db.Model):
    __tablename__ = 'performance_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String(100), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    response_time = db.Column(db.Float, nullable=False)  # in milliseconds
    status_code = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PerformanceLog {self.endpoint} - {self.response_time}ms>'
