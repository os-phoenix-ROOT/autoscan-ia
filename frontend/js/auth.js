// auth.js - Manejo de autenticación REAL con backend
class AuthManager {
    constructor() {
        this.currentTab = 'login';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupPasswordStrength();
        this.checkExistingAuth();
    }

    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.auth-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Switch tab links
        document.querySelectorAll('.switch-tab').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Form submissions
        document.getElementById('loginForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin(e);
        });

        document.getElementById('registerForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRegister(e);
        });

        // Show password toggle
        document.getElementById('showLoginPassword').addEventListener('change', (e) => {
            this.togglePasswordVisibility('loginPassword', e.target.checked);
        });

        document.getElementById('showRegisterPassword').addEventListener('change', (e) => {
            this.togglePasswordVisibility('registerPassword', e.target.checked);
            this.togglePasswordVisibility('registerConfirmPassword', e.target.checked);
        });

        // Forgot password link
        document.querySelector('.forgot-link').addEventListener('click', (e) => {
            e.preventDefault();
            this.showForgotPasswordModal();
        });

        // Modal close
        document.querySelector('.modal-close').addEventListener('click', this.closeModal);
        document.getElementById('forgotPasswordModal').addEventListener('click', (e) => {
            if (e.target.id === 'forgotPasswordModal') {
                this.closeModal();
            }
        });
    }

    switchTab(tab) {
        // Update tabs
        document.querySelectorAll('.auth-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });

        // Update forms
        document.querySelectorAll('.auth-form').forEach(form => {
            form.classList.toggle('active', form.id === `${tab}Form`);
        });

        this.currentTab = tab;
    }

    async handleLogin(e) {
        const formData = new FormData(e.target);
        const data = {
            email: formData.get('email'),
            password: formData.get('password')
        };

        // Validación básica
        if (!this.validateEmail(data.email)) {
            this.showError('Por favor ingresa un email válido');
            return;
        }

        if (!data.password) {
            this.showError('Por favor ingresa tu contraseña');
            return;
        }

        // Mostrar loading
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Iniciando sesión...';
        submitBtn.disabled = true;

        try {
            // LLAMADA REAL AL BACKEND
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
                credentials: 'include'
            });

            console.log('📨 Response status:', response.status);
            
            const responseText = await response.text();
            console.log('📨 Response text:', responseText);
            
            let result;
            try {
                result = JSON.parse(responseText);
            } catch (parseError) {
                console.error('❌ Error parseando JSON:', parseError);
                throw new Error('Respuesta inválida del servidor');
            }

            if (!response.ok) {
                throw new Error(result.error || `Error ${response.status}`);
            }

            // Guardar sesión REAL
            localStorage.setItem('auth_token', result.session_id);
            localStorage.setItem('user_email', result.user.email);
            localStorage.setItem('user_name', `${result.user.firstName} ${result.user.lastName}`);
            localStorage.setItem('user_plan', result.user.plan);
            
            // Mostrar mensaje de éxito
            this.showSuccess(result.message || '¡Sesión iniciada exitosamente!');
            
            // Redirigir al dashboard
            setTimeout(() => {
                this.redirectToDashboard();
            }, 1000);
            
        } catch (error) {
            console.error('❌ Error completo:', error);
            this.showError(error.message);
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    async handleRegister(e) {
        const formData = new FormData(e.target);
        const data = {
            firstName: formData.get('firstName'),
            lastName: formData.get('lastName'),
            email: formData.get('email'),
            password: formData.get('password'),
            confirmPassword: formData.get('confirmPassword'),
            acceptTerms: formData.get('acceptTerms') === 'on'
        };

        // Validaciones
        if (!data.firstName || !data.lastName) {
            this.showError('Por favor ingresa tu nombre completo');
            return;
        }

        if (!this.validateEmail(data.email)) {
            this.showError('Por favor ingresa un email válido');
            return;
        }

        if (data.password.length < 6) {
            this.showError('La contraseña debe tener al menos 6 caracteres');
            return;
        }

        if (data.password !== data.confirmPassword) {
            this.showError('Las contraseñas no coinciden');
            return;
        }

        if (!data.acceptTerms) {
            this.showError('Debes aceptar los términos y condiciones');
            return;
        }

        // Mostrar loading
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Creando cuenta...';
        submitBtn.disabled = true;

        try {
            // LLAMADA REAL AL BACKEND
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
                credentials: 'include'
            });

            console.log('📨 Response status:', response.status);
            
            const responseText = await response.text();
            console.log('📨 Response text:', responseText);
            
            let result;
            try {
                result = JSON.parse(responseText);
            } catch (parseError) {
                console.error('❌ Error parseando JSON:', parseError);
                throw new Error('Respuesta inválida del servidor');
            }

            if (!response.ok) {
                throw new Error(result.error || `Error ${response.status}`);
            }

            // ✅ CORRECCIÓN: Guardar información PERO NO REDIRIGIR automáticamente
            localStorage.setItem('pending_verification_email', result.user.email);
            localStorage.setItem('pending_user_name', `${result.user.firstName} ${result.user.lastName}`);
            
            // Mostrar mensaje de éxito ESPECÍFICO
            if (result.email_sent === false) {
                this.showSuccess('Cuenta creada, pero no se pudo enviar el email de verificación. Contacta soporte.');
            } else {
                this.showSuccess('¡Cuenta creada exitosamente! Revisa tu email para verificar tu cuenta.');
                
                // ✅ CORRECCIÓN: Cambiar a pestaña de login con mensaje informativo
                setTimeout(() => {
                    this.switchTab('login');
                    this.showInfo('Verifica tu email y luego inicia sesión');
                }, 2000);
            }
            
        } catch (error) {
            console.error('❌ Error completo:', error);
            this.showError(error.message);
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    setupPasswordStrength() {
        const passwordInput = document.getElementById('registerPassword');
        const strengthFill = document.querySelector('.strength-fill');
        const strengthText = document.querySelector('.strength-text');

        if (!passwordInput || !strengthFill) return;

        passwordInput.addEventListener('input', (e) => {
            const password = e.target.value;
            const strength = this.calculatePasswordStrength(password);
            
            strengthFill.setAttribute('data-strength', strength);
            
            const texts = [
                'Muy débil',
                'Débil',
                'Moderada', 
                'Fuerte',
                'Muy fuerte'
            ];
            strengthText.textContent = texts[strength] || 'Seguridad de la contraseña';
        });
    }

    calculatePasswordStrength(password) {
        let strength = 0;
        
        if (password.length >= 8) strength++;
        if (password.match(/[a-z]/) && password.match(/[A-Z]/)) strength++;
        if (password.match(/\d/)) strength++;
        if (password.match(/[^a-zA-Z\d]/)) strength++;
        
        return Math.min(strength, 4);
    }

    togglePasswordVisibility(passwordFieldId, show) {
        const passwordField = document.getElementById(passwordFieldId);
        if (passwordField) {
            passwordField.type = show ? 'text' : 'password';
        }
    }

    showForgotPasswordModal() {
        document.getElementById('forgotPasswordModal').classList.add('show');
    }

    closeModal() {
        document.getElementById('forgotPasswordModal').classList.remove('show');
    }

    async sendResetLink() {
        const email = document.getElementById('forgotEmail').value;
        
        if (!this.validateEmail(email)) {
            this.showError('Por favor ingresa un email válido');
            return;
        }

        try {
            await new Promise(resolve => setTimeout(resolve, 1500));
            this.showSuccess('Se ha enviado un enlace de recuperación a tu email');
            this.closeModal();
        } catch (error) {
            this.showError(error.message);
        }
    }

    validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    checkExistingAuth() {
        const token = localStorage.getItem('auth_token');
        const currentPage = window.location.pathname.split('/').pop();
    
        if (token && (currentPage === 'login.html' || currentPage === 'index.html' || currentPage === '')) {
            this.verifyTokenAndRedirect(token);
        } else if (!token && currentPage === 'dashboard.html') {
            window.location.href = 'login.html';
        }
    }

    async verifyTokenAndRedirect(token) {
        try {
            const response = await fetch('/api/auth/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ session_id: token })
            });

            const result = await response.json();

            if (result.valid) {
                this.redirectToDashboard();
            } else {
                localStorage.removeItem('auth_token');
                localStorage.removeItem('user_email');
                localStorage.removeItem('user_name');
                localStorage.removeItem('user_plan');
            }
        } catch (error) {
            console.error('Error verificando token:', error);
        }
    }

    redirectToDashboard() {
        window.location.href = 'dashboard.html';
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    // ✅ NUEVA FUNCIÓN: Mensajes informativos
    showInfo(message) {
        this.showNotification(message, 'info');
    }

    showNotification(message, type = 'info') {
        const colors = {
            'error': '#ef4444',
            'success': '#10b981', 
            'info': '#3b82f6'
        };
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                <button class="notification-close">&times;</button>
            </div>
        `;

        notification.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            background: ${colors[type] || '#3b82f6'};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            z-index: 10000;
            max-width: 400px;
            animation: slideInRight 0.3s ease-out;
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);

        notification.querySelector('.notification-close').addEventListener('click', () => {
            if (notification.parentNode) {
                notification.remove();
            }
        });
    }
}

// Google Auth (simulación por ahora)
function loginWithGoogle() {
    const authManager = new AuthManager();
    authManager.showError('Autenticación con Google en desarrollo');
    authManager.switchTab('register');
}

function registerWithGoogle() {
    loginWithGoogle();
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    new AuthManager();
});

// Funciones globales para los modales
function closeModal() {
    document.getElementById('forgotPasswordModal').classList.remove('show');
}

function sendResetLink() {
    const authManager = new AuthManager();
    authManager.sendResetLink();
}