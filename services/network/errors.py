class NetworkUnavailableError(Exception):
    def __init__(self, message: str = "Network unavailable"):
        self.message = message
        super().__init__(self.message)


class ConnectFailedError(Exception):
    def __init__(self, message: str = "Connection failed"):
        self.message = message
        super().__init__(self.message)


class UnsupportedPlatformError(Exception):
    def __init__(self, message: str = "Unsupported platform"):
        self.message = message
        super().__init__(self.message)


class TailscaleUnavailableError(Exception):
    def __init__(self, message: str = "Tailscale unavailable"):
        self.message = message
        super().__init__(self.message)


class TailscaleBadResponseError(Exception):
    def __init__(self, message: str = "Invalid Tailscale LocalAPI response"):
        self.message = message
        super().__init__(self.message)
