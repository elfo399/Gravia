from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, field_serializer
from pydantic.alias_generators import to_camel


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    @field_serializer("*", check_fields=False)
    def serialize_utc_timestamp(self, value):
        # SQLite returns naive UTC datetimes; make the API timezone explicit.
        if isinstance(value, datetime):
            return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
        return value
