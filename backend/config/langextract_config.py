"""
LangExtract Configuration Management
Centralized configuration for LangExtract extraction parameters.
"""

import os
from typing import Optional


class LangExtractConfig:
    """Configuration class for LangExtract extraction parameters."""
    
    # Default values
    DEFAULT_CHUNK_SIZE = 2000
    DEFAULT_MAX_WORKERS = 10
    DEFAULT_MODEL = "gemini-2.5-flash"  # Same model used in successful BIRD V8 extraction
    DEFAULT_EXTRACTION_PASSES = 2
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_BASE_DELAY = 2.0  # seconds
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        self.chunk_size = self._get_int_env('LANGEXTRACT_CHUNK_SIZE', self.DEFAULT_CHUNK_SIZE)
        self.max_workers = self._get_int_env('LANGEXTRACT_MAX_WORKERS', self.DEFAULT_MAX_WORKERS)
        self.model = os.getenv('LANGEXTRACT_MODEL', self.DEFAULT_MODEL)
        self.extraction_passes = self._get_int_env('LANGEXTRACT_EXTRACTION_PASSES', self.DEFAULT_EXTRACTION_PASSES)
        self.max_retries = self._get_int_env('LANGEXTRACT_MAX_RETRIES', self.DEFAULT_MAX_RETRIES)
        self.retry_base_delay = self._get_float_env('LANGEXTRACT_RETRY_BASE_DELAY', self.DEFAULT_RETRY_BASE_DELAY)
        
        # Validation
        self._validate()
    
    def _get_int_env(self, key: str, default: int) -> int:
        """Get integer from environment variable with fallback."""
        try:
            value = os.getenv(key)
            return int(value) if value else default
        except (ValueError, TypeError):
            print(f"[Config] Invalid value for {key}, using default: {default}")
            return default
    
    def _get_float_env(self, key: str, default: float) -> float:
        """Get float from environment variable with fallback."""
        try:
            value = os.getenv(key)
            return float(value) if value else default
        except (ValueError, TypeError):
            print(f"[Config] Invalid value for {key}, using default: {default}")
            return default
    
    def _validate(self):
        """Validate configuration values."""
        if self.chunk_size < 500:
            print(f"[Config] Warning: chunk_size {self.chunk_size} is very small, minimum recommended: 500")
        if self.chunk_size > 10000:
            print(f"[Config] Warning: chunk_size {self.chunk_size} is very large, maximum recommended: 10000")
        
        if self.max_workers < 1:
            print(f"[Config] Error: max_workers must be >= 1, got {self.max_workers}")
            self.max_workers = 1
        if self.max_workers > 50:
            print(f"[Config] Warning: max_workers {self.max_workers} is very high, may cause rate limiting")
        
        if self.max_retries < 0:
            print(f"[Config] Error: max_retries must be >= 0, got {self.max_retries}")
            self.max_retries = 0
        
        if self.retry_base_delay < 0.5:
            print(f"[Config] Warning: retry_base_delay {self.retry_base_delay}s is very short")
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            'chunk_size': self.chunk_size,
            'max_workers': self.max_workers,
            'model': self.model,
            'extraction_passes': self.extraction_passes,
            'max_retries': self.max_retries,
            'retry_base_delay': self.retry_base_delay
        }
    
    def __repr__(self) -> str:
        """String representation of configuration."""
        return (
            f"LangExtractConfig("
            f"chunk_size={self.chunk_size}, "
            f"max_workers={self.max_workers}, "
            f"model={self.model}, "
            f"extraction_passes={self.extraction_passes}, "
            f"max_retries={self.max_retries}, "
            f"retry_base_delay={self.retry_base_delay}s)"
        )


# Global configuration instance
_config: Optional[LangExtractConfig] = None


def get_config() -> LangExtractConfig:
    """Get the global configuration instance (singleton pattern)."""
    global _config
    if _config is None:
        _config = LangExtractConfig()
        print(f"[Config] Initialized: {_config}")
    return _config


def reload_config() -> LangExtractConfig:
    """Reload configuration from environment variables."""
    global _config
    _config = LangExtractConfig()
    print(f"[Config] Reloaded: {_config}")
    return _config
