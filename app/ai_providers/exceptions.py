"""Provider resolution errors (configuration / wiring)."""


class UnknownAIProviderError(LookupError):
    def __init__(self, provider_id: str) -> None:
        super().__init__(f"Unknown AI provider: {provider_id!r}")
        self.provider_id = provider_id


class MissingAIProviderCredentialsError(RuntimeError):
    def __init__(self, provider_id: str, detail: str | None = None) -> None:
        msg = f"Missing credentials for AI provider {provider_id!r}"
        if detail:
            msg = f"{msg}: {detail}"
        super().__init__(msg)
        self.provider_id = provider_id
