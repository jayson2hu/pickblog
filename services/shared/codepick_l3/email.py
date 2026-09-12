from __future__ import annotations

from dataclasses import dataclass, field
import json
import urllib.request

from .config import get_settings
from .schemas import Brief


@dataclass
class EmailDelivery:
    to: str
    subject: str
    provider: str
    status: str
    metadata: dict


class EmailClient:
    def send_brief(self, to: str, brief: Brief) -> EmailDelivery:
        raise NotImplementedError


class EmailDeliveryError(RuntimeError):
    pass


@dataclass
class MockEmailClient(EmailClient):
    deliveries: list[EmailDelivery] = field(default_factory=list)

    def send_brief(self, to: str, brief: Brief) -> EmailDelivery:
        delivery = EmailDelivery(
            to=to,
            subject=f"CodePick brief {brief.brief_date}",
            provider="mock",
            status="sent",
            metadata={"brief_id": brief.id, "item_count": len(brief.items)},
        )
        self.deliveries.append(delivery)
        return delivery


def brief_email_body(brief: Brief) -> str:
    lines = [f"CodePick brief {brief.brief_date}", ""]
    for index, item in enumerate(brief.items, start=1):
        lines.append(f"{index}. {item.title}")
        lines.append(item.summary)
        lines.append(item.url)
        lines.append("")
    return "\n".join(lines).strip()


class ConfiguredEmailClient(EmailClient):
    def __init__(
        self,
        provider: str,
        api_key: str | None = None,
        region: str | None = None,
        sender: str = "CodePick <briefs@codepick.dev>",
        resend_api_url: str = "https://api.resend.com/emails",
    ) -> None:
        self.provider = provider
        self.api_key = api_key
        self.region = region
        self.sender = sender
        self.resend_api_url = resend_api_url

    def send_brief(self, to: str, brief: Brief) -> EmailDelivery:
        if self.provider == "resend" and not self.api_key:
            raise RuntimeError("RESEND_API_KEY is required for Resend email delivery")
        if self.provider == "ses" and not self.region:
            raise RuntimeError("SES_REGION is required for SES email delivery")
        subject = f"CodePick brief {brief.brief_date}"
        if self.provider == "resend":
            metadata = self._send_resend(to, subject, brief)
        elif self.provider == "ses":
            metadata = self._send_ses(to, subject, brief)
        else:
            raise RuntimeError(f"unsupported EMAIL_PROVIDER: {self.provider}")
        return EmailDelivery(
            to=to,
            subject=subject,
            provider=self.provider,
            status="queued",
            metadata={"brief_id": brief.id, "item_count": len(brief.items), **metadata},
        )

    def _send_resend(self, to: str, subject: str, brief: Brief) -> dict:
        payload = {
            "from": self.sender,
            "to": [to],
            "subject": subject,
            "text": brief_email_body(brief),
        }
        request = urllib.request.Request(
            self.resend_api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8") or "{}")
        except Exception as exc:
            raise EmailDeliveryError("Resend email delivery failed") from exc
        return {"provider_message_id": data.get("id")}

    def _send_ses(self, to: str, subject: str, brief: Brief) -> dict:
        try:
            import boto3  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("boto3 is required for SES email delivery") from exc
        try:
            client = boto3.client("ses", region_name=self.region)
            response = client.send_email(
                Source=self.sender,
                Destination={"ToAddresses": [to]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": brief_email_body(brief), "Charset": "UTF-8"}},
                },
            )
        except Exception as exc:
            raise EmailDeliveryError("SES email delivery failed") from exc
        return {"provider_message_id": response.get("MessageId")}


mock_email_client = MockEmailClient()


def get_email_client() -> EmailClient:
    settings = get_settings()
    if settings.email_provider == "mock":
        return mock_email_client
    if settings.email_provider in {"resend", "ses"}:
        return ConfiguredEmailClient(
            settings.email_provider,
            api_key=settings.resend_api_key,
            region=settings.ses_region,
            sender=settings.email_from,
            resend_api_url=settings.resend_api_url,
        )
    raise RuntimeError(f"unsupported EMAIL_PROVIDER: {settings.email_provider}")
