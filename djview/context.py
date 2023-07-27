from collections import UserDict
from contextlib import contextmanager
from contextvars import ContextVar, Token, copy_context
from typing import Any, Dict, Iterator, Optional

from django.http import HttpRequest

_HTTP_REQUEST_KEY: str = "__request__"
_REQUEST_CONTEXT_VAR: ContextVar[Dict[Any, Any]] = ContextVar("djview_context")


@contextmanager
def enter_context(initial_data: Optional[Dict[Any, Any]] = None) -> Iterator[None]:
    global _REQUEST_CONTEXT_VAR

    if initial_data is None:
        initial_data = {}

    token: Token = _REQUEST_CONTEXT_VAR.set(initial_data.copy())
    yield
    _REQUEST_CONTEXT_VAR.reset(token)


class Context(UserDict):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        assert (
            not args and not kwargs
        ), "Context does not accept positional or keyword arguments"

    @property
    def request(self) -> Optional[HttpRequest]:
        global _HTTP_REQUEST_KEY
        return self.get(_HTTP_REQUEST_KEY)

    def set_request(self, request: HttpRequest) -> "Context":
        global _HTTP_REQUEST_KEY
        self[_HTTP_REQUEST_KEY] = request
        return self

    @property
    def data(self) -> Dict[Any, Any]:
        global _REQUEST_CONTEXT_VAR
        return _REQUEST_CONTEXT_VAR.get()

    def exists(self) -> bool:
        global _REQUEST_CONTEXT_VAR
        return _REQUEST_CONTEXT_VAR in copy_context()

    def copy(self) -> Dict[Any, Any]:
        import copy

        return copy.copy(self.data)

    def __repr__(self) -> str:
        return f"<{__name__}.{self.__class__.__name__} {self.data}>"

    def __str__(self) -> str:
        return str(self.data)


_CONTEXT: Context = Context()
_ = _CONTEXT
