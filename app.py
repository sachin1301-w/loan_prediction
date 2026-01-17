from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import pickle
import numpy as np
from datetime import datetime
from models import db, User, OTP, Prediction
from otp_utils import create_otp, verify_otp, send_otp_email
from utils import generate_recommendations, calculate_feature_importance, export_to_pdf, export_to_excel
import os
import json

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
    return User.query.get(int(user_id))


# Create database tables
with app.app_context():
    db.create_all()


@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


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
        
        flash("OTP sent to your email! Check console for demo.", "success")
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
            
            flash("OTP sent to your email! Check console for demo.", "success")
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
            user = User.query.get(session.get('login_user_id'))
            user.last_login = datetime.utcnow()
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
                         chart_data=json.dumps(chart_data))


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
        prediction_id=new_prediction.id
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


if __name__ == "__main__":
    app.run(debug=True)
