"""
Тесты для Speech-to-Text сервиса
"""

import pytest
import tempfile
import os
from unittest.mock import patch, AsyncMock, MagicMock

from services.stt import transcribe_voice_message, _convert_ogg_to_wav


class TestSTTService:
    """Тесты STT сервиса"""
    
    @patch('services.stt.openai_client.stt')
    @patch('services.stt._convert_ogg_to_wav')
    async def test_transcribe_voice_message_success(self, mock_convert, mock_stt):
        """Тест успешной транскрипции"""
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
            ogg_path = temp_file.name
        
        try:
            # Мокаем конвертацию
            wav_path = ogg_path.replace(".ogg", ".wav")
            mock_convert.return_value = wav_path
            
            # Мокаем STT
            mock_stt.return_value = "Привет, расскажи рецепт негрони"
            
            result = await transcribe_voice_message(ogg_path)
            
            assert result == "Привет, расскажи рецепт негрони"
            mock_convert.assert_called_once_with(ogg_path)
            mock_stt.assert_called_once_with(wav_path)
            
        finally:
            # Очистка
            if os.path.exists(ogg_path):
                os.unlink(ogg_path)
    
    @patch('services.stt.openai_client.stt')
    @patch('services.stt._convert_ogg_to_wav')
    async def test_transcribe_voice_message_conversion_failure(self, mock_convert, mock_stt):
        """Тест неудачной конвертации"""
        
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
            ogg_path = temp_file.name
        
        try:
            # Мокаем неудачную конвертацию
            mock_convert.return_value = None
            
            result = await transcribe_voice_message(ogg_path)
            
            assert result is None
            mock_convert.assert_called_once_with(ogg_path)
            mock_stt.assert_not_called()
            
        finally:
            if os.path.exists(ogg_path):
                os.unlink(ogg_path)
    
    @patch('services.stt.openai_client.stt')
    @patch('services.stt._convert_ogg_to_wav')
    async def test_transcribe_voice_message_stt_failure(self, mock_convert, mock_stt):
        """Тест неудачной транскрипции"""
        
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
            ogg_path = temp_file.name
        
        try:
            wav_path = ogg_path.replace(".ogg", ".wav")
            mock_convert.return_value = wav_path
            
            # Мокаем неудачную транскрипцию
            mock_stt.return_value = None
            
            result = await transcribe_voice_message(ogg_path)
            
            assert result is None
            mock_convert.assert_called_once_with(ogg_path)
            mock_stt.assert_called_once_with(wav_path)
            
        finally:
            if os.path.exists(ogg_path):
                os.unlink(ogg_path)
    
    @patch('pydub.AudioSegment.from_ogg')
    async def test_convert_ogg_to_wav_success(self, mock_from_ogg):
        """Тест успешной конвертации OGG в WAV"""
        
        # Мокаем AudioSegment
        mock_audio = MagicMock()
        mock_from_ogg.return_value = mock_audio
        
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
            ogg_path = temp_file.name
        
        try:
            result = await _convert_ogg_to_wav(ogg_path)
            
            assert result is not None
            assert result.endswith(".wav")
            mock_from_ogg.assert_called_once_with(ogg_path)
            mock_audio.export.assert_called_once()
            
            # Очистка созданного WAV файла
            if result and os.path.exists(result):
                os.unlink(result)
                
        finally:
            if os.path.exists(ogg_path):
                os.unlink(ogg_path)
    
    @patch('pydub.AudioSegment.from_ogg')
    async def test_convert_ogg_to_wav_failure(self, mock_from_ogg):
        """Тест неудачной конвертации"""
        
        # Мокаем исключение
        mock_from_ogg.side_effect = Exception("Ошибка конвертации")
        
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
            ogg_path = temp_file.name
        
        try:
            result = await _convert_ogg_to_wav(ogg_path)
            
            assert result is None
            mock_from_ogg.assert_called_once_with(ogg_path)
            
        finally:
            if os.path.exists(ogg_path):
                os.unlink(ogg_path)


if __name__ == "__main__":
    pytest.main([__file__])