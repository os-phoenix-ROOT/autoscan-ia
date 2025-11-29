#!/usr/bin/env python3
"""
Servidor principal de AutoScan IA - Versión Profesional
"""
import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from backend.damage_analyzer import DamageAnalyzer
from backend.auth import auth_bp
from flask_cors import CORS

# Configuración
app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app, 
     resources={
         r"/api/*": {
             "origins": ["http://localhost:5000", "http://127.0.0.1:5000"],
             "methods": ["GET", "POST", "PUT", "DELETE"],
             "allow_headers": ["Content-Type", "Authorization"]
         }
     },
     supports_credentials=True)

# ✅ REGISTRAR Blueprint DESPUÉS de crear la app
app.register_blueprint(auth_bp)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar el analizador de daños
try:
    analyzer = DamageAnalyzer()
    logger.info("✅ Analizador de daños inicializado correctamente")
except Exception as e:
    logger.error(f"❌ Error inicializando el analizador: {e}")
    analyzer = None

# Configuración
UPLOAD_FOLDER = 'backend/temp_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Servir archivos estáticos del frontend
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

# API Routes
@app.route('/api/')
def api_index():
    """Endpoint principal de la API - Documentación"""
    base_url = request.url_root.rstrip('/')
    
    endpoints = {
        "service": "AutoScan IA API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "health": f"{base_url}/api/health",
            "analyze": f"{base_url}/api/analyze",
            "stats": f"{base_url}/api/stats",
            "auth_register": f"{base_url}/api/auth/register",
            "auth_login": f"{base_url}/api/auth/login",
            "auth_verify": f"{base_url}/api/auth/verify",
            "auth_logout": f"{base_url}/api/auth/logout"
        },
        "description": "API profesional para análisis de daños vehiculares con IA",
        "documentation": "Visita / para la interfaz web completa"
    }
    
    return jsonify(endpoints)

@app.route('/api/health')
def health_check():
    """Health check del servicio"""
    ia_status = "healthy" if analyzer and analyzer.model_loaded else "unavailable"
    return jsonify({
        "status": "healthy",
        "ia_status": ia_status,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_vehicle():
    """
    Endpoint principal para análisis de vehículo
    """
    if analyzer is None:
        return jsonify({
            "error": "Servicio de IA no disponible",
            "status": "error"
        }), 503

    try:
        # Verificar imágenes
        required_angles = ['frontal', 'lateral-derecho', 'lateral-izquierdo', 'trasero']
        image_files = {}
        
        for angle in required_angles:
            if angle not in request.files:
                return jsonify({
                    "error": f"Falta imagen: {angle}",
                    "status": "error"
                }), 400
            
            file = request.files[angle]
            if file.filename == '':
                return jsonify({
                    "error": f"Archivo vacío: {angle}",
                    "status": "error"
                }), 400
            
            # Validar tipo de archivo
            if not file.content_type.startswith('image/'):
                return jsonify({
                    "error": f"Archivo no es imagen: {angle}",
                    "status": "error"
                }), 400
            
            image_files[angle] = file

        logger.info(f"📨 Análisis solicitado con {len(image_files)} imágenes")

        # Guardar imágenes temporalmente
        saved_paths = {}
        for angle, file in image_files.items():
            filename = f"{angle}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            saved_paths[angle] = filepath

        # Procesar con IA
        logger.info("🔮 Procesando imágenes con IA...")
        results = analyzer.analyze_vehicle(saved_paths)
        
        # Limpiar archivos temporales
        for filepath in saved_paths.values():
            try:
                os.remove(filepath)
            except Exception as e:
                logger.warning(f"No se pudo eliminar {filepath}: {e}")

        logger.info("✅ Análisis completado exitosamente")
        
        return jsonify({
            "status": "success",
            "results": results,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"❌ Error en análisis: {str(e)}")
        
        # Limpiar archivos en caso de error
        if 'saved_paths' in locals():
            for filepath in saved_paths.values():
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except:
                    pass
        
        return jsonify({
            "error": f"Error procesando las imágenes: {str(e)}",
            "status": "error"
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Endpoint para obtener estadísticas del servicio"""
    return jsonify({
        "status": "online",
        "service": "AutoScan IA",
        "version": "1.0.0",
        "model_loaded": analyzer.model_loaded if analyzer else False,
        "timestamp": datetime.now().isoformat()
    })

# Error handlers
@app.errorhandler(413)
def too_large(e):
    return jsonify({
        "error": "Archivo demasiado grande. Máximo 16MB por imagen.",
        "status": "error"
    }), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint no encontrado",
        "status": "error"
    }), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "error": "Error interno del servidor",
        "status": "error"
    }), 500

# Al final de app.py, cambia esto:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )