from flask import Flask, request, Response
from flask_cors import CORS
from handler import handle
import json

app = Flask(__name__)
CORS(app)

@app.route('/function/generate-password', methods=['POST'])
def generate_password():
    body = request.get_data(as_text=True)
    result, status = handle(body)
    return Response(json.dumps(result), status=status, mimetype='application/json')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
