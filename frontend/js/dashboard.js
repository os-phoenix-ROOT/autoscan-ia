// dashboard.js - Lógica principal del dashboard
class DashboardManager {
    constructor() {
        this.uploadedImages = {
            frontal: null,
            'lateral-derecho': null,
            'lateral-izquierdo': null,
            trasero: null
        };
        this.analysisResults = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadUserData();
        this.checkAuth();
    }

    checkAuth() {
        const token = localStorage.getItem('auth_token');
        if (!token) {
            window.location.href = 'login.html';
            return;
        }
        
        // Verificar sesión con backend
        this.verifySession(token);
    }

    async verifySession(token) {
        try {
            const response = await fetch('/api/auth/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ session_id: token })
            });
            
            const data = await response.json();
            
            if (!data.valid) {
                this.handleLogout();
            } else {
                this.loadUserData(data.user);
            }
        } catch (error) {
            console.error('Error verificando sesión:', error);
        }
    }

    setupEventListeners() {
        // File input changes
        document.querySelectorAll('.file-input').forEach(input => {
            input.addEventListener('change', (e) => {
                this.handleImageUpload(e);
            });
        });

        // User menu
        document.querySelector('.logout').addEventListener('click', (e) => {
            e.preventDefault();
            this.handleLogout();
        });

        // Check if all images are uploaded to enable analyze button
        this.updateAnalyzeButton();
    }

    handleImageUpload(event) {
        const file = event.target.files[0];
        const angle = event.target.dataset.angle;
        
        if (!file) return;

        // Validar tipo de archivo
        if (!file.type.startsWith('image/')) {
            this.showError('Por favor sube solo archivos de imagen');
            return;
        }

        // Validar tamaño (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            this.showError('La imagen es demasiado grande. Máximo 10MB');
            return;
        }

        const reader = new FileReader();
        
        reader.onload = (e) => {
            this.uploadedImages[angle] = {
                file: file,
                dataUrl: e.target.result
            };
            
            this.updateImagePreview(angle, e.target.result);
            this.updateAnalyzeButton();
        };
        
        reader.readAsDataURL(file);
    }

    updateImagePreview(angle, dataUrl) {
        const card = document.querySelector(`[data-angle="${angle}"]`);
        const preview = document.getElementById(`preview${this.capitalize(angle)}`);
        const removeBtn = card.querySelector('.btn-remove');
        
        card.classList.add('has-image');
        preview.src = dataUrl;
        preview.style.display = 'block';
        removeBtn.style.display = 'block';
    }

    removeImage(angle) {
        const card = document.querySelector(`[data-angle="${angle}"]`);
        const preview = document.getElementById(`preview${this.capitalize(angle)}`);
        const fileInput = document.getElementById(`file${this.capitalize(angle)}`);
        const removeBtn = card.querySelector('.btn-remove');
        
        card.classList.remove('has-image');
        preview.style.display = 'none';
        preview.src = '';
        removeBtn.style.display = 'none';
        fileInput.value = '';
        
        this.uploadedImages[angle] = null;
        this.updateAnalyzeButton();
    }

    clearAllImages() {
        Object.keys(this.uploadedImages).forEach(angle => {
            if (this.uploadedImages[angle]) {
                this.removeImage(angle);
            }
        });
    }

    updateAnalyzeButton() {
        const analyzeBtn = document.getElementById('analyzeBtn');
        const allUploaded = Object.values(this.uploadedImages).every(img => img !== null);
        analyzeBtn.disabled = !allUploaded;
    }

    async analyzeVehicle() {
        // Validar que todas las imágenes estén subidas
        const missingAngles = Object.entries(this.uploadedImages)
            .filter(([angle, img]) => !img)
            .map(([angle]) => angle);

        if (missingAngles.length > 0) {
            this.showError(`Faltan imágenes: ${missingAngles.join(', ')}`);
            return;
        }

        // Mostrar modal de carga
        this.showLoadingModal();

        try {
            // Simular progreso
            this.simulateProgress();
        
            // Enviar imágenes al backend REAL
            const results = await this.sendToBackend();
            this.analysisResults = results;
        
            // Ocultar loading y mostrar resultados
            this.hideLoadingModal();
            this.showResults(results);
        
            // Actualizar estadísticas
            this.updateUsageStats();
        
        } catch (error) {
            this.hideLoadingModal();
            this.showError('Error al analizar las imágenes: ' + error.message);
        }
    }

    simulateProgress() {
        const progressFill = document.getElementById('loadingProgressFill');
        const progressText = document.getElementById('loadingProgressText');
        const messages = [
            'Procesando imagen frontal...',
            'Analizando lateral derecho...',
            'Evaluando lateral izquierdo...',
            'Revisando vista trasera...',
            'Generando reporte final...'
        ];

        let progress = 0;
        const interval = setInterval(() => {
            progress += 5;
            if (progress <= 100) {
                progressFill.style.width = `${progress}%`;
                progressText.textContent = `${progress}%`;
                
                // Cambiar mensaje según progreso
                const messageIndex = Math.floor(progress / 20);
                if (messageIndex < messages.length) {
                    document.getElementById('loadingMessage').textContent = messages[messageIndex];
                }
            } else {
                clearInterval(interval);
            }
        }, 100);
    }

    async sendToBackend() {
        const formData = new FormData();
    
        console.log("📤 Preparando envío de imágenes...");
    
        // Agregar las 4 imágenes al FormData
        Object.entries(this.uploadedImages).forEach(([angle, imageData]) => {
            console.log(`   📁 ${angle}:`, imageData.file.name);
            formData.append(angle, imageData.file, imageData.file.name);
        });

        try {
            console.log("🚀 Enviando al backend...");
        
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });

            console.log("📨 Respuesta recibida:", response.status);
        
            const data = await response.json();
        
            if (!response.ok) {
                throw new Error(data.error || `Error ${response.status}`);
            }

            console.log("✅ Análisis exitoso:", data);
            return data.results;
        
        } catch (error) {
            console.error('❌ Error en backend:', error);
            throw new Error(`Error del servidor: ${error.message}`);
        }
    }

    showResults(results) {
        const resultsSection = document.getElementById('resultsSection');
        const resultsGrid = document.getElementById('resultsGrid');
        const conclusionCard = document.getElementById('conclusionCard');
        
        // Limpiar resultados anteriores
        resultsGrid.innerHTML = '';
        
        // Mostrar resultados por ángulo
        Object.entries(results).forEach(([angle, data]) => {
            if (angle !== 'conclusion') {
                const resultCard = this.createResultCard(angle, data);
                resultsGrid.appendChild(resultCard);
            }
        });
        
        // Mostrar conclusión
        conclusionCard.innerHTML = this.createConclusionCard(results.conclusion);
        
        // Mostrar sección de resultados
        resultsSection.style.display = 'block';
        
        // Scroll a resultados
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    createResultCard(angle, data) {
        const angleNames = {
            frontal: 'Vista Frontal',
            'lateral-derecho': 'Lateral Derecho',
            'lateral-izquierdo': 'Lateral Izquierdo',
            trasero: 'Vista Trasera'
        };

        const damageColors = {
            'no-damage': 'no-damage',
            'minor': 'minor',
            'moderate': 'moderate',
            'severe': 'severe'
        };

        const card = document.createElement('div');
        card.className = 'result-card';
        card.innerHTML = `
            <div class="result-header">
                <span class="result-angle">${angleNames[angle]}</span>
                <span class="result-confidence">${data.confidence}%</span>
            </div>
            <div class="result-damage">
                <span class="damage-badge ${damageColors[data.damage]}">${data.damage_label}</span>
            </div>
            <div class="result-details">
                <div class="detail-item">
                    <span class="detail-label">Nivel de Daño:</span>
                    <span class="detail-value">${data.damage_label}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Confianza:</span>
                    <span class="detail-value">${data.confidence}%</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Detalles:</span>
                    <span class="detail-value">${data.details}</span>
                </div>
            </div>
        `;
        
        return card;
    }

    createConclusionCard(conclusion) {
        const overallIcons = {
            excellent: '🎉',
            good: '👍',
            acceptable: '⚠️',
            poor: '🚨'
        };

        const overallTexts = {
            excellent: 'Excelente estado',
            good: 'Buen estado',
            acceptable: 'Estado aceptable',
            poor: 'Requiere atención'
        };

        return `
            <div class="conclusion-header">
                <div class="conclusion-icon">${overallIcons[conclusion.overall]}</div>
                <h3>Conclusión General - ${overallTexts[conclusion.overall]}</h3>
            </div>
            <div class="conclusion-summary">
                <p>${conclusion.conclusion}</p>
            </div>
            <div class="recommendation">
                <h4>Recomendación:</h4>
                <ul class="recommendation-list">
                    <li><i class="fas fa-check-circle"></i> ${conclusion.recommendation}</li>
                    <li><i class="fas fa-tools"></i> Consultar con especialista para evaluación completa</li>
                    <li><i class="fas fa-car-crash"></i> Verificar daños internos con mecánico</li>
                </ul>
            </div>
        `;
    }

    updateUsageStats() {
        const analysesCount = document.getElementById('analysesCount');
        const remainingAnalyses = document.getElementById('remainingAnalyses');
    
        // Obtener del localStorage o empezar desde 0
        let currentCount = parseInt(localStorage.getItem('analyses_count')) || 0;
        let currentRemaining = parseInt(localStorage.getItem('remaining_analyses')) || 3;
    
        // Incrementar contador y decrementar restantes
        currentCount += 1;
        currentRemaining = Math.max(0, currentRemaining - 1);
    
        // Guardar en localStorage
        localStorage.setItem('analyses_count', currentCount.toString());
        localStorage.setItem('remaining_analyses', currentRemaining.toString());
    
        // Actualizar UI
        analysesCount.textContent = currentCount;
        remainingAnalyses.textContent = currentRemaining;
    
        console.log(`📊 Estadísticas actualizadas: ${currentCount} análisis, ${currentRemaining} restantes`);
    }

    loadUserData(userData = null) {
        if (userData) {
            document.getElementById('userName').textContent = `${userData.firstName} ${userData.lastName}`;
        } else {
            const userName = localStorage.getItem('user_name') || 'Usuario';
            document.getElementById('userName').textContent = userName;
        }
    }

    handleLogout() {
        const token = localStorage.getItem('auth_token');
        
        if (token) {
            // Notificar al backend
            fetch('/api/auth/logout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ session_id: token })
            });
        }
        
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_name');
        localStorage.removeItem('user_email');
        window.location.href = 'login.html';
    }

    showInstructionsModal() {
        document.getElementById('instructionsModal').classList.add('show');
    }

    showLoadingModal() {
        document.getElementById('loadingModal').classList.add('show');
    }

    hideLoadingModal() {
        document.getElementById('loadingModal').classList.remove('show');
    }

    showError(message) {
        // Crear notificación temporal
        const notification = document.createElement('div');
        notification.className = 'notification notification-error';
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                <button class="notification-close">&times;</button>
            </div>
        `;

        // Estilos para la notificación
        notification.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            background: #ef4444;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            z-index: 10000;
            max-width: 400px;
            animation: slideInRight 0.3s ease-out;
        `;

        document.body.appendChild(notification);

        // Auto-remover después de 5 segundos
        setTimeout(() => {
            notification.remove();
        }, 5000);

        // Cerrar al hacer click
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
    }

    capitalize(str) {
        return str.split('-').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join('');
    }
}

// Funciones globales para los modales
function showInstructionsModal() {
    document.getElementById('instructionsModal').classList.add('show');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

function removeImage(angle) {
    const dashboard = window.dashboard;
    if (dashboard) {
        dashboard.removeImage(angle);
    }
}

function clearAllImages() {
    const dashboard = window.dashboard;
    if (dashboard) {
        dashboard.clearAllImages();
    }
}

function analyzeVehicle() {
    const dashboard = window.dashboard;
    if (dashboard) {
        dashboard.analyzeVehicle();
    }
}

function exportResults() {
    // Simular exportación de resultados
    const dashboard = window.dashboard;
    if (dashboard && dashboard.analysisResults) {
        alert('Funcionalidad de exportación en desarrollo');
    } else {
        alert('No hay resultados para exportar');
    }
}

function newAnalysis() {
    const dashboard = window.dashboard;
    if (dashboard) {
        dashboard.clearAllImages();
        document.getElementById('resultsSection').style.display = 'none';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

// Inicializar dashboard cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new DashboardManager();
});