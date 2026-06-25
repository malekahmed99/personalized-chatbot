from enum import Enum


class RoleEnum(str, Enum):
    user = "user"
    assistant = "assistant"


class VoteEnum(str, Enum):
    up = "up"
    down = "down"
