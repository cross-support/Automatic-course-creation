from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    PROJECT_NAME: str = "Research Tool"

    CREDENTIALS_PATH: str = "credentials.json"
    TOKEN_PATH: str = "token.json"
    
    class Config:
        env_file = ".env"

settings = Settings()