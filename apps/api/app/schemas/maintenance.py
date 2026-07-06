from pydantic import BaseModel


class MaintenanceStatusResponse(BaseModel):
    """Public shape — deliberately only these two fields. Never add admin,
    auth, or config detail here; this is served without authentication."""

    enabled: bool
    message: str | None


class MaintenanceUpdateRequest(BaseModel):
    enabled: bool
    message: str | None = None
