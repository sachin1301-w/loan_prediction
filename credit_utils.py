"""
Credit Score Analysis and Financial Health Utilities
"""
import json
from datetime import datetime, timedelta
from models import CreditScoreHistory, Prediction

def calculate_credit_health_score(user):
    """Calculate overall credit health score (0-100)"""
    score = 0
    
    # Get latest prediction
    latest_prediction = Prediction.query.filter_by(user_id=user.id).order_by(Prediction.created_at.desc()).first()
    
    if latest_prediction:
        # CIBIL Score (40 points)
        cibil = latest_prediction.cibil_score
        if cibil >= 750:
            score += 40
        elif cibil >= 700:
            score += 30
        elif cibil >= 650:
            score += 20
        else:
            score += 10
        
        # Loan to Income Ratio (30 points)
        loan_to_income = latest_prediction.loan_amount / (latest_prediction.income_annum / 12)
        if loan_to_income <= 3:
            score += 30
        elif loan_to_income <= 5:
            score += 20
        elif loan_to_income <= 10:
            score += 10
        
        # Asset Coverage (20 points)
        total_assets = (latest_prediction.residential_assets_value + 
                       latest_prediction.commercial_assets_value + 
                       latest_prediction.luxury_assets_value + 
                       latest_prediction.bank_asset_value)
        asset_ratio = total_assets / latest_prediction.loan_amount if latest_prediction.loan_amount > 0 else 0
        if asset_ratio >= 1.5:
            score += 20
        elif asset_ratio >= 1.0:
            score += 15
        elif asset_ratio >= 0.5:
            score += 10
        
        # Employment Stability (10 points)
        if latest_prediction.self_employed == 'No':
            score += 10
        else:
            score += 5
    
    return min(score, 100)


def get_credit_score_trend(user, days=180):
    """Get credit score trend data"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    history = CreditScoreHistory.query.filter(
        CreditScoreHistory.user_id == user.id,
        CreditScoreHistory.recorded_at >= cutoff_date
    ).order_by(CreditScoreHistory.recorded_at).all()
    
    # Also get from predictions
    predictions = Prediction.query.filter(
        Prediction.user_id == user.id,
        Prediction.created_at >= cutoff_date
    ).order_by(Prediction.created_at).all()
    
    trend_data = []
    for item in history:
        trend_data.append({
            'date': item.recorded_at.strftime('%Y-%m-%d'),
            'score': item.cibil_score,
            'source': item.source
        })
    
    for pred in predictions:
        trend_data.append({
            'date': pred.created_at.strftime('%Y-%m-%d'),
            'score': pred.cibil_score,
            'source': 'prediction'
        })
    
    # Sort by date
    trend_data.sort(key=lambda x: x['date'])
    
    return trend_data


def analyze_credit_issues(user):
    """Identify credit issues and provide explanations"""
    issues = []
    
    latest_prediction = Prediction.query.filter_by(user_id=user.id).order_by(Prediction.created_at.desc()).first()
    
    if not latest_prediction:
        return [{
            'icon': '📊',
            'issue': 'No Credit History',
            'explanation': 'Make your first loan prediction to see personalized insights.',
            'severity': 'info'
        }]
    
    cibil = latest_prediction.cibil_score
    
    # Low CIBIL Score
    if cibil < 650:
        issues.append({
            'icon': '🔴',
            'issue': 'Poor Credit Score',
            'explanation': f'Your CIBIL score of {cibil} is below the recommended 650. This significantly reduces loan approval chances.',
            'severity': 'critical',
            'impact': 'Very High'
        })
    elif cibil < 700:
        issues.append({
            'icon': '🟡',
            'issue': 'Below Average Credit Score',
            'explanation': f'Your CIBIL score of {cibil} is below the ideal 750+. Improving this can unlock better interest rates.',
            'severity': 'warning',
            'impact': 'High'
        })
    
    # High Loan Amount
    monthly_income = latest_prediction.income_annum / 12
    loan_amount = latest_prediction.loan_amount
    if loan_amount > monthly_income * 10:
        issues.append({
            'icon': '💰',
            'issue': 'High Loan-to-Income Ratio',
            'explanation': f'Your loan amount (₹{loan_amount:,.0f}) is very high compared to your monthly income (₹{monthly_income:,.0f}).',
            'severity': 'warning',
            'impact': 'High'
        })
    
    # Insufficient Assets
    total_assets = (latest_prediction.residential_assets_value + 
                   latest_prediction.commercial_assets_value + 
                   latest_prediction.luxury_assets_value + 
                   latest_prediction.bank_asset_value)
    if total_assets < loan_amount * 0.3:
        issues.append({
            'icon': '🏠',
            'issue': 'Low Asset Coverage',
            'explanation': f'Your assets (₹{total_assets:,.0f}) are less than 30% of your loan amount. This increases risk perception.',
            'severity': 'warning',
            'impact': 'Medium'
        })
    
    # Many Dependents
    if latest_prediction.no_of_dependents > 3:
        issues.append({
            'icon': '👨‍👩‍👧‍👦',
            'issue': 'Multiple Dependents',
            'explanation': f'With {latest_prediction.no_of_dependents} dependents, your disposable income may be limited.',
            'severity': 'info',
            'impact': 'Low'
        })
    
    if not issues:
        issues.append({
            'icon': '✅',
            'issue': 'Healthy Credit Profile',
            'explanation': 'Your credit profile looks strong! Keep maintaining good financial habits.',
            'severity': 'success',
            'impact': 'None'
        })
    
    return issues


def calculate_loan_readiness(user):
    """Calculate loan readiness percentage"""
    readiness = 0
    factors = []
    
    latest_prediction = Prediction.query.filter_by(user_id=user.id).order_by(Prediction.created_at.desc()).first()
    
    if not latest_prediction:
        return {
            'score': 0,
            'level': 'Not Ready',
            'color': '#e74c3c',
            'factors': [{'name': 'No data available', 'status': False}]
        }
    
    # CIBIL Score Check
    if latest_prediction.cibil_score >= 750:
        readiness += 30
        factors.append({'name': 'Excellent CIBIL Score (750+)', 'status': True})
    elif latest_prediction.cibil_score >= 700:
        readiness += 20
        factors.append({'name': 'Good CIBIL Score (700+)', 'status': True})
    else:
        factors.append({'name': f'CIBIL Score {latest_prediction.cibil_score} (Need 700+)', 'status': False})
    
    # Income Check
    monthly_income = latest_prediction.income_annum / 12
    if monthly_income >= 50000:
        readiness += 25
        factors.append({'name': f'Stable Income ₹{monthly_income:,.0f}/month', 'status': True})
    else:
        factors.append({'name': f'Income ₹{monthly_income:,.0f} (Recommended: ₹50,000+)', 'status': False})
    
    # Loan-to-Income Ratio
    loan_to_income = latest_prediction.loan_amount / (latest_prediction.income_annum / 12)
    if loan_to_income <= 5:
        readiness += 25
        factors.append({'name': 'Manageable Loan Amount', 'status': True})
    else:
        factors.append({'name': 'Loan Amount Too High vs Income', 'status': False})
    
    # Asset Coverage
    total_assets = (latest_prediction.residential_assets_value + 
                   latest_prediction.commercial_assets_value + 
                   latest_prediction.luxury_assets_value + 
                   latest_prediction.bank_asset_value)
    if total_assets >= latest_prediction.loan_amount * 0.5:
        readiness += 20
        factors.append({'name': 'Sufficient Asset Coverage', 'status': True})
    else:
        factors.append({'name': 'Need More Asset Documentation', 'status': False})
    
    # Determine level
    if readiness >= 80:
        level = 'Excellent'
        color = '#2ecc71'
    elif readiness >= 60:
        level = 'Good'
        color = '#3498db'
    elif readiness >= 40:
        level = 'Fair'
        color = '#f39c12'
    else:
        level = 'Needs Improvement'
        color = '#e74c3c'
    
    return {
        'score': readiness,
        'level': level,
        'color': color,
        'factors': factors
    }


def generate_improvement_plan(user):
    """Generate personalized credit improvement plan"""
    plan = []
    
    latest_prediction = Prediction.query.filter_by(user_id=user.id).order_by(Prediction.created_at.desc()).first()
    
    if not latest_prediction:
        return [{
            'priority': 'high',
            'action': 'Complete Your First Loan Prediction',
            'description': 'Use our prediction tool to assess your loan eligibility.',
            'timeline': '1 day',
            'impact': 'Get personalized insights'
        }]
    
    cibil = latest_prediction.cibil_score
    
    # CIBIL Improvement
    if cibil < 700:
        plan.append({
            'priority': 'critical',
            'action': 'Improve Your CIBIL Score',
            'description': 'Pay all dues on time, reduce credit utilization below 30%, avoid multiple loan applications.',
            'timeline': '3-6 months',
            'impact': f'+{750 - cibil} points potential'
        })
    
    # Debt-to-Income
    monthly_income = latest_prediction.income_annum / 12
    emi_estimate = (latest_prediction.loan_amount * 0.09) / 12  # Rough EMI
    if emi_estimate / monthly_income > 0.4:
        plan.append({
            'priority': 'high',
            'action': 'Reduce Loan Amount or Increase Income',
            'description': 'EMI should not exceed 40% of monthly income. Consider reducing loan amount or exploring income sources.',
            'timeline': '1-3 months',
            'impact': 'Improve approval chances by 40%'
        })
    
    # Asset Building
    total_assets = (latest_prediction.residential_assets_value + 
                   latest_prediction.commercial_assets_value + 
                   latest_prediction.luxury_assets_value + 
                   latest_prediction.bank_asset_value)
    if total_assets < latest_prediction.loan_amount * 0.5:
        plan.append({
            'priority': 'medium',
            'action': 'Build Your Asset Base',
            'description': 'Increase savings, document existing assets properly, consider fixed deposits.',
            'timeline': '6-12 months',
            'impact': 'Strengthen application security'
        })
    
    # Documentation
    plan.append({
        'priority': 'low',
        'action': 'Gather Required Documents',
        'description': 'Keep PAN, Aadhaar, salary slips, bank statements, property papers ready.',
        'timeline': '1 week',
        'impact': 'Faster processing'
    })
    
    return plan
