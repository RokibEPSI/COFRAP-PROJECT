from flask import Flask, request
import handler

app = Flask(__name__)

class OpenFaaSEvent:
    def __init__(self, req):
        self.body = req.get_data()
        self.method = req.method
        self.path = req.path
        self.headers = dict(req.headers)

@app.route('/', defaults={'path': ''}, methods=['POST', 'GET', 'OPTIONS'])
@app.route('/<path:path>', methods=['POST', 'GET', 'OPTIONS'])
def catch_all(path):
    # Mapping de la requête HTTP vers l'objet Event natif attendu par ton handler
    event = OpenFaaSEvent(request)
    
    # Exécution de la fonction de sécurité PULSAR
    res = handler.handle(event, None)
    
    status_code = res.get("statusCode", 200)
    headers = res.get("headers", {})
    body = res.get("body", "")
    
    return body, status_code, headers

if __name__ == '__main__':
    if __name__ == '__main__':
     app.run(host='0.0.0.0', port=8080) # Écoute directe sur le port OpenFaaS