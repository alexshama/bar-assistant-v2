"""
Сервис кэширования изображений коктейлей
"""

import os
import hashlib
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ImageCache:
    """Класс для кэширования сгенерированных изображений коктейлей"""
    
    def __init__(self, cache_dir: str = "data/images"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Инициализирован кэш изображений в {self.cache_dir}")
    
    def _get_cache_key(self, cocktail_id: str, prompt: str) -> str:
        """Создание ключа кэша на основе ID коктейля"""
        # Для коктейлей используем только ID, так как промпт генерируется на основе рецепта
        # Это позволяет переиспользовать изображения для одного коктейля
        
        # Нормализуем ID коктейля
        normalized_id = cocktail_id.upper().replace("COCKTAIL_", "").replace("_", "-")
        
        # Для специальных коктейлей с фиксированными промптами используем только ID
        special_cocktails = ["045-B-52", "008-MARGARITA", "050-SINGAPORE-SLING"]
        
        if any(special in normalized_id for special in special_cocktails):
            return f"{cocktail_id}_standard"
        
        # Для остальных коктейлей используем упрощенный хэш основных характеристик
        # Извлекаем ключевые слова из промпта для хэширования
        key_elements = []
        prompt_lower = prompt.lower()
        
        # Ищем цвет
        colors = ["red", "pink", "golden", "amber", "clear", "green", "brown"]
        for color in colors:
            if color in prompt_lower:
                key_elements.append(color)
                break
        
        # Ищем тип стакана
        glasses = ["rocks", "martini", "coupe", "highball", "shot"]
        for glass in glasses:
            if glass in prompt_lower:
                key_elements.append(glass)
                break
        
        # Создаем хэш из ключевых элементов
        if key_elements:
            elements_str = "_".join(sorted(key_elements))
            prompt_hash = hashlib.md5(elements_str.encode('utf-8')).hexdigest()[:6]
        else:
            prompt_hash = "default"
        
        return f"{cocktail_id}_{prompt_hash}"
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Получение пути к файлу кэша"""
        return self.cache_dir / f"{cache_key}.png"
    
    def _find_cache_file(self, cache_key: str) -> Optional[Path]:
        """Поиск файла кэша с любым расширением"""
        # Сначала ищем .png
        png_path = self.cache_dir / f"{cache_key}.png"
        if png_path.exists():
            return png_path
        
        # Потом ищем .jpg
        jpg_path = self.cache_dir / f"{cache_key}.jpg"
        if jpg_path.exists():
            return jpg_path
        
        # Потом ищем .jpeg
        jpeg_path = self.cache_dir / f"{cache_key}.jpeg"
        if jpeg_path.exists():
            return jpeg_path
        
        return None
    
    def get_cached_image(self, cocktail_id: str, prompt: str) -> Optional[bytes]:
        """Получение изображения из кэша"""
        try:
            cache_key = self._get_cache_key(cocktail_id, prompt)
            cache_path = self._find_cache_file(cache_key)
            
            if cache_path:
                with open(cache_path, 'rb') as f:
                    image_bytes = f.read()
                
                logger.info(f"Изображение найдено в кэше: {cache_key} ({cache_path.name})")
                return image_bytes
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении изображения из кэша: {e}")
            return None
    
    def save_to_cache(self, cocktail_id: str, prompt: str, image_bytes: bytes) -> bool:
        """Сохранение изображения в кэш"""
        try:
            cache_key = self._get_cache_key(cocktail_id, prompt)
            cache_path = self._get_cache_path(cache_key)
            
            with open(cache_path, 'wb') as f:
                f.write(image_bytes)
            
            logger.info(f"Изображение сохранено в кэш: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении изображения в кэш: {e}")
            return False
    
    def clear_cache(self) -> int:
        """Очистка всего кэша"""
        try:
            count = 0
            for cache_file in self.cache_dir.glob("*.png"):
                cache_file.unlink()
                count += 1
            
            logger.info(f"Очищено {count} файлов из кэша")
            return count
            
        except Exception as e:
            logger.error(f"Ошибка при очистке кэша: {e}")
            return 0
    
    def get_cache_stats(self) -> dict:
        """Получение статистики кэша"""
        try:
            cache_files = list(self.cache_dir.glob("*.png"))
            total_files = len(cache_files)
            
            total_size = sum(f.stat().st_size for f in cache_files)
            total_size_mb = total_size / (1024 * 1024)
            
            return {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size_mb, 2),
                "cache_dir": str(self.cache_dir)
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики кэша: {e}")
            return {"error": str(e)}
    
    def cleanup_duplicates(self) -> int:
        """Очистка дублирующихся изображений одного коктейля"""
        try:
            cache_files = list(self.cache_dir.glob("*.png"))
            
            # Группируем файлы по ID коктейля
            cocktail_groups = {}
            for cache_file in cache_files:
                # Извлекаем ID коктейля из имени файла
                parts = cache_file.stem.split("_")
                if len(parts) >= 3:  # COCKTAIL_XXX_NAME_hash
                    cocktail_id = "_".join(parts[:3])  # COCKTAIL_XXX_NAME
                    if cocktail_id not in cocktail_groups:
                        cocktail_groups[cocktail_id] = []
                    cocktail_groups[cocktail_id].append(cache_file)
            
            removed_count = 0
            
            # Для каждого коктейля оставляем только самый новый файл
            for cocktail_id, files in cocktail_groups.items():
                if len(files) > 1:
                    # Сортируем по времени создания (новые последними)
                    files.sort(key=lambda f: f.stat().st_ctime)
                    
                    # Удаляем все кроме последнего
                    for old_file in files[:-1]:
                        old_file.unlink()
                        removed_count += 1
                        logger.info(f"Удален дублирующийся файл: {old_file.name}")
            
            logger.info(f"Очистка дубликатов завершена. Удалено файлов: {removed_count}")
            return removed_count
            
        except Exception as e:
            logger.error(f"Ошибка при очистке дубликатов: {e}")
            return 0
    
    def cleanup_old_cache(self, max_files: int = 1000) -> int:
        """Очистка старых файлов кэша при превышении лимита"""
        try:
            cache_files = list(self.cache_dir.glob("*.png"))
            
            if len(cache_files) <= max_files:
                return 0
            
            # Сортируем по времени последнего доступа (старые первыми)
            cache_files.sort(key=lambda f: f.stat().st_atime)
            
            # Удаляем самые старые файлы
            files_to_remove = len(cache_files) - max_files
            removed_count = 0
            
            for cache_file in cache_files[:files_to_remove]:
                cache_file.unlink()
                removed_count += 1
            
            logger.info(f"Удалено {removed_count} старых файлов из кэша")
            return removed_count
            
        except Exception as e:
            logger.error(f"Ошибка при очистке старого кэша: {e}")
            return 0


# Глобальный экземпляр кэша
image_cache = ImageCache()