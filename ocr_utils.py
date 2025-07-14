"""
Utilitaires pour la reconnaissance optique de caractères (OCR)
"""
import os
import logging
from PIL import Image
import pytesseract
import cv2
import numpy as np
from typing import Dict, Optional, Tuple
import fitz  # PyMuPDF pour les PDF

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRProcessor:
    """Processeur OCR pour extraire le texte des images et documents"""
    
    def __init__(self):
        # Configuration Tesseract
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.pdf']
        self.languages = {
            'fr': 'fra',
            'en': 'eng',
            'auto': 'fra+eng'  # Par défaut français + anglais
        }
    
    def preprocess_image(self, image_path: str) -> Image.Image:
        """Prétraitement de l'image pour améliorer l'OCR"""
        try:
            # Charger l'image avec OpenCV
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Impossible de charger l'image: {image_path}")
            
            # Convertir en niveaux de gris
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Améliorer le contraste avec CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # Débruitage
            denoised = cv2.medianBlur(enhanced, 3)
            
            # Binarisation adaptative
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Convertir en PIL Image
            return Image.fromarray(binary)
            
        except Exception as e:
            logger.warning(f"Erreur lors du prétraitement: {e}, utilisation de l'image originale")
            return Image.open(image_path)
    
    def extract_text_from_image(self, image_path: str, lang: str = 'auto') -> Dict:
        """Extraire le texte d'une image"""
        try:
            # Prétraitement de l'image
            processed_img = self.preprocess_image(image_path)
            
            # Configuration Tesseract
            tesseract_lang = self.languages.get(lang, 'fra+eng')
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?;:()-"\' àâäéèêëîïôöùûüÿç'
            
            # Extraction du texte
            text = pytesseract.image_to_string(
                processed_img, 
                lang=tesseract_lang,
                config=custom_config
            ).strip()
            
            # Obtenir les données détaillées avec confiance
            data = pytesseract.image_to_data(
                processed_img, 
                lang=tesseract_lang,
                output_type=pytesseract.Output.DICT
            )
            
            # Calculer la confiance moyenne (exclure les valeurs -1)
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Détecter la langue principale
            detected_lang = self._detect_language(text)
            
            return {
                'text': text,
                'confidence': round(avg_confidence, 2),
                'language': detected_lang,
                'success': True,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction OCR: {e}")
            return {
                'text': '',
                'confidence': 0,
                'language': 'unknown',
                'success': False,
                'error': str(e)
            }
    
    def extract_text_from_pdf(self, pdf_path: str, lang: str = 'auto') -> Dict:
        """Extraire le texte d'un PDF (texte natif + OCR si nécessaire)"""
        try:
            doc = fitz.open(pdf_path)
            all_text = ""
            needs_ocr = False
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Tenter d'extraire le texte natif d'abord
                text = page.get_text()
                
                if len(text.strip()) < 50:  # Si peu de texte natif, utiliser OCR
                    needs_ocr = True
                    # Convertir la page en image
                    mat = fitz.Matrix(2.0, 2.0)  # Augmenter la résolution
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("png")
                    
                    # Sauvegarder temporairement pour OCR
                    temp_img_path = f"temp_page_{page_num}.png"
                    with open(temp_img_path, "wb") as f:
                        f.write(img_data)
                    
                    # Effectuer OCR
                    ocr_result = self.extract_text_from_image(temp_img_path, lang)
                    text = ocr_result['text']
                    
                    # Nettoyer le fichier temporaire
                    os.remove(temp_img_path)
                
                all_text += text + "\n"
            
            doc.close()
            
            # Détecter la langue
            detected_lang = self._detect_language(all_text)
            
            return {
                'text': all_text.strip(),
                'confidence': 95 if not needs_ocr else 75,  # Confiance plus élevée pour texte natif
                'language': detected_lang,
                'success': True,
                'error': None,
                'ocr_used': needs_ocr
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction PDF: {e}")
            return {
                'text': '',
                'confidence': 0,
                'language': 'unknown',
                'success': False,
                'error': str(e)
            }
    
    def _detect_language(self, text: str) -> str:
        """Détection simple de la langue basée sur les caractères"""
        if not text:
            return 'unknown'
        
        # Mots français communs
        french_words = ['le', 'la', 'les', 'de', 'du', 'des', 'et', 'à', 'un', 'une', 'ce', 'que', 'qui', 'dans', 'pour', 'avec', 'sur']
        # Mots anglais communs
        english_words = ['the', 'and', 'to', 'of', 'a', 'in', 'is', 'it', 'you', 'that', 'he', 'was', 'for', 'on', 'are', 'as', 'with']
        
        text_lower = text.lower()
        french_count = sum(1 for word in french_words if f' {word} ' in text_lower)
        english_count = sum(1 for word in english_words if f' {word} ' in text_lower)
        
        # Détecter les caractères accentués français
        french_chars = sum(1 for char in text if char in 'àâäéèêëîïôöùûüÿç')
        
        if french_count > english_count or french_chars > 0:
            return 'fr'
        elif english_count > french_count:
            return 'en'
        else:
            return 'mixed'
    
    def process_file(self, file_path: str, lang: str = 'auto') -> Dict:
        """Traiter un fichier (image ou PDF) pour extraction OCR"""
        if not os.path.exists(file_path):
            return {
                'text': '',
                'confidence': 0,
                'language': 'unknown',
                'success': False,
                'error': 'Fichier non trouvé'
            }
        
        # Obtenir l'extension du fichier
        _, ext = os.path.splitext(file_path.lower())
        
        if ext not in self.supported_formats:
            return {
                'text': '',
                'confidence': 0,
                'language': 'unknown',
                'success': False,
                'error': f'Format non supporté: {ext}'
            }
        
        try:
            if ext == '.pdf':
                return self.extract_text_from_pdf(file_path, lang)
            else:
                return self.extract_text_from_image(file_path, lang)
        except Exception as e:
            logger.error(f"Erreur lors du traitement du fichier {file_path}: {e}")
            return {
                'text': '',
                'confidence': 0,
                'language': 'unknown',
                'success': False,
                'error': str(e)
            }

# Instance globale du processeur OCR
ocr_processor = OCRProcessor()

def extract_text_from_file(file_path: str, lang: str = 'auto') -> Dict:
    """Fonction principale pour extraire le texte d'un fichier"""
    return ocr_processor.process_file(file_path, lang)

def is_ocr_supported(filename: str) -> bool:
    """Vérifier si le format de fichier est supporté pour l'OCR"""
    _, ext = os.path.splitext(filename.lower())
    return ext in ocr_processor.supported_formats