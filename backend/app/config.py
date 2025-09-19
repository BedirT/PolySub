from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    storage_root: Path = Field(default=Path("../storage"), alias="STORAGE_ROOT")
    temp_dir: Path = Field(default=Path("../storage/tmp"), alias="TEMP_DIR")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    assemblyai_api_key: str | None = Field(default=None, alias="ASSEMBLYAI_API_KEY")
    default_local_model: str = Field(default="large-v3")
    ffmpeg_path: Path | None = Field(default=None, alias="FFMPEG_PATH")
    available_local_models: List[str] = Field(
        default_factory=lambda: [
            "tiny",
            "base",
            "small",
            "medium",
            "large-v3",
            "distil-large-v3",
        ]
    )
    subtitle_lead_in: float = Field(default=0.15, alias="SUBTITLE_LEAD_IN")
    subtitle_linger: float = Field(default=0.45, alias="SUBTITLE_LINGER")
    subtitle_min_gap: float = Field(default=0.08, alias="SUBTITLE_MIN_GAP")
    subtitle_min_duration: float = Field(default=0.24, alias="SUBTITLE_MIN_DURATION")
    subtitle_max_chars_per_line: int = Field(default=42, alias="SUBTITLE_MAX_CHARS")
    subtitle_max_lines: int = Field(default=2, alias="SUBTITLE_MAX_LINES")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
settings.storage_root.mkdir(parents=True, exist_ok=True)
settings.temp_dir.mkdir(parents=True, exist_ok=True)
