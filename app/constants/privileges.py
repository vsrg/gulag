from __future__ import annotations

from enum import IntEnum
from enum import IntFlag
from enum import unique

from app.utils import escape_enum
from app.utils import pymysql_encode

__all__ = ("Privileges", "ClientPrivileges", "ClanPrivileges")


@unique
@pymysql_encode(escape_enum)
class Privileges(IntFlag):
    """Server side user privileges."""

    # privileges intended for all normal players.
    NORMAL = 1 << 0  # is an unbanned player.                   # 1
    VERIFIED = 1 << 1  # has logged in to the server in-game.   # 2

    # has bypass to low-ceiling anticheat measures (trusted).
    WHITELISTED = 1 << 2 # trusted player.                      # 4

    # donation tiers, receives some extra benefits.
    SUPPORTER = 1 << 4                                          # 8
    PREMIUM = 1 << 5                                            # 16

    # notable users, receives some extra benefits.
    ALUMNI = 1 << 7                                             # 128

    # staff permissions, able to manage server app.state.
    TOURNAMENT = 1 << 10  # able to manage match state without host.  # 1024
    NOMINATOR = 1 << 11  # able to manage maps ranked status.         # 2048
    MODERATOR = 1 << 12  # able to manage users (level 1).            # 4096
    ADMINISTRATOR = 1 << 13  # able to manage users (level 2).        # 8192
    DEVELOPER = 1 << 14  # able to manage full server app.state.      # 16384

    #* Anti Privileges
    BLOCK_AVATAR = 1 << 24
    BLOCK_BANNER = 1 << 25
    BLOCK_BACKGROUND = 1 << 26

    BLOCK_ABOUT_ME = 1 << 27           # Blocks user from changing about me
    BLOCK_WEBSITE = 1 << 28            # Blocks from changing user's website field on profile
    BLOCK_LOCATION = 1 << 29           # Same as above but location
    BLOCK_INTERESTS = 1 << 30          # Same as above but interests

    BLOCK_CLAN_CREATION = 1 << 31      # Blocks clan creation
    BLOCK_CLAN_AVATAR = 1 << 32        # Blocks changing clan avatar
    BLOCK_CLAN_BANNER = 1 << 33  # Blocks changing clan banner
    BLOCK_CLAN_ABOUT = 1 << 34         # Blocks changing clan about us field

    BLOCK_BEATMAP_REQUESTS = 1 << 35
    DONATOR = SUPPORTER | PREMIUM
    STAFF = MODERATOR | ADMINISTRATOR | DEVELOPER

    IMAGES = BLOCK_AVATAR | BLOCK_BANNER | BLOCK_BACKGROUND
    PROFILE_ABOUT_ME = BLOCK_LOCATION | BLOCK_INTERESTS | BLOCK_ABOUT_ME
    CLAN = BLOCK_CLAN_CREATION | BLOCK_CLAN_AVATAR | BLOCK_CLAN_BANNER | BLOCK_CLAN_ABOUT

@unique
@pymysql_encode(escape_enum)
class ClientPrivileges(IntFlag):
    """Client side user privileges."""

    PLAYER = 1 << 0
    MODERATOR = 1 << 1
    SUPPORTER = 1 << 2
    OWNER = 1 << 3
    DEVELOPER = 1 << 4
    TOURNAMENT = 1 << 5  # NOTE: not used in communications with osu! client


@unique
@pymysql_encode(escape_enum)
class ClanPrivileges(IntEnum):
    """A class to represent a clan members privs."""

    Member = 1
    Officer = 2
    Owner = 3

@unique
@pymysql_encode(escape_enum)
class BNPriv(IntEnum):
    """A class to represent a bn types."""

    STD = 1 << 0
    TAIKO = 1 << 1
    CATCH = 1 << 2
    MANIA = 1 << 3
