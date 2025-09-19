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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
settings.storage_root.mkdir(parents=True, exist_ok=True)
settings.temp_dir.mkdir(parents=True, exist_ok=True)
