"""Round-trip tests for Query.to_json / from_json.

The critical invariant: __post_init__ shifts `after` and `before` to date
boundaries, and from_json must NOT re-run __post_init__ or the cursor will
drift on every restart. These tests pin that behavior.
"""
import os
import sys
import types
from datetime import datetime

import pytest

# bot_secrets.py asserts these exist at import time. Provide dummy values so
# the exception path inside Query.__post_init__ can lazy-import without crashing.
os.environ.setdefault("ERROR_CHANNEL_ID", "1")
os.environ.setdefault("DB_NAME", "production")  # avoids the testing-only asserts
os.environ.setdefault("DISCORD_TOKEN", "x")
os.environ.setdefault("TEST_DISCORD_TOKEN", "x")
os.environ.setdefault("SEARCH_METRICS_CHANNEL_ID", "1")
os.environ.setdefault("EXPORT_METRICS_CHANNEL_ID", "1")
os.environ.setdefault("DELETE_METRICS_CHANNEL_ID", "1")
os.environ.setdefault("TEST_SEARCH_METRICS_CHANNEL_ID", "1")
os.environ.setdefault("TEST_EXPORT_METRICS_CHANNEL_ID", "1")
os.environ.setdefault("TEST_DELETE_METRICS_CHANNEL_ID", "1")
os.environ.setdefault("SERVER_COUNT_CHANNEL_ID", "1")
os.environ.setdefault("TEST_SERVER_COUNT_CHANNEL_ID", "1")


def _install_stubs():
    """Stub the discord/dotenv import graph so Query can load standalone."""
    if "discord" not in sys.modules:
        discord_mod = types.ModuleType("discord")
        discord_mod.User = type("User", (), {})
        discord_mod.TextChannel = type("TextChannel", (), {})
        discord_mod.Message = type("Message", (), {})
        discord_mod.TextChannel = type("TextChannel", (), {})
        discord_mod.__path__ = []  # mark as package
        sys.modules["discord"] = discord_mod

        ext_mod = types.ModuleType("discord.ext")
        ext_mod.__path__ = []
        sys.modules["discord.ext"] = ext_mod

        commands_mod = types.ModuleType("discord.ext.commands")
        commands_mod.Bot = type("Bot", (), {})
        sys.modules["discord.ext.commands"] = commands_mod

    if "dotenv" not in sys.modules:
        dotenv_mod = types.ModuleType("dotenv")
        dotenv_mod.__path__ = []
        dotenv_mod.load_dotenv = lambda *a, **k: None
        sys.modules["dotenv"] = dotenv_mod

        dotenv_main = types.ModuleType("dotenv.main")
        dotenv_main.load_dotenv = lambda *a, **k: None
        sys.modules["dotenv.main"] = dotenv_main


_install_stubs()

from python.models.query import Query  # noqa: E402


class _FakeBot:
    """Stand-in for discord.Client.get_user / get_channel."""

    def get_user(self, _id):
        return None

    def get_channel(self, _id):
        return None


def test_roundtrip_dates_are_idempotent():
    q = Query(after="2026-04-01", before="2026-04-05")
    blob = q.to_json()

    rehydrated = Query.from_json(blob, bot=_FakeBot())
    assert rehydrated.after == q.after
    assert rehydrated.before == q.before

    # Critical: a SECOND round-trip must not drift the cursor.
    rehydrated2 = Query.from_json(rehydrated.to_json(), bot=_FakeBot())
    assert rehydrated2.after == q.after
    assert rehydrated2.before == q.before


def test_roundtrip_after_does_not_drift_backwards():
    """Regression test for the __post_init__ drift bug.

    `__post_init__` truncates `after` to date components and subtracts 1us,
    so re-running it on the already-shifted value would shift it back another
    full day. from_json bypasses __post_init__ to prevent this.
    """
    q = Query(after="2026-04-01")
    # First post_init: 2026-04-01 -> 2026-03-31 23:59:59.999999
    assert q.after == datetime(2026, 3, 31, 23, 59, 59, 999999)

    rehydrated = Query.from_json(q.to_json(), bot=_FakeBot())
    assert rehydrated.after == datetime(2026, 3, 31, 23, 59, 59, 999999)


def test_roundtrip_preserves_simple_fields():
    q = Query(
        filename="report.pdf",
        filetype="image",
        custom_filetype="png",
        content="quarterly results",
        dm=True,
    )
    rehydrated = Query.from_json(q.to_json(), bot=_FakeBot())
    assert rehydrated.filename == "report.pdf"
    assert rehydrated.filetype == "image"
    assert rehydrated.custom_filetype == "png"
    assert rehydrated.content == "quarterly results"
    assert rehydrated.dm is True
    assert rehydrated.author is None
    assert rehydrated.channel is None


def test_roundtrip_channel_date_map():
    q = Query()
    q.channel_date_map = {
        "12345": datetime(2026, 4, 1, 12, 0, 0),
        "67890": datetime(2026, 4, 2, 8, 30, 0),
    }
    rehydrated = Query.from_json(q.to_json(), bot=_FakeBot())
    assert rehydrated.channel_date_map == q.channel_date_map


def test_roundtrip_empty_query():
    q = Query()
    rehydrated = Query.from_json(q.to_json(), bot=_FakeBot())
    assert rehydrated.filename is None
    assert rehydrated.after is None
    assert rehydrated.before is None
    assert rehydrated.channel_date_map is None
    assert rehydrated.dm is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
