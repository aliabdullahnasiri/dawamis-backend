from fake_useragent import UserAgent


class UserAgentService:
    """
    Service for generating and providing fake User-Agent strings.

    Useful for testing, mocking, or generating default device identifiers.
    """


    def __init__(self) -> None:
        self._user_agent = UserAgent()

    def random(self) -> str:
        """
        Return a random User-Agent string.

        Returns:
            A randomly selected User-Agent string.
        """
        return self._user_agent.random


    def chrome(self) -> str:
        """
        Return a Chrome-specific User-Agent string.

        Returns:
            A Chrome User-Agent string.
        """
        return self._user_agent.chrome


    def firefox(self) -> str:
        """
        Return a Firefox-specific User-Agent string.

        Returns:
            A Firefox User-Agent string.
        """
        return self._user_agent.firefox


    def safari(self) -> str:
        """
        Return a Safari-specific User-Agent string.

        Returns:
            A Safari User-Agent string.
        """
        return self._user_agent.safari


    def edge(self) -> str:
        """
        Return an Edge-specific User-Agent string.

        Returns:
            An Edge User-Agent string.
        """
        return self._user_agent.edge

