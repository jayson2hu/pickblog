from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


IdType = BigInteger().with_variant(Integer, "sqlite")
JsonType = JSON().with_variant(JSONB, "postgresql")
ArrayTextType = JSON().with_variant(ARRAY(Text), "postgresql")


class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(IdType, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(120))
    locale: Mapped[str] = mapped_column(String(12), default="en")
    plan: Mapped[str] = mapped_column(String(24), default="free")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    audience_code: Mapped[str | None] = mapped_column(ForeignKey("audiences.code"))
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class TaxonomyCategoryModel(Base):
    __tablename__ = "taxonomy_categories"
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    label_en: Mapped[str] = mapped_column(String(120), nullable=False)
    label_zh: Mapped[str] = mapped_column(String(120), nullable=False)
    color_from: Mapped[str] = mapped_column(String(32), nullable=False)
    color_to: Mapped[str] = mapped_column(String(32), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AudienceModel(Base):
    __tablename__ = "audiences"
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    label_en: Mapped[str] = mapped_column(String(120), nullable=False)
    label_zh: Mapped[str] = mapped_column(String(120), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class AudienceCategoryModel(Base):
    __tablename__ = "audience_categories"
    audience_code: Mapped[str] = mapped_column(ForeignKey("audiences.code"), primary_key=True)
    category_code: Mapped[str] = mapped_column(ForeignKey("taxonomy_categories.code"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)


class SubscriptionModel(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(IdType, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    plan: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    period_end = mapped_column(DateTime(timezone=True))
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_ref: Mapped[str] = mapped_column(String(160), nullable=False)


class UserInterestModel(Base):
    __tablename__ = "user_interests"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    tag_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    weight: Mapped[int] = mapped_column(Integer, default=1)


class UserFollowModel(Base):
    __tablename__ = "user_follows"
    id: Mapped[int] = mapped_column(IdType, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(160), nullable=False)


class ReadingEventModel(Base):
    __tablename__ = "reading_events"
    id: Mapped[int] = mapped_column(IdType, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content_id: Mapped[str] = mapped_column(String(160), nullable=False)
    type: Mapped[str] = mapped_column(String(48), nullable=False)
    ts = mapped_column(DateTime(timezone=True), server_default=func.now())


class BriefModel(Base):
    __tablename__ = "briefs"
    id: Mapped[int] = mapped_column(IdType, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    vertical_code: Mapped[str | None] = mapped_column(String(64))
    brief_date = mapped_column(Date, nullable=False)
    items = mapped_column(JsonType, nullable=False)
    channels = mapped_column(JsonType, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class BookmarkModel(Base):
    __tablename__ = "bookmarks"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    content_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    note: Mapped[str | None] = mapped_column(Text)
    highlights = mapped_column(JsonType, nullable=False, default=list)


class ApiKeyModel(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(IdType, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    scopes = mapped_column(ArrayTextType, nullable=False)
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_quota: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class ApiUsageDailyModel(Base):
    __tablename__ = "api_usage_daily"
    key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id"), primary_key=True)
    day = mapped_column(Date, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)


class CompanionUsageModel(Base):
    __tablename__ = "companion_usage"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    day = mapped_column(Date, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
