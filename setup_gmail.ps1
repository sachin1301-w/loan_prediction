# Quick Gmail Setup Script for PowerShell
# Run this to configure Gmail OTP

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   📧 Gmail OTP Configuration Setup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Instructions
Write-Host "STEP 1: Get Your Gmail App Password" -ForegroundColor Yellow
Write-Host "1. Go to: https://myaccount.google.com/apppasswords" -ForegroundColor White
Write-Host "2. Enable 2-Step Verification if needed" -ForegroundColor White
Write-Host "3. Create an App Password (name it 'Loan App')" -ForegroundColor White
Write-Host "4. Copy the 16-character password" -ForegroundColor White
Write-Host ""

# Prompt for Gmail
$gmailUser = Read-Host "Enter your Gmail address (e.g., yourname@gmail.com)"
$gmailPassword = Read-Host "Enter your Gmail App Password (16 characters, no spaces)" -AsSecureString
$gmailPasswordPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($gmailPassword))

Write-Host ""
Write-Host "Setting environment variables..." -ForegroundColor Green

# Set environment variables for current session
$env:GMAIL_USER = $gmailUser
$env:GMAIL_APP_PASSWORD = $gmailPasswordPlain

# Option to make permanent
Write-Host ""
$makePermanent = Read-Host "Make these settings permanent? (Y/N)"

if ($makePermanent -eq "Y" -or $makePermanent -eq "y") {
    [System.Environment]::SetEnvironmentVariable('GMAIL_USER', $gmailUser, 'User')
    [System.Environment]::SetEnvironmentVariable('GMAIL_APP_PASSWORD', $gmailPasswordPlain, 'User')
    Write-Host "✅ Settings saved permanently!" -ForegroundColor Green
    Write-Host "   You may need to restart your terminal/IDE" -ForegroundColor Yellow
} else {
    Write-Host "✅ Settings saved for current session only" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   Configuration Complete! ✅" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Current Settings:" -ForegroundColor Yellow
Write-Host "  GMAIL_USER: $env:GMAIL_USER" -ForegroundColor White
Write-Host "  GMAIL_APP_PASSWORD: ***configured***" -ForegroundColor White
Write-Host ""
Write-Host "Now run your app:" -ForegroundColor Yellow
Write-Host "  python app.py" -ForegroundColor White
Write-Host ""
Write-Host "OTPs will be sent to user emails! 📧" -ForegroundColor Green
