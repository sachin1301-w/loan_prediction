"""
AI Chatbot using Google Gemini AI (FREE & Open Source)
Get your free API key from: https://aistudio.google.com/app/apikey
"""

import os
import json

# Try to use Google Gemini AI (new package)
try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
    # Get API key from environment
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        client = genai.Client(api_key=api_key)
except Exception as e:
    HAS_GEMINI = False
    print(f"Gemini AI not configured: {e}")

# Rule-based responses for demo without API key
DEMO_RESPONSES = {
    'cibil': "Your CIBIL score is crucial! Aim for 750+ for best approval chances. Pay bills on time, keep credit utilization below 30%, and avoid multiple loan applications.",
    'rejected': "Common rejection reasons: Low CIBIL score, high loan-to-income ratio, insufficient assets. Check your prediction details for personalized recommendations.",
    'improve': "To improve approval chances: 1) Increase your CIBIL score, 2) Reduce loan amount, 3) Add a co-applicant, 4) Increase asset values, 5) Extend loan term.",
    'documents': "Required documents: PAN card, Aadhaar, salary slips (3 months), bank statements (6 months), property papers (if any), employment proof.",
    'income': "Include all sources: salary, rental income, business income, investments. Higher income improves approval chances significantly.",
    'assets': "Assets act as security. Include residential property, commercial property, vehicles, gold, investments. Accurate valuation helps.",
    'eligibility': "Use our Calculator tool for quick eligibility check. Generally, EMI shouldn't exceed 40% of monthly income.",
    'approval': "Approval depends on: CIBIL score (35%), Income vs Loan (30%), Assets (20%), Employment (10%), Dependents (5%).",
    'hello': "Hello! I'm your AI loan advisor. I can help with CIBIL scores, loan rejections, approval tips, documents, and financial advice. What would you like to know?",
    'help': "I can assist with: CIBIL score improvement, understanding rejections, required documents, income calculations, asset evaluation, and eligibility checks.",
    'thank': "You're welcome! Feel free to ask anything else about loan applications. I'm here to help!",
}

def get_chatbot_response(user_message, user_context=None):
    """
    Get chatbot response - uses Gemini AI if available, else rule-based
    """
    user_message_lower = user_message.lower()
    
    # Try Gemini AI first
    if HAS_GEMINI and api_key:
        try:
            # Create context for the AI
            system_prompt = """You are a helpful loan advisor assistant for a loan prediction system. 
            Provide clear, concise advice about loan applications, credit scores, and financial planning. 
            Keep responses under 100 words and be encouraging but realistic.
            Focus on: CIBIL scores, loan eligibility, required documents, financial tips."""
            
            context = ""
            if user_context:
                context += f"User: {user_context.get('username', 'User')}\n"
                if user_context.get('last_prediction'):
                    context += f"Last Prediction: {user_context['last_prediction']}\n"
            
            # Use new Gemini API
            response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=f"{system_prompt}\n\n{context}\nUser Question: {user_message}"
            )
            
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"Gemini AI error: {e}")
            # Fall through to rule-based
    
    # Rule-based fallback
    for keyword, response in DEMO_RESPONSES.items():
        if keyword in user_message_lower:
            return response
    
    # Default response
    return ("I can help with: CIBIL scores, loan rejections, approval tips, required documents, income calculation, "
            "asset evaluation, and eligibility checks. What would you like to know?")

def get_loan_advice(prediction_data):
    """Generate specific advice based on prediction data"""
    advice = []
    
    if prediction_data['cibil_score'] < 700:
        advice.append("🎯 Priority: Improve your CIBIL score to 750+ for better approval chances.")
    
    loan_to_income = prediction_data['loan_amount'] / prediction_data['income_annum']
    if loan_to_income > 4:
        advice.append("💡 Your loan amount is high relative to income. Consider reducing it or increasing income sources.")
    
    total_assets = (prediction_data.get('residential_assets_value', 0) + 
                   prediction_data.get('commercial_assets_value', 0) + 
                   prediction_data.get('luxury_assets_value', 0))
    if total_assets < prediction_data['loan_amount'] * 0.3:
        advice.append("🏠 Building assets will strengthen your application. Consider increasing asset documentation.")
    
    if not advice:
        advice.append("✅ Your profile looks strong! Keep maintaining good financial habits.")
    
    return advice
