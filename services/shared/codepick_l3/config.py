from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    jwt_secret: str = "dev-secret"
    auth_login_mode: str = "development"
    paddle_webhook_secret: str = "dev-webhook-secret"
    companion_free_daily: int = 5
    api_rate_free_rpm: int = 20
    api_quota_free_day: int = 200
    l3_use_stub_l2: bool = True
    l2_base_url: str | None = None
    l2_api_key: str | None = None
    email_provider: str = "mock"
    resend_api_key: str | None = None
    resend_api_url: str = "https://api.resend.com/emails"
    email_from: str = "CodePick <briefs@codepick.dev>"
    ses_region: str | None = None
    billing_environment: str = "sandbox"
    paddle_checkout_base_url: str = "https://sandbox-payments.codepick.local"
    default_locale: str = "en"
    supported_locales: tuple[str, ...] = ("en", "zh")
    price_pro_month_usd: str = "8"
    price_pro_year_usd: str = "79"
    price_earlybird_usd: str = "4.9"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        jwt_secret=os.getenv("JWT_SECRET", "dev-secret"),
        auth_login_mode=os.getenv("L3_AUTH_LOGIN_MODE", "development").lower(),
        paddle_webhook_secret=os.getenv("PADDLE_WEBHOOK_SECRET", "dev-webhook-secret"),
        companion_free_daily=int(os.getenv("COMPANION_FREE_DAILY", "5")),
        api_rate_free_rpm=int(os.getenv("API_RATE_FREE_RPM", "20")),
        api_quota_free_day=int(os.getenv("API_QUOTA_FREE_DAY", "200")),
        l3_use_stub_l2=os.getenv("L3_USE_STUB_L2", "true").lower() == "true",
        l2_base_url=os.getenv("L2_BASE_URL"),
        l2_api_key=os.getenv("L2_API_KEY"),
        email_provider=os.getenv("EMAIL_PROVIDER", "mock"),
        resend_api_key=os.getenv("RESEND_API_KEY"),
        resend_api_url=os.getenv("RESEND_API_URL", "https://api.resend.com/emails"),
        email_from=os.getenv("EMAIL_FROM", "CodePick <briefs@codepick.dev>"),
        ses_region=os.getenv("SES_REGION"),
        billing_environment=os.getenv("BILLING_ENVIRONMENT", "sandbox"),
        paddle_checkout_base_url=os.getenv("PADDLE_CHECKOUT_BASE_URL", "https://sandbox-payments.codepick.local"),
        default_locale=os.getenv("DEFAULT_LOCALE", "en"),
        supported_locales=tuple(os.getenv("SUPPORTED_LOCALES", "en,zh").split(",")),
        price_pro_month_usd=os.getenv("PRICE_PRO_MONTH_USD", "8"),
        price_pro_year_usd=os.getenv("PRICE_PRO_YEAR_USD", "79"),
        price_earlybird_usd=os.getenv("PRICE_EARLYBIRD_USD", "4.9"),
    )


def reset_settings_cache() -> None:
    get_settings.cache_clear()
