import cv2
import numpy as np
from PIL import Image
import io
from typing import Tuple, Optional

class ImagePreprocessor:
    """
    Pré-processamento de imagens para melhorar acurácia do OCR.
    Aplica técnicas de visão computacional para limpar e otimizar imagens manuscritas.
    """
    
    def __init__(self):
        self.target_dpi = 300  # DPI ideal para OCR
        self.min_size = 1000   # Tamanho mínimo em pixels
    
    def preprocess(self, image_bytes: bytes) -> bytes:
        """
        Pipeline completo de pré-processamento.
        
        Args:
            image_bytes: Imagem original em bytes
            
        Returns:
            Imagem processada em bytes (PNG)
        """
        # Converter bytes para numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Não foi possível decodificar a imagem")
        
        # Pipeline de processamento
        img = self._resize_if_needed(img)
        img = self._convert_to_grayscale(img)
        img = self._enhance_contrast(img)
        img = self._denoise(img)
        img = self._deskew(img)
        img = self._binarize(img)
        img = self._remove_borders(img)
        
        # Converter de volta para bytes
        success, encoded = cv2.imencode('.png', img)
        if not success:
            raise ValueError("Erro ao codificar imagem processada")
        
        return encoded.tobytes()
    
    def _resize_if_needed(self, img: np.ndarray) -> np.ndarray:
        """Redimensiona imagem se necessário para otimizar OCR"""
        height, width = img.shape[:2]
        
        # Se muito pequena, aumentar
        if min(height, width) < self.min_size:
            scale = self.min_size / min(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Se muito grande, reduzir (>4000px)
        elif max(height, width) > 4000:
            scale = 4000 / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        return img
    
    def _convert_to_grayscale(self, img: np.ndarray) -> np.ndarray:
        """Converte para escala de cinza"""
        if len(img.shape) == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img
    
    def _enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        """
        Melhora contraste usando CLAHE (Contrast Limited Adaptive Histogram Equalization).
        Melhor que equalização simples para documentos.
        """
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(img)
    
    def _denoise(self, img: np.ndarray) -> np.ndarray:
        """Remove ruído mantendo bordas nítidas"""
        # fastNlMeansDenoising é específico para escala de cinza
        return cv2.fastNlMeansDenoising(img, h=10)
    
    def _deskew(self, img: np.ndarray) -> np.ndarray:
        """
        Corrige inclinação do documento.
        Usa detecção de linhas de Hough para encontrar ângulo.
        """
        # Detectar bordas
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        
        # Detectar linhas
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is None:
            return img
        
        # Calcular ângulo médio das linhas
        angles = []
        for rho, theta in lines[:, 0]:
            angle = np.degrees(theta) - 90
            if -45 < angle < 45:  # Ignorar linhas muito inclinadas
                angles.append(angle)
        
        if not angles:
            return img
        
        # Usar mediana para robustez
        median_angle = np.median(angles)
        
        # Só corrigir se inclinação significativa (>0.5 graus)
        if abs(median_angle) < 0.5:
            return img
        
        # Rotacionar imagem
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), 
                                 flags=cv2.INTER_CUBIC, 
                                 borderMode=cv2.BORDER_REPLICATE)
        
        return rotated
    
    def _binarize(self, img: np.ndarray) -> np.ndarray:
        """
        Binarização adaptativa (Otsu).
        Melhor que threshold fixo para iluminação irregular.
        """
        # Gaussian blur leve antes da binarização
        blurred = cv2.GaussianBlur(img, (5, 5), 0)
        
        # Otsu's binarization
        _, binary = cv2.threshold(blurred, 0, 255, 
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def _remove_borders(self, img: np.ndarray) -> np.ndarray:
        """Remove bordas pretas que podem atrapalhar OCR"""
        # Encontrar contornos
        contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return img
        
        # Pegar maior contorno (assumindo que é o documento)
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Bounding box
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Crop com margem de 10px
        margin = 10
        x = max(0, x - margin)
        y = max(0, y - margin)
        w = min(img.shape[1] - x, w + 2 * margin)
        h = min(img.shape[0] - y, h + 2 * margin)
        
        return img[y:y+h, x:x+w]
    
    def get_debug_images(self, image_bytes: bytes) -> dict:
        """
        Retorna imagens intermediárias para debug/visualização.
        Útil para entender o que cada etapa faz.
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        results = {}
        
        # Original
        results['original'] = self._encode_image(img)
        
        # Cada etapa
        img = self._resize_if_needed(img)
        results['resized'] = self._encode_image(img)
        
        img = self._convert_to_grayscale(img)
        results['grayscale'] = self._encode_image(img)
        
        img = self._enhance_contrast(img)
        results['contrast'] = self._encode_image(img)
        
        img = self._denoise(img)
        results['denoised'] = self._encode_image(img)
        
        img = self._deskew(img)
        results['deskewed'] = self._encode_image(img)
        
        img = self._binarize(img)
        results['binarized'] = self._encode_image(img)
        
        img = self._remove_borders(img)
        results['final'] = self._encode_image(img)
        
        return results
    
    def _encode_image(self, img: np.ndarray) -> bytes:
        """Helper para converter numpy array para bytes"""
        success, encoded = cv2.imencode('.png', img)
        if success:
            return encoded.tobytes()
        return b''

# Singleton
image_preprocessor = ImagePreprocessor()
