from datetime import UTC, datetime


class DateTimeService:
    @staticmethod
    def utc_now() -> datetime:
        """Return the current UTC time as a naive datetime."""
        return datetime.now(UTC).replace(tzinfo=None)
