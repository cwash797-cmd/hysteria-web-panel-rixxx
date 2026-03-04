from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=4, max_length=256)
    days: int = Field(default=30, ge=0, le=3650)
    permanent: bool = False
    restart_service: bool = True


class RemoveUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    restart_service: bool = True


class RestartServiceRequest(BaseModel):
    restart_service: bool = True


class UpdateUserAccessRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    set_days: int | None = Field(default=None, ge=0, le=3650)
    add_days: int | None = Field(default=None, ge=-3650, le=3650)
    permanent: bool | None = None
    restart_service: bool = True


class IntegrationIssueRequest(BaseModel):
    tg_id: str = Field(min_length=1, max_length=64)
    plan: str = Field(min_length=1, max_length=32)
    order_id: str | None = None
    uuid: str | None = None
    email: str | None = None
    username: str | None = None
    password: str | None = None
