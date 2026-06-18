import os
from app import app

if __name__ == '__main__':
    # debug uniquement hors production (la prod tourne via gunicorn, qui n'exécute pas ce bloc)
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get('FLASK_ENV') != 'production')
