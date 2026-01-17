import io
import json
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import pandas as pd


def generate_recommendations(prediction_data, result):
    """Generate smart recommendations based on prediction"""
    recommendations = []
    tips = []
    
    cibil = prediction_data.get('cibil_score', 0)
    loan_amount = prediction_data.get('loan_amount', 0)
    income = prediction_data.get('income_annum', 0)
    assets_total = (
        prediction_data.get('residential_assets_value', 0) +
        prediction_data.get('commercial_assets_value', 0) +
        prediction_data.get('luxury_assets_value', 0) +
        prediction_data.get('bank_asset_value', 0)
    )
    
    if 'Rejected' in result:
        recommendations.append({
            'title': 'Credit Score Improvement',
            'icon': '📈',
            'priority': 'high',
            'items': []
        })
        
        if cibil < 750:
            target_score = 750
            recommendations[0]['items'].append(
                f"Your CIBIL score is {cibil}. Aim for {target_score}+ for better approval chances."
            )
            recommendations[0]['items'].append(
                f"Pay all bills on time for the next 6-12 months to improve your score by {target_score - cibil} points."
            )
        
        # Loan amount recommendation
        if loan_amount > income * 3:
            suggested_amount = int(income * 2.5)
            recommendations.append({
                'title': 'Loan Amount Adjustment',
                'icon': '💰',
                'priority': 'high',
                'items': [
                    f"Your requested amount (₹{loan_amount:,.0f}) is high relative to your income.",
                    f"Consider reducing to ₹{suggested_amount:,.0f} for better approval odds.",
                    f"This keeps your loan-to-income ratio within acceptable limits."
                ]
            })
        
        # Asset building
        if assets_total < loan_amount * 0.5:
            recommendations.append({
                'title': 'Build Your Assets',
                'icon': '🏠',
                'priority': 'medium',
                'items': [
                    f"Total assets: ₹{assets_total:,.0f}. Banks prefer assets worth at least 50% of the loan.",
                    f"Consider building savings or assets worth ₹{int(loan_amount * 0.5 - assets_total):,.0f} more.",
                    "Assets show financial stability and improve approval chances significantly."
                ]
            })
    else:
        # Approved - optimization tips
        recommendations.append({
            'title': 'Congratulations! Optimization Tips',
            'icon': '🎉',
            'priority': 'info',
            'items': [
                "Your loan is likely to be approved! Here are some tips:",
                "Maintain your CIBIL score by making timely payments.",
                "Keep your credit utilization below 30% of available credit.",
                "Consider setting up auto-pay to never miss a payment."
            ]
        })
        
        if cibil >= 800:
            recommendations[0]['items'].append(
                "Excellent CIBIL score! You may be eligible for lower interest rates."
            )
    
    # General tips
    tips = [
        "Pay all credit card bills in full each month",
        "Don't apply for multiple loans simultaneously",
        "Keep old credit accounts active (longer credit history helps)",
        "Check your credit report annually for errors",
        "Maintain a healthy debt-to-income ratio (below 40%)"
    ]
    
    return recommendations, tips


def calculate_feature_importance(prediction_data):
    """Calculate which factors contributed most to the decision"""
    # Simplified feature importance (in a real app, use model.feature_importances_)
    features = {
        'CIBIL Score': min(prediction_data.get('cibil_score', 0) / 900 * 100, 100),
        'Income Level': min(prediction_data.get('income_annum', 0) / 2000000 * 100, 100),
        'Total Assets': min((prediction_data.get('residential_assets_value', 0) + 
                           prediction_data.get('commercial_assets_value', 0) + 
                           prediction_data.get('luxury_assets_value', 0) + 
                           prediction_data.get('bank_asset_value', 0)) / 5000000 * 100, 100),
        'Loan Amount': 100 - min(prediction_data.get('loan_amount', 0) / 5000000 * 100, 100),
        'Employment': 80 if prediction_data.get('self_employed') == 'No' else 60,
        'Education': 85 if prediction_data.get('education') == 'Graduate' else 65,
    }
    
    # Normalize to percentages
    total = sum(features.values())
    if total > 0:
        features = {k: (v / total * 100) for k, v in features.items()}
    
    return dict(sorted(features.items(), key=lambda x: x[1], reverse=True))


def export_to_pdf(predictions, user):
    """Generate PDF report of predictions"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#764ba2'),
        spaceAfter=12
    )
    
    # Title
    story.append(Paragraph("🏦 Loan Prediction Report", title_style))
    story.append(Spacer(1, 0.3*inch))
    
    # User info
    user_info = f"<b>Generated for:</b> {user.username} ({user.email})<br/>"
    user_info += f"<b>Date:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br/>"
    user_info += f"<b>Total Predictions:</b> {len(predictions)}"
    story.append(Paragraph(user_info, styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Summary statistics
    if predictions:
        approved = sum(1 for p in predictions if 'Approved' in p.result)
        avg_amount = sum(p.loan_amount for p in predictions) / len(predictions)
        avg_cibil = sum(p.cibil_score for p in predictions) / len(predictions)
        
        story.append(Paragraph("Summary Statistics", heading_style))
        summary_data = [
            ['Metric', 'Value'],
            ['Total Applications', str(len(predictions))],
            ['Approved', str(approved)],
            ['Rejected', str(len(predictions) - approved)],
            ['Approval Rate', f"{(approved/len(predictions)*100):.1f}%"],
            ['Average Loan Amount', f"₹{avg_amount:,.0f}"],
            ['Average CIBIL Score', f"{avg_cibil:.0f}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
    
    # Detailed predictions
    story.append(Paragraph("Prediction Details", heading_style))
    
    for pred in predictions[:10]:  # Limit to 10 most recent
        pred_data = [
            ['Date', pred.created_at.strftime('%Y-%m-%d %H:%M')],
            ['Loan Amount', f"₹{pred.loan_amount:,.0f}"],
            ['Income', f"₹{pred.income_annum:,.0f}"],
            ['CIBIL Score', str(pred.cibil_score)],
            ['Result', pred.result],
            ['Probability', f"{pred.probability}%"],
        ]
        
        pred_table = Table(pred_data, colWidths=[2*inch, 4*inch])
        pred_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(pred_table)
        story.append(Spacer(1, 0.2*inch))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    footer = "This report is generated automatically by the Loan Prediction System. "
    footer += "For queries, contact your administrator."
    story.append(Paragraph(footer, styles['Italic']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


def export_to_excel(predictions, user):
    """Generate Excel report of predictions"""
    buffer = io.BytesIO()
    
    # Create DataFrame
    data = []
    for pred in predictions:
        data.append({
            'Date': pred.created_at.strftime('%Y-%m-%d %H:%M'),
            'Loan Amount': pred.loan_amount,
            'Income': pred.income_annum,
            'CIBIL Score': pred.cibil_score,
            'Education': pred.education,
            'Self Employed': pred.self_employed,
            'Dependents': pred.no_of_dependents,
            'Loan Term': pred.loan_term,
            'Residential Assets': pred.residential_assets_value,
            'Commercial Assets': pred.commercial_assets_value,
            'Luxury Assets': pred.luxury_assets_value,
            'Bank Assets': pred.bank_asset_value,
            'Result': pred.result,
            'Probability': pred.probability
        })
    
    df = pd.DataFrame(data)
    
    # Write to Excel
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Predictions', index=False)
        
        # Add summary sheet
        summary_data = {
            'Metric': ['Total Predictions', 'Approved', 'Rejected', 'Approval Rate', 
                      'Avg Loan Amount', 'Avg CIBIL Score'],
            'Value': [
                len(predictions),
                sum(1 for p in predictions if 'Approved' in p.result),
                sum(1 for p in predictions if 'Rejected' in p.result),
                f"{sum(1 for p in predictions if 'Approved' in p.result)/len(predictions)*100:.1f}%" if predictions else "0%",
                f"₹{sum(p.loan_amount for p in predictions)/len(predictions):,.0f}" if predictions else "₹0",
                f"{sum(p.cibil_score for p in predictions)/len(predictions):.0f}" if predictions else "0"
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    buffer.seek(0)
    return buffer
