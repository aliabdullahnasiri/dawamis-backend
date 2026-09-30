from fake_useragent import UserAgent


class UserAgentService:
    """Service for generating fake User-Agent strings."""

    def __init__(self) -> None:
        self._user_agent = UserAgent()

    def random(self) -> str:
        """Return a random User-Agent."""
        return self._user_agent.random

    def chrome(self) -> str:
        """Return a Chrome User-Agent."""
        return self._user_agent.chrome

    def firefox(self) -> str:
        """Return a Firefox User-Agent."""
        return self._user_agent.firefox

    def safari(self) -> str:
        """Return a Safari User-Agent."""
        return self._user_agent.safari

    def edge(self) -> str:
        """Return an Edge User-Agent."""
        return self._user_agent.edge
