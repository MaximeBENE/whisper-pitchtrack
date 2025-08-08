from flask import Flask, request, jsonify
import whisper
import tempfile
import os
from werkzeug.utils import secure_filename
import logging

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger le modèle Whisper au démarrage (base pour équilibre vitesse/qualité)
logger.info("Chargement du modèle Whisper...")
model = whisper.load_model("base")
logger.info("Modèle Whisper chargé avec succès")

ALLOWED_EXTENSIONS = {'wav', 'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'webm', 'ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "running",
        "message": "Whisper Microservice is ready",
        "model": "base"
    })

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    try:
        # Vérifier si un fichier a été envoyé
        if 'audio' not in request.files:
            return jsonify({"error": "Aucun fichier audio fourni"}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({"error": "Nom de fichier vide"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Format de fichier non supporté"}), 400

        # Paramètres optionnels
        language = request.form.get('language', 'auto')  # 'fr', 'en', ou 'auto'
        include_timestamps = request.form.get('timestamps', 'true').lower() == 'true'
        
        # Sauvegarder temporairement le fichier
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            filename = secure_filename(file.filename)
            temp_path = temp_file.name
            file.save(temp_path)
            
            logger.info(f"Transcription en cours pour: {filename}")
            
            # Options de transcription
            transcribe_options = {}
            if language != 'auto':
                transcribe_options['language'] = language
            
            # Transcription avec Whisper
            result = model.transcribe(temp_path, **transcribe_options)
            
            # Nettoyage du fichier temporaire
            os.unlink(temp_path)
            
            # Préparer la réponse
            response_data = {
                "text": result["text"],
                "language": result["language"],
                "duration": result.get("duration", 0)
            }
            
            if include_timestamps:
                segments = []
                for segment in result["segments"]:
                    segments.append({
                        "start": round(segment["start"], 2),
                        "end": round(segment["end"], 2),
                        "text": segment["text"].strip(),
                        "duration": round(segment["end"] - segment["start"], 2)
                    })
                response_data["segments"] = segments
                
                # Calcul du temps de parole total (sans les silences)
                total_speech_time = sum(seg["duration"] for seg in segments)
                response_data["total_speech_time"] = round(total_speech_time, 2)
                response_data["silence_time"] = round(result.get("duration", 0) - total_speech_time, 2)
            
            logger.info(f"Transcription terminée: {len(result['text'])} caractères")
            return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"Erreur lors de la transcription: {str(e)}")
        return jsonify({"error": f"Erreur de transcription: {str(e)}"}), 500

@app.route('/transcribe-url', methods=['POST'])
def transcribe_from_url():
    try:
        data = request.get_json()
        audio_url = data.get('url')
        
        if not audio_url:
            return jsonify({"error": "URL audio requise"}), 400
        
        language = data.get('language', 'auto')
        include_timestamps = data.get('timestamps', True)
        
        logger.info(f"Transcription depuis URL: {audio_url}")
        
        # Options de transcription
        transcribe_options = {}
        if language != 'auto':
            transcribe_options['language'] = language
        
        # Transcription directe depuis l'URL
        result = model.transcribe(audio_url, **transcribe_options)
        
        # Préparer la réponse
        response_data = {
            "text": result["text"],
            "language": result["language"],
            "duration": result.get("duration", 0)
        }
        
        if include_timestamps:
            segments = []
            for segment in result["segments"]:
                segments.append({
                    "start": round(segment["start"], 2),
                    "end": round(segment["end"], 2),
                    "text": segment["text"].strip(),
                    "duration": round(segment["end"] - segment["start"], 2)
                })
            response_data["segments"] = segments
            
            # Calcul du temps de parole total
            total_speech_time = sum(seg["duration"] for seg in segments)
            response_data["total_speech_time"] = round(total_speech_time, 2)
            response_data["silence_time"] = round(result.get("duration", 0) - total_speech_time, 2)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Erreur lors de la transcription URL: {str(e)}")
        return jsonify({"error": f"Erreur de transcription: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
