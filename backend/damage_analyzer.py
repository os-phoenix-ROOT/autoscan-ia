"""
Módulo profesional para análisis de daños vehiculares - CORREGIDO
"""
import os
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import load_img, img_to_array
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input
import logging

logger = logging.getLogger(__name__)

class DamageAnalyzer:
    def __init__(self, model_path=None):
        self.model = None
        self.model_loaded = False
        
        # Configuración CORREGIDA - igual que tu script de prueba
        self.IMG_SIZE = (224, 224)
        self.CLASS_NAMES = {
            0: "01-minor",
            1: "02-moderate", 
            2: "03-severe",
            3: "04-no-damage"
        }
        
        self.CLASS_LABELS = {
            "01-minor": "Daño Leve",
            "02-moderate": "Daño Moderado", 
            "03-severe": "Daño Severo",
            "04-no-damage": "Sin Daño"
        }
        
        self.CLASS_DESCRIPTIONS = {
            "01-minor": "Rayones pequeños, abolladuras leves",
            "02-moderate": "Abolladuras medias, roturas parciales", 
            "03-severe": "Estructura comprometida, grandes abolladuras",
            "04-no-damage": "Vehículo en buen estado sin daños visibles"
        }
        
        self._load_model(model_path)
    
    def _load_model(self, model_path=None):
        """Carga el modelo de IA"""
        try:
            if model_path is None:
                model_path = "backend/models/best_mobilenet_4classes_improved.keras"
            
            if not os.path.exists(model_path):
                # Intentar con formato .h5 si .keras no existe
                h5_path = model_path.replace('.keras', '.h5')
                if os.path.exists(h5_path):
                    model_path = h5_path
                    logger.info(f"🔄 Usando modelo .h5: {h5_path}")
                else:
                    raise FileNotFoundError(f"Modelo no encontrado: {model_path}")
            
            logger.info(f"📦 Cargando modelo desde: {model_path}")
            self.model = load_model(model_path)
            self.model_loaded = True
            logger.info("✅ Modelo cargado exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error cargando el modelo: {e}")
            self.model_loaded = False
            raise
    
    def preprocess_image(self, image_path):
        """Preprocesa una imagen para el modelo"""
        try:
            img = load_img(image_path, target_size=self.IMG_SIZE)
            img_array = img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = preprocess_input(img_array)
            return img_array
            
        except Exception as e:
            logger.error(f"Error preprocesando imagen {image_path}: {e}")
            raise
    
    def analyze_single_image(self, image_path):
        """Analiza una sola imagen"""
        if not self.model_loaded:
            raise RuntimeError("Modelo no cargado")
        
        try:
            # Preprocesar
            processed_img = self.preprocess_image(image_path)
            
            # Predecir
            predictions = self.model.predict(processed_img, verbose=0)
            prediction_array = predictions[0]
            
            # Obtener resultados
            main_class_idx = np.argmax(prediction_array)
            main_class = self.CLASS_NAMES[main_class_idx]
            confidence = float(prediction_array[main_class_idx] * 100)
            
            # Todas las probabilidades
            all_predictions = {}
            for i, prob in enumerate(prediction_array):
                class_name = self.CLASS_NAMES[i]
                all_predictions[class_name] = float(prob * 100)
            
            # Nivel de confianza
            if confidence > 80:
                confidence_level = "alta"
            elif confidence > 60:
                confidence_level = "media" 
            else:
                confidence_level = "baja"
            
            result = {
                "damage": main_class.replace("01-", "").replace("02-", "").replace("03-", "").replace("04-", ""),
                "damage_label": self.CLASS_LABELS[main_class],
                "confidence": round(confidence, 2),
                "confidence_level": confidence_level,
                "description": self.CLASS_DESCRIPTIONS[main_class],
                "all_predictions": all_predictions,
                "details": self._generate_details(main_class, confidence)
            }
            
            logger.info(f"📊 {self.CLASS_LABELS[main_class]} ({confidence:.1f}%)")
            return result
            
        except Exception as e:
            logger.error(f"Error analizando {image_path}: {e}")
            raise
    
    def analyze_vehicle(self, image_paths):
        """Analiza un vehículo completo con 4 ángulos"""
        if not self.model_loaded:
            raise RuntimeError("Modelo no cargado")
        
        results = {}
        angle_names = {
            'frontal': 'Vista Frontal',
            'lateral-derecho': 'Lateral Derecho',
            'lateral-izquierdo': 'Lateral Izquierdo', 
            'trasero': 'Vista Trasera'
        }
        
        try:
            # Analizar cada ángulo
            for angle, image_path in image_paths.items():
                logger.info(f"🔍 Analizando {angle_names[angle]}...")
                results[angle] = self.analyze_single_image(image_path)
            
            # Conclusión general
            conclusion = self._generate_general_conclusion(results)
            results['conclusion'] = conclusion
            
            return results
            
        except Exception as e:
            logger.error(f"Error en análisis completo: {e}")
            raise
    
    def _generate_details(self, class_name, confidence):
        """Genera detalles específicos"""
        details_map = {
            "01-minor": "Rayones superficiales o abolladuras menores",
            "02-moderate": "Abolladuras medias que podrían requerir reparación",
            "03-severe": "Daños estructurales que afectan integridad", 
            "04-no-damage": "Vehículo en excelente estado sin daños visibles"
        }
        
        detail = details_map.get(class_name, "Daño no especificado")
        
        if confidence < 60:
            detail += " (Baja confianza - verificación manual recomendada)"
        elif confidence < 80:
            detail += " (Confianza media)"
        else:
            detail += " (Alta confianza)"
            
        return detail
    
    def _generate_general_conclusion(self, results):
        """Genera conclusión general"""
        damage_counts = {"Sin Daño": 0, "Daño Leve": 0, "Daño Moderado": 0, "Daño Severo": 0}
        total_confidence = 0
        angle_count = 0
        
        for angle, result in results.items():
            if angle != 'conclusion':
                damage_label = result['damage_label']
                damage_counts[damage_label] += 1
                total_confidence += result['confidence']
                angle_count += 1
        
        avg_confidence = total_confidence / angle_count if angle_count > 0 else 0
        
        # Determinar estado general
        if damage_counts["Daño Severo"] > 0:
            overall = "poor"
            conclusion_text = "El vehículo presenta daños severos que requieren atención inmediata."
            recommendation = "No recomendado para compra sin evaluación profesional exhaustiva."
        elif damage_counts["Daño Moderado"] > 1:
            overall = "acceptable" 
            conclusion_text = "El vehículo tiene múltiples daños moderados que necesitan reparación."
            recommendation = "Evaluar costos de reparación antes de proceder."
        elif damage_counts["Daño Leve"] > 0:
            overall = "good"
            conclusion_text = "El vehículo se encuentra en buen estado con daños menores cosméticos."
            recommendation = "Adecuado para compra, considerar reparaciones estéticas."
        else:
            overall = "excellent"
            conclusion_text = "El vehículo está en excelente estado sin daños detectados."
            recommendation = "Recomendado para compra, verificar mantenimiento interno."
        
        if avg_confidence < 70:
            conclusion_text += " Nota: La confianza del análisis es baja, se recomienda verificación manual."
        
        return {
            "overall": overall,
            "conclusion": conclusion_text,
            "recommendation": recommendation,
            "damage_breakdown": damage_counts,
            "average_confidence": round(avg_confidence, 2)
        }