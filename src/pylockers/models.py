"""Pydantic models for the Relaxx System API.

Field names follow the API's JSON payloads; aliases map them to
snake_case Python attributes.
"""

from enum import StrEnum
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class DoorState(StrEnum):
    UNKNOWN = "Unknown"
    OPEN = "Open"
    CLOSED = "Closed"
    LOCKED = "Locked"


class LockerMode(StrEnum):
    PERSONAL_LOCKER = "PersonalLocker"
    DYNAMIC_LOCKER = "DynamicLocker"
    FREE_LOCKER = "FreeLocker"
    PERSONAL_LOCKER_PROGRAMMING_CARD = "PersonalLockerProgrammingCard"
    PERSONAL_LOCKER_EXPIRY_DATE = "PersonalLockerExpiryDate"
    FREE_LOCKER_UID = "FreeLockerUID"


class LockerType(StrEnum):
    NET = "Net"
    SMART = "Smart"
    BLE = "Ble"
    VIRTUAL = "Virtual"
    UNKNOWN = "Unknown"


class ConnectionState(StrEnum):
    ONLINE = "Online"
    OFFLINE = "Offline"
    NOT_FOUND = "NotFound"


class LockerAction(StrEnum):
    OPEN_LOCKER = "OpenLocker"
    CLOSE_LOCKER = "CloseLocker"
    SET_MAINTENANCE = "SetMaintenance"
    REVERT_MAINTENANCE = "RevertMaintenance"
    ENABLE_LOCKER = "EnableLocker"
    DISABLE_LOCKER = "DisableLocker"
    QUIT_ALARM = "QuitAlarm"
    QUIT_ALARM_AND_ENABLE_LOCKER = "QuitAlarmAndEnableLocker"
    SYNC_TIME = "SyncTime"


class ApiModel(BaseModel):
    """Base model tolerating extra fields returned by the API."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class Locker(ApiModel):
    id: UUID
    number: str | None = None
    locker_type: LockerType | None = Field(
        default=None, validation_alias=AliasChoices("lockerType", "locker_type")
    )
    mode: LockerMode | None = None
    door_state: DoorState | None = Field(
        default=None, validation_alias=AliasChoices("doorState", "door_state")
    )
    connection_state: ConnectionState | None = Field(
        default=None,
        validation_alias=AliasChoices("connectionState", "connection_state"),
    )
    enabled: bool = True
    rented: bool = False
    blocked: bool = False
    alarmed: bool = False


class LockerUser(ApiModel):
    id: UUID
    first_name: str | None = Field(
        default=None, validation_alias=AliasChoices("firstName", "first_name")
    )
    last_name: str | None = Field(
        default=None, validation_alias=AliasChoices("lastName", "last_name")
    )
    email: str | None = None
    member_number: str | None = Field(
        default=None, validation_alias=AliasChoices("memberNumber", "member_number")
    )
    department: str | None = None
    remark: str | None = None
    is_active: bool = Field(
        default=True, validation_alias=AliasChoices("isActive", "is_active")
    )


class PagedResult[T](ApiModel):
    results: list[T] = Field(default_factory=list)
    total_records: int = Field(
        default=0, validation_alias=AliasChoices("totalRecords", "total_records")
    )
    page_number: int = Field(
        default=1, validation_alias=AliasChoices("pageNumber", "page_number")
    )
    page_size: int = Field(
        default=0, validation_alias=AliasChoices("pageSize", "page_size")
    )
