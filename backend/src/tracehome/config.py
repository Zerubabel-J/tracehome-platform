"""Settings come only from environment variables, never from files in the image.

Locally, docker-compose.yml sets them. On ECS, the task definition sets them, and the database
password comes from Secrets Manager at task start-up.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings
from sqlalchemy.engine import URL

# A key that is safe to publish, because it only works locally. The API refuses to start with it
# anywhere else.
LOCAL_ONLY_SIGNING_KEY = "local-development-only-signing-key-not-a-secret"


class Settings(BaseSettings):
    app_env: str = "local"

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "tracehome"
    db_user: str = "tracehome"
    db_password: str = ""

    # Demo sign-in (decision 82). Tokens expire after 5 minutes, which matches
    # "a removed agent loses access within 5 minutes" (requirements, invariant 15).
    token_signing_key: str = LOCAL_ONLY_SIGNING_KEY
    token_ttl_seconds: int = 300
    demo_sign_in_enabled: bool = True

    aws_region: str = "us-east-1"
    # The address the *browser* uses to reach S3. Only set locally (LocalStack); on AWS the
    # presigned URL points to real S3.
    s3_public_endpoint_url: str | None = None
    incoming_bucket: str = "tracehome-incoming-local"
    photos_bucket: str = "tracehome-photos-local"
    upload_results_queue_name: str = "upload-results"

    max_photo_bytes: int = 5 * 1024 * 1024
    max_photos_per_listing: int = 10
    upload_url_ttl_seconds: int = 300

    @property
    def database_url(self) -> URL:
        # URL.create escapes special characters, which RDS-generated passwords contain.
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    def check(self) -> None:
        if self.app_env != "local" and self.token_signing_key == LOCAL_ONLY_SIGNING_KEY:
            raise RuntimeError("TOKEN_SIGNING_KEY must be set outside local development")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.check()
    return settings
