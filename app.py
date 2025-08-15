from flask import Flask, jsonify
import os
import logging

app = Flask(__name__)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/', methods=['GET'])
def health_check():
    logger.info("Health check appelé")
    print("Health check appelé - print direct")
    return jsonify({
        "status": "running",
        "message": "Debug app working - NO Whisper",
        "port": os.environ.get('PORT', 'not set')
    })

@app.route('/test', methods=['GET'])
def test_route():
    logger.info("Test route appelée")
    return jsonify({"test": "OK", "debug": "simple flask app"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
