import sys
sys.path.insert(0, '.')
from datetime import datetime
from utils import format_date, get_current_language

# Définir la langue sur français
from flask import Flask, session
app = Flask(__name__)
app.secret_key = 'test'

with app.test_request_context():
    session['language'] = 'fr'
    
    # Tester le formatage des dates
    date_test = datetime(2025, 8, 10)  # Samedi 10 août 2025
    date_test2 = datetime(2025, 8, 18)  # Lundi 18 août 2025
    
    print("Langue courante:", get_current_language())
    print("Date 1:", format_date(date_test))
    print("Date 1 avec heure:", format_date(date_test, include_time=True))
    print("Date 2:", format_date(date_test2))
    print("Date 2 avec heure:", format_date(date_test2, include_time=True))
