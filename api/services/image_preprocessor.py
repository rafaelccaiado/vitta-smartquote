from __future__ import annotations
import io
from typing import Tuple, Optional, Any

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    if NUMPY_AVAILABLE:
        import cv2
        OPENCV_AVAILABLE = True
    else:
        OPENCV_AVAILABLE = False
except ImportError:
    OPENCV_AVAILABLE = False

try:
    from PIL import Image
except ImportError:
    Image = None

class ImagePreprocessor:
    def __init__(self):
        self.target_dpi = 300
        self.min_size = 1000
    
    def preprocess(self, image_bytes: bytes) -> bytes:
        if not OPENCV_AVAILABLE or not NUMPY_AVAILABLE:
            return image_bytes
        
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return image_bytes
            
            # Pipeline
            img = self._resize_if_needed(img)
            img = self._convert_to_grayscale(img)
            img = self._enhance_contrast(img)
            img = self._denoise(img)
            img = self._deskew(img)
            img = self._binarize(img)
            img = self._remove_borders(img)
            
            success, encoded = cv2.imencode('.png', img)
            return encoded.tobytes() if success else image_bytes
        except:
            return image_bytes
    
    def _resize_if_needed(self, img: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE: return img
        height, width = img.shape[:2]
        if min(height, width) < self.min_size:
            scale = self.min_size / min(height, width)
            img = cv2.resize(img, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_CUBIC)
        elif max(height, width) > 4000:
            scale = 4000 / max(height, width)
            img = cv2.resize(img, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
        return img
    
    def _convert_to_grayscale(self, img: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE: return img
        if len(img.shape) == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img
    
    def _enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE: return img
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(img)
    
    def _denoise(self, img: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE: return img
        return cv2.fastNlMeansDenoising(img, h=10)
    
    def _deskew(self, img: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE: return img
        edges = cv2.Canny(img, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, 3.14159 / 180, 200)
        if lines is None: return img
        angles = [3.14159 * theta / 180 - 90 for rho, theta in lines[:, 0]]
        if not angles: return img
        import statistics
        median_angle = statistics.median(angles)
        if abs(median_angle) < 0.5: return img
        (h, w) = img.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), median_angle, 1.0)
        return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    def _binarize(self, img: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE: return img
        blurred = cv2.GaussianBlur(img, (5, 5), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    
    def _remove_borders(self, img: np.ndarray) -> np.ndarray:
        if not OPENCV_AVAILABLE: return img
        contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours: return img
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        return img[max(0, y-10):min(img.shape[0], y+h+10), max(0, x-10):min(img.shape[1], x+w+10)]

    def detect_roi(self, image_bytes: bytes) -> bytes:
        return image_bytes # Stub
    
    def get_debug_images(self, image_bytes: bytes) -> dict:
        return {} # Stub

image_preprocessor = ImagePreprocessor()
