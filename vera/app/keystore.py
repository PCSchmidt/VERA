"""The user's model key, held in this process's memory only (APP-C-02).

The key is accepted once, kept in an attribute of this object, handed to a run's worker process through its environment,
and never written to a file, a log, a ledger, a response or a URL. `repr` and `str` show nothing of it.
"""

from __future__ import annotations

import re

KEY_SHAPE = re.compile(r"\S{16,300}")


class InvalidKey(ValueError):
    """The text is not shaped like a key (the message never repeats the text)."""


class SessionKey:
    def __init__(self) -> None:
        self._key: str | None = None

    def set(self, key: str) -> None:
        key = (key or "").strip()
        if not KEY_SHAPE.fullmatch(key):
            raise InvalidKey("that does not look like an API key: 16 to 300 characters with no spaces")
        self._key = key

    def get(self) -> str | None:
        return self._key

    def clear(self) -> None:
        self._key = None

    @property
    def present(self) -> bool:
        return self._key is not None

    def __repr__(self) -> str:
        return f"SessionKey(present={self.present})"

    __str__ = __repr__
