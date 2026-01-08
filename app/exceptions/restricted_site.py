class RestrictedWebsiteError(Exception):
    """
    Raised when a website blocks automated access
    (403 / 404 / 429 or bot-detection).
    """

    def __init__(self, url: str, reason: str = "Website blocks automated access"):
        self.url = url
        self.reason = reason
        super().__init__(f"{reason}: {url}")
