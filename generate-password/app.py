from flask import Flask, request, Response
from flask_cors import CORS
from handler import handle # Importe ta fonction handle unique
import json

app = Flask(__name__)
CORS(app)

@app.route('/function/generate-password', methods=['POST'])
def call_handle():
    # Récupère les données envoyées par le frontend
    body = request.get_data(as_text=True)
    
    # Appelle la fonction handle du handler.py
    # Elle gérera soit 'create_account' (US1) soit 'setup_2fa' (US2)
    result, status = handle(body)
    
    return Response(
        json.dumps(result), 
        status=status, 
        mimetype='application/json'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)