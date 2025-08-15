from flask import Flask, jsonify, request, abort
from tempfile import NamedTemporaryFile
import os
import logging
import whisper
import torch

app = Flask(__name__)

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Whisper
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {DEVICE}")

# Chargement du modèle Whisper au démarrage
try:
    # Utilisez 'base' pour un bon compromis vitesse/précision
    # Ou 'tiny' pour plus de rapidité, 'small', 'medium', 'large' pour plus de précision
    model = whisper.load_model("base", device=DEVICE)
    logger.info("Modèle Whisper chargé avec succès")
except Exception as e:
    logger.error(f"Erreur lors du chargement du modèle Whisper: {e}")
    model = None

@app.route('/', methods=['GET'])
def health_check():
    logger.info("=== Health check appelé ===")
    print("=== Health check appelé depuis Gunicorn ===")
    return jsonify({
        "status": "running",
        "message": "Whisper API working with Gunicorn",
        "port": os.environ.get('PORT', 'not set'),
        "device": DEVICE,
        "model_loaded": model is not None
    }), 200

@app.route('/test', methods=['GET'])
def test_route():
    logger.info("=== Test route appelée ===")
    print("=== Test route appelée ===")
    return jsonify({
        "test": "OK", 
        "debug": "gunicorn flask app with whisper",
        "model_status": "loaded" if model else "not loaded"
    }), 200

@app.route('/whisper', methods=['POST'])
def transcribe_audio():
    """
    Endpoint pour transcrire un fichier audio
    Accepte: fichier audio en form-data avec la clé 'file'
    Retourne: JSON avec la transcription
    """
    logger.info("=== Transcription demandée ===")
    
    if not model:
        logger.error("Modèle Whisper non disponible")
        return jsonify({"error": "Whisper model not loaded"}), 500
    
    if not request.files:
        logger.error("Aucun fichier fourni")
        return jsonify({"error": "No file provided"}), 400
    
    results = []
    
    try:
        # Traitement de chaque fichier uploadé
        for filename, file_handle in request.files.items():
            logger.info(f"Traitement du fichier: {filename}")
            
            # Création d'un fichier temporaire
            with NamedTemporaryFile(delete=False) as temp_file:
                file_handle.save(temp_file.name)
                
                logger.info("Début de la transcription...")
                
                # Transcription avec Whisper
                result = model.transcribe(temp_file.name)
                
                logger.info("Transcription terminée")
                
                # Stockage du résultat
                results.append({
                    'filename': filename,
                    'transcript': result['text'],
                    'language': result.get('language', 'unknown'),
                    'segments': len(result.get('segments', []))
                })
                
                # Nettoyage du fichier temporaire
                os.unlink(temp_file.name)
        
        logger.info(f"Transcription réussie pour {len(results)} fichier(s)")
        return jsonify({'results': results}), 200
        
    except Exception as e:
        logger.error(f"Erreur lors de la transcription: {e}")
        return jsonify({"error": f"Transcription failed: {str(e)}"}), 500

@app.route('/models', methods=['GET'])
def available_models():
    """Endpoint pour lister les modèles Whisper disponibles"""
    models = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
    current_model = "base" if model else None
    
    return jsonify({
        "available_models": models,
        "current_model": current_model,
        "device": DEVICE
    }), 200

@app.before_request
def log_request_info():
    logger.info(f'=== Nouvelle requête: {request.method} {request.path} ===')

@app.after_request
def log_response_info(response):
    logger.info(f'=== Réponse envoyée: {response.status_code} ===')
    return response

# Pour la production avec Gunicorn, cette partie ne sera pas utilisée
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Démarrage en mode développement sur le port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
