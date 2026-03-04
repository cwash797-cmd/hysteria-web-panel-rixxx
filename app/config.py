from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    admin_user: str
    admin_password: str
    token_ttl_minutes: int
    hysteria_config_path: str
    hysteria_service_name: str
    public_domain: str
    public_port: int
    public_sni: str
    allow_insecure_defaults: bool
    api_keys_raw: str

    @property
    def api_keys(self) -> list[str]:
        return [x.strip() for x in self.api_keys_raw.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings(
        admin_user=os.getenv("HWP_ADMIN_USER", "admin"),
        admin_password=os.getenv("HWP_ADMIN_PASSWORD", "change_me_strong_password"),
        token_ttl_minutes=int(os.getenv("HWP_TOKEN_TTL_MINUTES", "720")),
        hysteria_config_path=os.getenv("HWP_HYSTERIA_CONFIG_PATH", "/etc/hysteria/config.yaml"),
        hysteria_service_name=os.getenv("HWP_HYSTERIA_SERVICE_NAME", "hysteria-server"),
        public_domain=os.getenv("HWP_PUBLIC_DOMAIN", ""),
        public_port=int(os.getenv("HWP_PUBLIC_PORT", "443")),
        public_sni=os.getenv("HWP_PUBLIC_SNI", ""),
        allow_insecure_defaults=os.getenv("HWP_ALLOW_INSECURE_DEFAULTS", "false").lower() == "true",
        api_keys_raw=os.getenv("HWP_API_KEYS", ""),
    )
