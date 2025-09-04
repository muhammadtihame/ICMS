import os
import joblib
import pickle
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class AIModelManager:
    """Manager for AI models in the CMS system"""
    
    def __init__(self):
        self.models_dir = os.path.join(settings.BASE_DIR, 'models', 'ai')
        self.models = {}
        self.feature_names = None
        self._load_models()
    
    def _load_models(self):
        """Load all AI models from the models directory"""
        try:
            # Load feature names
            feature_names_path = os.path.join(self.models_dir, 'feature_names.pkl')
            if os.path.exists(feature_names_path):
                with open(feature_names_path, 'rb') as f:
                    self.feature_names = pickle.load(f)
                logger.info("Feature names loaded successfully")
            
            # Load LightGBM classifier
            classifier_path = os.path.join(self.models_dir, 'lgb_classifier.pkl')
            if os.path.exists(classifier_path):
                self.models['classifier'] = joblib.load(classifier_path)
                logger.info("LightGBM classifier loaded successfully")
            
            # Load LightGBM regressor
            regressor_path = os.path.join(self.models_dir, 'lgb_regressor.pkl')
            if os.path.exists(regressor_path):
                self.models['regressor'] = joblib.load(regressor_path)
                logger.info("LightGBM regressor loaded successfully")
                
        except Exception as e:
            logger.error(f"Error loading AI models: {str(e)}")
            self.models = {}
            self.feature_names = None
    
    def get_model(self, model_type):
        """Get a specific model by type"""
        return self.models.get(model_type)
    
    def get_feature_names(self):
        """Get feature names for the models"""
        return self.feature_names
    
    def is_model_available(self, model_type):
        """Check if a specific model is available"""
        return model_type in self.models and self.models[model_type] is not None
    
    def predict_performance(self, features):
        """Predict student performance using the classifier"""
        try:
            classifier = self.get_model('classifier')
            if classifier is None:
                return None, "Classifier model not available"
            
            if self.feature_names is None:
                return None, "Feature names not available"
            
            # Ensure features match expected format
            if len(features) != len(self.feature_names):
                return None, f"Expected {len(self.feature_names)} features, got {len(features)}"
            
            # Make prediction
            prediction = classifier.predict([features])[0]
            probability = classifier.predict_proba([features])[0].max()
            
            return {
                'prediction': prediction,
                'probability': probability,
                'confidence': 'High' if probability > 0.8 else 'Medium' if probability > 0.6 else 'Low'
            }, None
            
        except Exception as e:
            logger.error(f"Error in performance prediction: {str(e)}")
            return None, str(e)
    
    def predict_score(self, features):
        """Predict numerical score using the regressor"""
        try:
            regressor = self.get_model('regressor')
            if regressor is None:
                return None, "Regressor model not available"
            
            if self.feature_names is None:
                return None, "Feature names not available"
            
            # Ensure features match expected format
            if len(features) != len(self.feature_names):
                return None, f"Expected {len(self.feature_names)} features, got {len(features)}"
            
            # Make prediction
            prediction = regressor.predict([features])[0]
            
            return {
                'predicted_score': round(prediction, 2),
                'score_range': self._get_score_range(prediction)
            }, None
            
        except Exception as e:
            logger.error(f"Error in score prediction: {str(e)}")
            return None, str(e)
    
    def _get_score_range(self, score):
        """Convert numerical score to grade range"""
        if score >= 90:
            return 'A+ (90-100)'
        elif score >= 80:
            return 'A (80-89)'
        elif score >= 70:
            return 'B (70-79)'
        elif score >= 60:
            return 'C (60-69)'
        elif score >= 50:
            return 'D (50-59)'
        else:
            return 'F (0-49)'
    
    def get_model_info(self):
        """Get information about loaded models"""
        info = {
            'models_loaded': len(self.models),
            'available_models': list(self.models.keys()),
            'feature_names_count': len(self.feature_names) if self.feature_names else 0,
            'models_directory': self.models_dir
        }
        
        for model_name, model in self.models.items():
            if hasattr(model, 'feature_importances_'):
                info[f'{model_name}_feature_count'] = len(model.feature_importances_)
            else:
                info[f'{model_name}_feature_count'] = 'Unknown'
        
        return info

# Global instance
ai_manager = AIModelManager()

def get_ai_manager():
    """Get the global AI model manager instance"""
    return ai_manager

def predict_student_performance(student_data):
    """Convenience function to predict student performance"""
    return ai_manager.predict_performance(student_data)

def predict_student_score(student_data):
    """Convenience function to predict student score"""
    return ai_manager.predict_score(student_data)

def is_ai_available():
    """Check if AI models are available"""
    return len(ai_manager.models) > 0
