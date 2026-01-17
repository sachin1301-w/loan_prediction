# 🏦 Loan Prediction System

A comprehensive loan prediction web application with ML-powered analytics, built for hackathon demonstration.

## 🚀 Features

### Core Functionality
- **User Authentication**: Secure registration and login with OTP verification
- **Loan Prediction**: ML-based loan approval prediction with detailed insights
- **Smart Dashboard**: Track prediction history with visual analytics
- **Quick Calculator**: Instant eligibility check with interactive sliders
- **Advanced Analytics**: Deep dive into prediction patterns with multiple chart types

### Advanced Features
- **ML Explainability**: Feature importance visualization showing how each factor affects predictions
- **Smart Recommendations**: Personalized suggestions to improve loan approval chances
- **Data Export**: Export prediction history to PDF and Excel formats
- **Real-time Visualization**: Interactive charts using Chart.js
- **Responsive Design**: Modern, professional UI that works on all devices

## 🛠️ Tech Stack

- **Backend**: Flask 3.1, Python 3.x
- **Database**: SQLite with SQLAlchemy ORM
- **ML**: Scikit-learn, Pandas, NumPy
- **Visualization**: Chart.js, Plotly
- **Export**: ReportLab (PDF), OpenPyXL (Excel)
- **Authentication**: Flask-Login with OTP verification

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd loan_prediction
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Access the app**
   Open your browser and navigate to `http://127.0.0.1:5000`

## 🎯 Usage

### Getting Started
1. **Register**: Create a new account with your email
2. **Verify OTP**: Check the terminal/console for your OTP code
3. **Login**: Access your dashboard with credentials

### Making Predictions
1. Navigate to **Predict** section
2. Fill in loan application details:
   - Personal: Number of dependents, education, employment
   - Financial: Income, loan amount, loan term, CIBIL score
   - Assets: Residential, commercial, luxury assets
3. Click **Predict** to get instant results
4. View personalized recommendations and feature importance

### Using the Calculator
1. Go to **Calculator** section
2. Adjust sliders for income, loan amount, and CIBIL score
3. Get instant eligibility score

### Viewing Analytics
1. Visit **Analytics** section
2. Explore:
   - Approval rate distribution (pie chart)
   - Loan amount trends (line chart)
   - CIBIL score analysis (scatter plot)

### Exporting Data
1. Go to **History** section
2. View all past predictions
3. Click **Export to PDF** or **Export to Excel**

## 📊 ML Model

The application uses a pre-trained machine learning model (`loan_model(2).pkl`) that analyzes:
- Applicant demographics
- Financial indicators
- Credit history (CIBIL score)
- Asset ownership
- Loan parameters

The model provides binary classification (Approved/Rejected) with confidence scores and feature importance rankings.

## 🔒 Security Features

- Password hashing with Werkzeug
- Session management with Flask-Login
- OTP-based verification (console display for demo)
- User data isolation
- CSRF protection

## 🎨 UI/UX Highlights

- Modern gradient backgrounds
- Smooth animations and transitions
- Color-coded feedback (green for approval, red for rejection)
- Interactive data visualizations
- Mobile-responsive design
- Professional typography and spacing

## 📁 Project Structure

```
loan_prediction/
├── app.py                 # Main Flask application
├── models.py             # Database models
├── utils.py              # Helper functions (recommendations, exports)
├── otp_utils.py          # OTP generation and verification
├── requirements.txt      # Python dependencies
├── runtime.txt          # Python version
├── loan_model(2).pkl    # ML model
├── templates/           # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── verify_otp.html
│   ├── dashboard.html
│   ├── predict.html
│   ├── calculator.html
│   ├── analytics.html
│   └── history.html
└── loan_approval_dataset.csv
```

## 🚧 Development Notes

- OTP codes are displayed in the terminal for demonstration purposes
- SQLite database is created automatically on first run
- ML model loads lazily on first prediction request
- All timestamps use UTC

## 🤝 Contributing

This is a hackathon project. Feel free to fork and enhance!

## 📝 License

MIT License - feel free to use this project for learning and development.

## 👨‍💻 Author

Built for hackathon demonstration

## 🙏 Acknowledgments

- Dataset: Loan approval dataset
- ML Framework: Scikit-learn
- Visualization: Chart.js
