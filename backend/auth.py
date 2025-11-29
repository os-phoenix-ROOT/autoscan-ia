"""
Sistema de autenticación para AutoScan IA con verificación de email
"""
import os
import sqlite3
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

# Configuración
auth_bp = Blueprint('auth', __name__)
DATABASE = 'backend/users.db'

# Configuración de email - USAR VARIABLES DE ENTORNO EN PRODUCCIÓN
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': os.environ.get('EMAIL_SENDER', 'scriptluisch@gmail.com'),
    'sender_password': os.environ.get('EMAIL_PASSWORD', 'czgbxznprzxbigad'),
    'app_url': os.environ.get('APP_URL', 'https://autoscan-ia.onrender.com')
}

def init_db():
    """Inicializar base de datos de usuarios con manejo de actualizaciones"""
    os.makedirs('backend', exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Crear tabla users si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            plan TEXT DEFAULT 'basic',
            analyses_count INTEGER DEFAULT 0,
            email_verified BOOLEAN DEFAULT FALSE,
            verification_token TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Verificar y agregar columnas faltantes
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'email_verified' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE")
            logger.info("✅ Columna 'email_verified' agregada")
        
        if 'verification_token' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN verification_token TEXT")
            logger.info("✅ Columna 'verification_token' agregada")
            
        # Marcar usuarios existentes como verificados
        cursor.execute("UPDATE users SET email_verified = TRUE WHERE email_verified IS NULL")
        
    except Exception as e:
        logger.warning(f"⚠️ Error verificando estructura de tabla: {e}")
    
    conn.commit()
    conn.close()
    logger.info("✅ Base de datos inicializada/actualizada")

def hash_password(password):
    """Hashear contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def send_verification_email(user_email, first_name, verification_token):
    """Enviar email de verificación"""
    try:
        subject = "Verifica tu cuenta - AutoScan IA"
        
        verification_url = f"{EMAIL_CONFIG['app_url']}/api/auth/verify-email?token={verification_token}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #3b82f6; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9fafb; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #3b82f6; color: white; 
                         text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>AutoScan IA</h1>
                    <p>Verificación de Cuenta</p>
                </div>
                <div class="content">
                    <h2>Hola {first_name},</h2>
                    <p>Gracias por registrarte en AutoScan IA. Para activar tu cuenta, por favor verifica tu dirección de email.</p>
                    
                    <div style="text-align: center;">
                        <a href="{verification_url}" class="button">Verificar Mi Email</a>
                    </div>
                    
                    <p>Si el botón no funciona, copia y pega este enlace en tu navegador:</p>
                    <p style="word-break: break-all; background: #e5e7eb; padding: 10px; border-radius: 5px;">
                        {verification_url}
                    </p>
                    
                    <p><strong>Este enlace expirará en 24 horas.</strong></p>
                    
                    <p>Si no te registraste en AutoScan IA, puedes ignorar este mensaje.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 AutoScan IA. Todos los derechos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
        
        logger.info(f"✅ Email de verificación enviado a {user_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email a {user_email}: {e}")
        return False

@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    """Registro de usuario con verificación de email"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ['email', 'password', 'firstName', 'lastName']):
            return jsonify({"error": "Datos incompletos"}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        first_name = data['firstName'].strip()
        last_name = data['lastName'].strip()
        
        if len(password) < 6:
            return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400
        
        if '@' not in email:
            return jsonify({"error": "Email inválido"}), 400
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "El email ya está registrado"}), 400
        
        password_hash = hash_password(password)
        verification_token = secrets.token_urlsafe(32)
        
        cursor.execute('''
            INSERT INTO users (email, password_hash, first_name, last_name, verification_token)
            VALUES (?, ?, ?, ?, ?)
        ''', (email, password_hash, first_name, last_name, verification_token))
        
        user_id = cursor.lastrowid
        
        email_sent = send_verification_email(email, first_name, verification_token)
        
        if not email_sent:
            logger.warning(f"⚠️ Usuario {email} registrado pero email no enviado")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Cuenta creada exitosamente. Por favor verifica tu email para activar tu cuenta.",
            "email_sent": email_sent,
            "user": {
                "id": user_id,
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "plan": "basic",
                "email_verified": False
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Error en el registro: {str(e)}"}), 500

@auth_bp.route('/api/auth/verify-email', methods=['GET'])
def verify_email():
    """Verificar email del usuario"""
    try:
        token = request.args.get('token')
        
        if not token:
            error_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error de Verificación - AutoScan IA</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .error { color: #ef4444; font-size: 24px; margin: 20px 0; }
                    .button { display: inline-block; padding: 12px 24px; background: #3b82f6; 
                             color: white; text-decoration: none; border-radius: 5px; margin: 20px; }
                </style>
            </head>
            <body>
                <div class="error">❌ Enlace inválido o expirado</div>
                <p>El enlace de verificación no es válido o ya ha sido utilizado.</p>
                <a href="/login.html" class="button">Ir al Login</a>
            </body>
            </html>
            """
            return error_html, 400
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, first_name FROM users 
            WHERE verification_token = ? AND email_verified = FALSE
        ''', (token,))
        
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            error_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Error de Verificación - AutoScan IA</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .error { color: #ef4444; font-size: 24px; margin: 20px 0; }
                    .button { display: inline-block; padding: 12px 24px; background: #3b82f6; 
                             color: white; text-decoration: none; border-radius: 5px; margin: 20px; }
                </style>
            </head>
            <body>
                <div class="error">❌ Enlace inválido o expirado</div>
                <p>El enlace de verificación no es válido o ya ha sido utilizado.</p>
                <a href="/login.html" class="button">Ir al Login</a>
            </body>
            </html>
            """
            return error_html, 400
        
        user_id, user_email, first_name = user
        
        cursor.execute('''
            UPDATE users 
            SET email_verified = TRUE, verification_token = NULL 
            WHERE id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        
        # ✅ CORRECCIÓN: Página de éxito SIN redirección automática al dashboard
        success_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Email Verificado - AutoScan IA</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .success {{ color: #10b981; font-size: 24px; margin: 20px 0; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #3b82f6; 
                         color: white; text-decoration: none; border-radius: 5px; margin: 10px; }}
                .info {{ color: #6b7280; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="success">✅ ¡Email verificado exitosamente!</div>
            <p>Hola <strong>{first_name}</strong>, tu cuenta ha sido activada correctamente.</p>
            
            <div class="info">
                <p>Ahora puedes iniciar sesión con tu email y contraseña.</p>
            </div>
            
            <div>
                <a href="/login.html" class="button">Iniciar Sesión</a>
                <a href="/" class="button" style="background: #6b7280;">Ir al Inicio</a>
            </div>
        </body>
        </html>
        """
        
        return success_html, 200
        
    except Exception as e:
        return jsonify({"error": f"Error verificando email: {str(e)}"}), 500

@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Inicio de sesión - requiere email verificado"""
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ['email', 'password']):
            return jsonify({"error": "Datos incompletos"}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, password_hash, first_name, last_name, plan, analyses_count, email_verified 
            FROM users WHERE email = ?
        ''', (email,))
        
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({"error": "Credenciales incorrectas"}), 401
        
        user_id, user_email, stored_hash, first_name, last_name, plan, analyses_count, email_verified = user
        
        if hash_password(password) != stored_hash:
            conn.close()
            return jsonify({"error": "Credenciales incorrectas"}), 401
        
        if not email_verified:
            conn.close()
            return jsonify({"error": "Por favor verifica tu email antes de iniciar sesión"}), 401
        
        session_id = secrets.token_hex(32)
        cursor.execute('''
            INSERT INTO user_sessions (session_id, user_id)
            VALUES (?, ?)
        ''', (session_id, user_id))
        
        cursor.execute('''
            DELETE FROM user_sessions 
            WHERE created_at < datetime('now', '-30 days')
        ''')
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Sesión iniciada exitosamente",
            "session_id": session_id,
            "user": {
                "id": user_id,
                "email": user_email,
                "firstName": first_name,
                "lastName": last_name,
                "plan": plan,
                "analysesCount": analyses_count,
                "email_verified": True
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Error en el login: {str(e)}"}), 500

@auth_bp.route('/api/auth/verify', methods=['POST'])
def verify_session():
    """Verificar sesión activa"""
    try:
        data = request.get_json()
        
        if not data or 'session_id' not in data:
            return jsonify({"error": "Sesión requerida"}), 401
        
        session_id = data['session_id']
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.id, u.email, u.first_name, u.last_name, u.plan, u.analyses_count, u.email_verified
            FROM users u
            JOIN user_sessions s ON u.id = s.user_id
            WHERE s.session_id = ? AND s.created_at > datetime('now', '-7 days')
        ''', (session_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({"error": "Sesión inválida o expirada"}), 401
        
        user_id, email, first_name, last_name, plan, analyses_count, email_verified = user
        
        return jsonify({
            "valid": True,
            "user": {
                "id": user_id,
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "plan": plan,
                "analysesCount": analyses_count,
                "email_verified": email_verified
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Error verificando sesión: {str(e)}"}), 500

@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    """Cerrar sesión"""
    try:
        data = request.get_json()
        
        if data and 'session_id' in data:
            session_id = data['session_id']
            
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.close()
        
        return jsonify({"success": True, "message": "Sesión cerrada"})
        
    except Exception as e:
        return jsonify({"error": f"Error cerrando sesión: {str(e)}"}), 500

# Inicializar base de datos al importar
init_db()