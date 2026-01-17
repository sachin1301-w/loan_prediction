from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import pickle
import numpy as np
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from models import db, User, OTP, Prediction, CreditScoreHistory, LoanProduct, FinancialTip, UserTip, PerformanceLog
from otp_utils import create_otp, verify_otp, send_otp_email
from utils import generate_recommendations, calculate_feature_importance, export_to_pdf, export_to_excel
from gamification import award_badge, get_user_badges, check_and_award_badges, BADGES
from chatbot import get_chatbot_response, get_loan_advice
from credit_utils import (calculate_credit_health_score, get_credit_score_trend, 
                         analyze_credit_issues, calculate_loan_readiness, generate_improvement_plan)
import os
import json
import time

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, use system environment variables

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loan_prediction.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Global variables for model
rf = None
scaler = None

def load_model():
    """Lazy load the model"""
    global rf, scaler
    if rf is None:
        try:
            with open("loan_model(2).pkl", "rb") as file:
                data = pickle.load(file)
            rf = data["model"]
            scaler = data["scaler"]
        except Exception as e:
            print(f"Error loading model: {e}")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def init_sample_data():
    """Initialize sample loan products and financial tips"""
    if LoanProduct.query.count() == 0:
        sample_loans = [
            LoanProduct(bank_name='HDFC Bank', loan_type='home', interest_rate=8.5, processing_fee=0.5,
                       min_amount=500000, max_amount=10000000, min_tenure=12, max_tenure=360, min_cibil=700,
                       features=json.dumps(['No prepayment charges', 'Quick approval', 'Doorstep service'])),
            LoanProduct(bank_name='SBI', loan_type='home', interest_rate=8.3, processing_fee=0.35,
                       min_amount=300000, max_amount=15000000, min_tenure=12, max_tenure=360, min_cibil=650,
                       features=json.dumps(['Lowest interest rate', 'Flexible tenure', 'Top-up facility'])),
            LoanProduct(bank_name='ICICI Bank', loan_type='personal', interest_rate=10.5, processing_fee=2.0,
                       min_amount=50000, max_amount=2000000, min_tenure=12, max_tenure=60, min_cibil=700,
                       features=json.dumps(['Instant approval', 'Minimal documentation', 'Online process'])),
            LoanProduct(bank_name='Axis Bank', loan_type='auto', interest_rate=9.0, processing_fee=1.0,
                       min_amount=100000, max_amount=1500000, min_tenure=12, max_tenure=84, min_cibil=680,
                       features=json.dumps(['90% funding', 'Quick disbursal', 'Free insurance'])),
            LoanProduct(bank_name='Kotak Mahindra', loan_type='business', interest_rate=11.0, processing_fee=1.5,
                       min_amount=500000, max_amount=5000000, min_tenure=12, max_tenure=120, min_cibil=720,
                       features=json.dumps(['Business advisory', 'Flexible repayment', 'Collateral-free up to 10L']))
        ]
        db.session.add_all(sample_loans)
        db.session.commit()
    
    if FinancialTip.query.count() == 0:
        sample_tips = [
            FinancialTip(category='credit', title='Pay Your Bills on Time', icon='⏰',
                        content='Payment history is the most important factor in your credit score. Set up automatic payments to never miss a due date.', priority=1),
            FinancialTip(category='credit', title='Keep Credit Utilization Below 30%', icon='📊',
                        content='Use less than 30% of your available credit limit. High utilization suggests you are over-reliant on credit.', priority=2),
            FinancialTip(category='savings', title='Follow the 50-30-20 Rule', icon='💰',
                        content='Allocate 50% of income to needs, 30% to wants, and 20% to savings and debt repayment.', priority=1),
            FinancialTip(category='savings', title='Build an Emergency Fund', icon='🛡️',
                        content='Save 6 months of expenses in a liquid emergency fund. This prevents taking high-interest loans during emergencies.', priority=2),
            FinancialTip(category='investment', title='Start Early with SIPs', icon='📈',
                        content='Systematic Investment Plans in mutual funds help build wealth through compounding. Even ₹1000/month makes a difference.', priority=1),
            FinancialTip(category='loan', title='Read Loan Terms Carefully', icon='📄',
                        content='Understand interest rates, processing fees, prepayment charges, and hidden costs before signing.', priority=1),
            FinancialTip(category='loan', title='Compare Before Applying', icon='🔍',
                        content='Multiple loan applications hurt your credit score. Compare options first, then apply to your best choice.', priority=2),
        ]
        db.session.add_all(sample_tips)
        db.session.commit()


# Create database tables
with app.app_context():
    db.create_all()
    # Initialize sample data if empty
    init_sample_data()


# Performance monitoring middleware
@app.before_request
def before_request():
    g.start_time = time.time()


@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        response_time = (time.time() - g.start_time) * 1000  # Convert to milliseconds
        
        # Log performance
        try:
            log = PerformanceLog(
                endpoint=request.endpoint or 'unknown',
                method=request.method,
                response_time=response_time,
                status_code=response.status_code,
                user_id=current_user.id if current_user.is_authenticated else None,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')[:200]
            )
            db.session.add(log)
            db.session.commit()
        except:
            db.session.rollback()
    
    return response


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash("Email already registered!", "error")
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash("Username already taken!", "error")
            return redirect(url_for('register'))
        
        # Store data in session temporarily
        session['temp_email'] = email
        session['temp_username'] = username
        session['temp_password'] = password
        
        # Generate and send OTP
        otp_code = create_otp(email, otp_type='register')
        send_otp_email(email, otp_code, purpose="registration")
        
        # Store OTP in session for display to judges
        session['demo_otp'] = otp_code
        
        flash(f"OTP sent! For demo: Your OTP is {otp_code}", "success")
        return redirect(url_for('verify_registration'))
    
    return render_template("register.html")


@app.route("/verify-registration", methods=["GET", "POST"])
def verify_registration():
    if 'temp_email' not in session:
        return redirect(url_for('register'))
    
    if request.method == "POST":
        otp_code = request.form.get("otp")
        email = session.get('temp_email')
        
        success, message = verify_otp(email, otp_code, otp_type='register')
        
        if success:
            # Create user
            new_user = User(
                email=email,
                username=session.get('temp_username'),
                is_verified=True
            )
            new_user.set_password(session.get('temp_password'))
            
            db.session.add(new_user)
            db.session.commit()
            
            # Clear session
            session.pop('temp_email', None)
            session.pop('temp_username', None)
            session.pop('temp_password', None)
            
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        else:
            flash(message, "error")
    
    return render_template("verify_otp.html", purpose="registration", email=session.get('temp_email'))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            # Store user info in session temporarily
            session['login_user_id'] = user.id
            session['login_email'] = email
            
            # Generate and send OTP
            otp_code = create_otp(email, otp_type='login')
            send_otp_email(email, otp_code, purpose="login")
            
            # Store OTP in session for display to judges
            session['demo_otp'] = otp_code
            
            flash(f"OTP sent! For demo: Your OTP is {otp_code}", "success")
            return redirect(url_for('verify_login'))
        else:
            flash("Invalid email or password!", "error")
    
    return render_template("login.html")


@app.route("/verify-login", methods=["GET", "POST"])
def verify_login():
    if 'login_email' not in session:
        return redirect(url_for('login'))
    
    if request.method == "POST":
        otp_code = request.form.get("otp")
        email = session.get('login_email')
        
        success, message = verify_otp(email, otp_code, otp_type='login')
        
        if success:
            user = db.session.get(User, session.get('login_user_id'))
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            
            login_user(user, remember=True)
            
            # Clear session
            session.pop('login_user_id', None)
            session.pop('login_email', None)
            
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash(message, "error")
    
    return render_template("verify_otp.html", purpose="login", email=session.get('login_email'))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "success")
    return redirect(url_for('login'))


@app.route("/dashboard")
@login_required
def dashboard():
    user_predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).all()
    
    # Calculate statistics
    total_predictions = len(user_predictions)
    approved_count = sum(1 for p in user_predictions if 'Approved' in p.result)
    approval_rate = (approved_count / total_predictions * 100) if total_predictions > 0 else 0
    
    # Recent predictions for quick view
    recent_predictions = user_predictions[:5]
    
    # Get user badges
    user_badges = get_user_badges(current_user)
    
    # Chart data for analytics
    chart_data = {
        'approval_trend': [],
        'loan_amounts': [],
        'cibil_scores': []
    }
    
    if user_predictions:
        # Last 10 predictions trend
        for pred in user_predictions[:10][::-1]:
            chart_data['approval_trend'].append({
                'date': pred.created_at.strftime('%m/%d'),
                'approved': 1 if 'Approved' in pred.result else 0
            })
            chart_data['loan_amounts'].append({
                'date': pred.created_at.strftime('%m/%d'),
                'amount': pred.loan_amount
            })
            chart_data['cibil_scores'].append({
                'score': pred.cibil_score,
                'result': pred.result
            })
    
    return render_template("dashboard.html", 
                         user=current_user, 
                         predictions=recent_predictions,
                         total_predictions=total_predictions,
                         approved_count=approved_count,
                         approval_rate=approval_rate,
                         chart_data=json.dumps(chart_data),
                         user_badges=user_badges[:3],
                         user_points=current_user.points)


@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    if request.method == "GET":
        return render_template("predict.html")
    
    # Load model if not loaded
    load_model()
    
    no_of_dependents = int(request.form["no_of_dependents"])
    education = request.form["education"]
    self_employed = request.form["self_employed"]
    income_annum = float(request.form["income_annum"])
    loan_amount = float(request.form["loan_amount"])
    loan_term = int(request.form["loan_term"])
    cibil_score = int(request.form["cibil_score"])
    residential_assets_value = float(request.form["residential_assets_value"])
    commercial_assets_value = float(request.form["commercial_assets_value"])
    luxury_assets_value = float(request.form["luxury_assets_value"])
    bank_asset_value = float(request.form["bank_asset_value"])

    education_val = 1 if education == "Graduate" else 0
    self_employed_val = 1 if self_employed == "Yes" else 0

    input_data = np.array([[  
        no_of_dependents,
        education_val,
        self_employed_val,
        income_annum,
        loan_amount,
        loan_term,
        cibil_score,
        residential_assets_value,
        commercial_assets_value,
        luxury_assets_value,
        bank_asset_value
    ]])

    input_data_scaled = scaler.transform(input_data)

    prediction = rf.predict(input_data_scaled)[0]
    probability = rf.predict_proba(input_data_scaled)[0][1] * 100

    result = "Approved ✅" if prediction == 1 else "Rejected ❌"

    # Save prediction to database
    new_prediction = Prediction(
        user_id=current_user.id,
        no_of_dependents=no_of_dependents,
        education=education,
        self_employed=self_employed,
        income_annum=income_annum,
        loan_amount=loan_amount,
        loan_term=loan_term,
        cibil_score=cibil_score,
        residential_assets_value=residential_assets_value,
        commercial_assets_value=commercial_assets_value,
        luxury_assets_value=luxury_assets_value,
        bank_asset_value=bank_asset_value,
        result=result,
        probability=round(probability, 2)
    )
    
    db.session.add(new_prediction)
    db.session.commit()
    
    # Award badges
    all_predictions = Prediction.query.filter_by(user_id=current_user.id).all()
    new_badges = check_and_award_badges(current_user, all_predictions)
    
    # Check for approval badge
    if prediction == 1:
        badge = award_badge(current_user, 'approved_once')
        if badge:
            new_badges.append(badge)
    
    # Check for high CIBIL badge
    if cibil_score >= 750:
        badge = award_badge(current_user, 'high_score')
        if badge:
            new_badges.append(badge)

    # Generate recommendations
    pred_data = {
        'cibil_score': cibil_score,
        'income_annum': income_annum,
        'loan_amount': loan_amount,
        'residential_assets_value': residential_assets_value,
        'commercial_assets_value': commercial_assets_value,
        'luxury_assets_value': luxury_assets_value,
        'bank_asset_value': bank_asset_value,
        'education': education,
        'self_employed': self_employed
    }
    
    recommendations, tips = generate_recommendations(pred_data, result)
    feature_importance = calculate_feature_importance(pred_data)

    return render_template(
        "predict.html",
        prediction=result,
        probability=round(probability, 2),
        recommendations=recommendations,
        tips=tips,
        feature_importance=feature_importance,
        new_badges=new_badges
    )


@app.route("/history")
@login_required
def history():
    user_predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).all()
    return render_template("history.html", predictions=user_predictions)


@app.route("/calculator")
@login_required
def calculator():
    """Loan eligibility calculator"""
    return render_template("calculator.html")


@app.route("/analytics")
@login_required
def analytics():
    """Advanced analytics dashboard"""
    predictions = Prediction.query.filter_by(user_id=current_user.id).all()
    
    if not predictions:
        return render_template("analytics.html", has_data=False)
    
    # Prepare data for charts
    analytics_data = {
        'total': len(predictions),
        'approved': sum(1 for p in predictions if 'Approved' in p.result),
        'rejected': sum(1 for p in predictions if 'Rejected' in p.result),
        'avg_cibil': sum(p.cibil_score for p in predictions) / len(predictions),
        'avg_loan': sum(p.loan_amount for p in predictions) / len(predictions),
        'predictions': []
    }
    
    for p in predictions:
        analytics_data['predictions'].append({
            'date': p.created_at.strftime('%Y-%m-%d'),
            'result': p.result,
            'probability': p.probability,
            'cibil_score': p.cibil_score,
            'loan_amount': p.loan_amount,
            'income': p.income_annum
        })
    
    return render_template("analytics.html", has_data=True, data=json.dumps(analytics_data))


@app.route("/export/pdf")
@login_required
def export_pdf():
    """Export predictions to PDF"""
    predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).all()
    
    if not predictions:
        flash("No predictions to export!", "error")
        return redirect(url_for('history'))
    
    pdf_buffer = export_to_pdf(predictions, current_user)
    filename = f"loan_predictions_{current_user.username}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@app.route("/export/excel")
@login_required
def export_excel():
    """Export predictions to Excel"""
    predictions = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).all()
    
    if not predictions:
        flash("No predictions to export!", "error")
        return redirect(url_for('history'))
    
    excel_buffer = export_to_excel(predictions, current_user)
    filename = f"loan_predictions_{current_user.username}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return send_file(
        excel_buffer,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@app.route("/api/calculate-eligibility", methods=["POST"])
@login_required
def calculate_eligibility():
    """Quick eligibility check API"""
    data = request.get_json()
    
    # Award calculator badge
    award_badge(current_user, 'calculator_user')
    
    income = float(data.get('income', 0))
    cibil = int(data.get('cibil', 0))
    loan_amount = float(data.get('loan_amount', 0))
    
    # Simple eligibility logic
    eligible = True
    score = 0
    feedback = []
    
    if cibil >= 750:
        score += 40
        feedback.append({"text": "Excellent CIBIL score!", "type": "success"})
    elif cibil >= 650:
        score += 25
        feedback.append({"text": "Good CIBIL score", "type": "info"})
    else:
        eligible = False
        feedback.append({"text": "CIBIL score too low (need 650+)", "type": "warning"})
    
    if loan_amount <= income * 3:
        score += 30
        feedback.append({"text": "Loan amount is reasonable", "type": "success"})
    else:
        score += 10
        feedback.append({"text": "High loan-to-income ratio", "type": "warning"})
    
    if income >= 300000:
        score += 30
        feedback.append({"text": "Good income level", "type": "success"})
    else:
        score += 15
        feedback.append({"text": "Modest income level", "type": "info"})
    
    return jsonify({
        'eligible': eligible,
        'score': score,
        'feedback': feedback,
        'recommendation': "Proceed with full application" if score >= 70 else "Consider improving factors"
    })


@app.route("/chatbot", methods=["GET", "POST"])
@login_required
def chatbot():
    if request.method == "GET":
        return render_template("chatbot.html")
    
    data = request.get_json()
    message = data.get('message', '')
    
    # Get user context
    last_prediction = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).first()
    context = {
        'username': current_user.username,
        'last_prediction': last_prediction.result if last_prediction else None
    }
    
    response = get_chatbot_response(message, context)
    return jsonify({'response': response})


@app.route("/simulator", methods=["GET", "POST"])
@login_required
def simulator():
    if request.method == "GET":
        return render_template("simulator.html")
    
    # Load model if not loaded
    load_model()
    
    data = request.get_json()
    
    # Get values from request
    no_of_dependents = int(data.get('dependents', 0))
    education = data.get('education', 'Graduate')
    self_employed = data.get('self_employed', 'No')
    income_annum = float(data.get('income', 300000))
    loan_amount = float(data.get('loan_amount', 500000))
    loan_term = int(data.get('loan_term', 12))
    cibil_score = int(data.get('cibil_score', 700))
    residential_assets_value = float(data.get('residential_assets', 0))
    commercial_assets_value = float(data.get('commercial_assets', 0))
    luxury_assets_value = float(data.get('luxury_assets', 0))
    bank_asset_value = float(data.get('bank_assets', 0))
    
    education_val = 1 if education == "Graduate" else 0
    self_employed_val = 1 if self_employed == "Yes" else 0
    
    input_data = np.array([[
        no_of_dependents,
        education_val,
        self_employed_val,
        income_annum,
        loan_amount,
        loan_term,
        cibil_score,
        residential_assets_value,
        commercial_assets_value,
        luxury_assets_value,
        bank_asset_value
    ]])
    
    input_data_scaled = scaler.transform(input_data)
    prediction = rf.predict(input_data_scaled)[0]
    probability = rf.predict_proba(input_data_scaled)[0][1] * 100
    
    pred_data = {
        'cibil_score': cibil_score,
        'income_annum': income_annum,
        'loan_amount': loan_amount,
        'residential_assets_value': residential_assets_value,
        'commercial_assets_value': commercial_assets_value,
        'luxury_assets_value': luxury_assets_value,
        'bank_asset_value': bank_asset_value,
        'education': education,
        'self_employed': self_employed
    }
    
    advice = get_loan_advice(pred_data)
    
    return jsonify({
        'approved': bool(prediction),
        'probability': round(probability, 2),
        'advice': advice
    })


@app.route("/bank-statement", methods=["GET", "POST"])
@login_required
def bank_statement():
    if request.method == "GET":
        return render_template("bank_statement.html")
    
    # Handle file upload
    if 'statement' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['statement']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # For demo: simulate data extraction
    # In production, use OCR/PDF parsing
    extracted_data = {
        'monthly_income': 45000,
        'average_balance': 125000,
        'recurring_emis': 8500,
        'credit_transactions': 12,
        'debit_transactions': 45,
        'suggested_loan_amount': 400000,
        'confidence': 85
    }
    
    badge = award_badge(current_user, 'export_expert')
    
    return jsonify({
        'success': True,
        'data': extracted_data,
        'message': 'Statement analyzed successfully',
        'badge': badge
    })


@app.route("/toggle-theme", methods=["POST"])
@login_required
def toggle_theme():
    data = request.get_json()
    theme = data.get('theme', 'light')
    current_user.theme_preference = theme
    db.session.commit()
    return jsonify({'success': True, 'theme': theme})


@app.route("/badges")
@login_required
def badges():
    user_badges = get_user_badges(current_user)
    all_badges = [{'key': k, **v} for k, v in BADGES.items()]
    return render_template("badges.html", 
                          user_badges=user_badges, 
                          all_badges=all_badges,
                          user_points=current_user.points)


@app.route("/credit-health")
@login_required
def credit_health():
    """Credit Health Report with trends and analysis"""
    health_score = calculate_credit_health_score(current_user)
    trend_data = get_credit_score_trend(current_user, days=180)
    credit_issues = analyze_credit_issues(current_user)
    readiness = calculate_loan_readiness(current_user)
    improvement_plan = generate_improvement_plan(current_user)
    
    # Determine health level and color
    if health_score >= 80:
        health_level = 'Excellent'
        health_color = '#2ecc71'
    elif health_score >= 60:
        health_level = 'Good'
        health_color = '#3498db'
    elif health_score >= 40:
        health_level = 'Fair'
        health_color = '#f39c12'
    else:
        health_level = 'Needs Improvement'
        health_color = '#e74c3c'
    
    # Add current credit score to trend if no history
    if not trend_data:
        latest_pred = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).first()
        if latest_pred:
            trend_data = [{
                'date': latest_pred.created_at.strftime('%Y-%m-%d'),
                'score': latest_pred.cibil_score,
                'source': 'prediction'
            }]
    
    return render_template('credit_health.html',
                          health_score=health_score,
                          health_level=health_level,
                          health_color=health_color,
                          trend_data=trend_data,
                          credit_issues=credit_issues,
                          readiness=readiness,
                          improvement_plan=improvement_plan)


@app.route("/loan-comparison")
@login_required
def loan_comparison():
    """Loan Product Comparison Dashboard"""
    loan_products = LoanProduct.query.filter_by(is_active=True).all()
    
    # Parse features from JSON
    for loan in loan_products:
        if loan.features:
            try:
                loan.features = json.loads(loan.features)
            except:
                loan.features = []
    
    # Find recommended loan based on user's latest prediction
    recommended_loan = None
    latest_pred = Prediction.query.filter_by(user_id=current_user.id).order_by(Prediction.created_at.desc()).first()
    if latest_pred:
        # Simple recommendation logic
        suitable_loans = [l for l in loan_products if l.min_cibil <= latest_pred.cibil_score]
        if suitable_loans:
            recommended_loan = min(suitable_loans, key=lambda x: x.interest_rate)
    
    return render_template('loan_comparison.html',
                          loan_products=loan_products,
                          recommended_loan=recommended_loan)


@app.route("/financial-tips")
@login_required
def financial_tips():
    """Financial Awareness Tips and Guidance"""
    tips = FinancialTip.query.filter_by(is_active=True).order_by(FinancialTip.priority.desc()).all()
    return render_template('financial_tips.html', financial_tips=tips)


@app.route("/mark-tip-helpful", methods=["POST"])
@login_required
def mark_tip_helpful():
    """Mark a financial tip as helpful"""
    data = request.get_json()
    tip_id = data.get('tip_id')
    helpful = data.get('helpful', True)
    
    user_tip = UserTip(user_id=current_user.id, tip_id=tip_id, is_helpful=helpful)
    db.session.add(user_tip)
    db.session.commit()
    
    return jsonify({'success': True})


@app.route("/admin")
@login_required
def admin_dashboard():
    """Admin Dashboard with Analytics and Performance Monitoring"""
    # Check if user is admin
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Calculate stats
    total_users = User.query.count()
    total_predictions = Prediction.query.count()
    
    # New users today
    today = datetime.now(timezone.utc).date()
    new_users_today = User.query.filter(func.date(User.created_at) == today).count()
    
    # Predictions today
    predictions_today = Prediction.query.filter(func.date(Prediction.created_at) == today).count()
    
    # Approval rate (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_predictions = Prediction.query.filter(Prediction.created_at >= thirty_days_ago).all()
    if recent_predictions:
        approved = sum(1 for p in recent_predictions if p.result == 'Approved')
        approval_rate = (approved / len(recent_predictions)) * 100
    else:
        approval_rate = 0
    
    # Average response time (last 24 hours)
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    recent_logs = PerformanceLog.query.filter(PerformanceLog.timestamp >= twenty_four_hours_ago).all()
    if recent_logs:
        avg_response_time = int(sum(l.response_time for l in recent_logs) / len(recent_logs))
    else:
        avg_response_time = 0
    
    stats = {
        'total_users': total_users,
        'new_users_today': new_users_today,
        'total_predictions': total_predictions,
        'predictions_today': predictions_today,
        'approval_rate': approval_rate,
        'avg_response_time': avg_response_time
    }
    
    # Recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    for user in recent_users:
        user.prediction_count = Prediction.query.filter_by(user_id=user.id).count()
    
    # Performance data for chart
    performance_data = {
        'hours': [],
        'response_times': []
    }
    for i in range(24):
        hour_start = datetime.now(timezone.utc) - timedelta(hours=24-i)
        hour_end = hour_start + timedelta(hours=1)
        hour_logs = PerformanceLog.query.filter(
            PerformanceLog.timestamp >= hour_start,
            PerformanceLog.timestamp < hour_end
        ).all()
        
        performance_data['hours'].append(hour_start.strftime('%H:00'))
        if hour_logs:
            avg = sum(l.response_time for l in hour_logs) / len(hour_logs)
            performance_data['response_times'].append(round(avg, 2))
        else:
            performance_data['response_times'].append(0)
    
    # User activity data
    activity_data = {
        'days': [],
        'new_users': [],
        'predictions': []
    }
    for i in range(7):
        day = datetime.now(timezone.utc).date() - timedelta(days=6-i)
        activity_data['days'].append(day.strftime('%m/%d'))
        
        new_users = User.query.filter(func.date(User.created_at) == day).count()
        activity_data['new_users'].append(new_users)
        
        preds = Prediction.query.filter(func.date(Prediction.created_at) == day).count()
        activity_data['predictions'].append(preds)
    
    # Top endpoints
    top_endpoints = db.session.query(
        PerformanceLog.endpoint,
        func.count(PerformanceLog.id).label('count')
    ).group_by(PerformanceLog.endpoint).order_by(func.count(PerformanceLog.id).desc()).limit(5).all()
    
    top_endpoints = [{'endpoint': e[0], 'count': e[1]} for e in top_endpoints]
    
    # Slowest endpoints
    slow_endpoints = db.session.query(
        PerformanceLog.endpoint,
        func.avg(PerformanceLog.response_time).label('avg_time')
    ).group_by(PerformanceLog.endpoint).order_by(func.avg(PerformanceLog.response_time).desc()).limit(5).all()
    
    slow_endpoints = [{'endpoint': e[0], 'avg_time': int(e[1])} for e in slow_endpoints]
    
    return render_template('admin_dashboard.html',
                          stats=stats,
                          recent_users=recent_users,
                          performance_data=performance_data,
                          activity_data=activity_data,
                          top_endpoints=top_endpoints,
                          slow_endpoints=slow_endpoints)


if __name__ == "__main__":
    app.run(debug=True)
