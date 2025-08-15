from flask import Flask, jsonify
import os
import logging

app = Flask(__name__)

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route('/', methods=['GET'])
def health_check():
    logger.info("=== Health check appelé ===")
    print("=== Health check appelé depuis Gunicorn ===")
    return jsonify({
        "status": "running",
        "message": "App working with Gunicorn",
        "port": os.environ.get('PORT', 'not set')
    }), 200

@app.route('/test', methods=['GET'])
def test_route():
    logger.info("=== Test route appelée ===")
    print("=== Test route appelée ===")
    return jsonify({"test": "OK", "debug": "gunicorn flask app"}), 200

# Pour la production avec Gunicorn, on n'utilise pas cette partie
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
