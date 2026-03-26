# config.py - Central configuration for Financial Intelligence System

import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class OllamaConfig:
    host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model: str = os.getenv("OLLAMA_MODEL", "llama3:8b")
    timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    stream: bool = False

@dataclass
class OpenAIConfig:
    api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    enabled: bool = bool(os.getenv("OPENAI_API_KEY"))

@dataclass
class DatabaseConfig:
    path: str = os.getenv("DB_PATH", "financial_intelligence.db")
    # For PostgreSQL migration: set DATABASE_URL env var
    url: Optional[str] = os.getenv("DATABASE_URL")

@dataclass
class AppConfig:
    # AI provider: "ollama" | "openai" | "auto" (try ollama, fallback to openai)
    ai_provider: str = os.getenv("AI_PROVIDER", "auto")
    backend_host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    frontend_port: int = int(os.getenv("FRONTEND_PORT", "8501"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    currency_symbol: str = "₹"
    anomaly_threshold: float = 1.4   # current > threshold × avg(last 3 months)
    rolling_window: int = 3           # months for rolling average
    high_freq_threshold: int = 5      # transactions/month = "high frequency"

@dataclass
class Config:
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    app: AppConfig = field(default_factory=AppConfig)

# Singleton
config = Config()
