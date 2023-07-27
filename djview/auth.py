from functools import wraps
from typing import Callable

from django.contrib.auth import authenticate
from django.contrib.auth.models import AnonymousUser
from django.http.response import HttpResponseBase

from djview.context import Context
from djview.views import Layer, Service, view403

USER_CONTEXT_KEY = "__user__"

Rule = Callable[[Context], bool]


# authentication_layer is a decorator that wraps a view function with authentication middleware.
def authentication_layer(
    *kwarg_keys: str, user_ctx_key: str = USER_CONTEXT_KEY
) -> Layer:
    def inner(service: Service) -> Service:
        @wraps(service)
        def wrapper(ctx: Context) -> HttpResponseBase:
            ctx[user_ctx_key] = (
                authenticate(ctx.request, **{key: ctx[key] for key in kwarg_keys})
                or AnonymousUser()
            )

            return service(ctx)

        return wrapper

    return inner


# permission_layer is a decorator that wraps a view function with permission middleware that returns a 403 if the user does not have the specified permissions.
def permission_layer(*rules: Rule) -> Layer:
    def inner(service: Service) -> Service:
        @wraps(service)
        def wrapper(ctx: Context) -> HttpResponseBase:
            for rule in rules:
                if not rule(ctx):
                    return view403(ctx)

            return service(ctx)

        return wrapper

    return inner


# is_authenticated_layer is a decorator that wraps a view function with authentication middleware that returns a 403 if the user is not authenticated.
def is_authenticated_layer(user_ctx_key: str = USER_CONTEXT_KEY) -> Layer:
    def rule(ctx: Context) -> bool:
        return ctx[user_ctx_key].is_authenticated

    return permission_layer(rule)


# has_permissions_layer is a decorator that wraps a view function with authentication middleware that returns a 403 if the user does not have the specified permissions.
def has_permissions_layer(
    *permissions: str, user_ctx_key: str = USER_CONTEXT_KEY
) -> Layer:
    def rule(ctx: Context) -> bool:
        return not any((not ctx[user_ctx_key].has_perm(perm) for perm in permissions))

    return permission_layer(rule)
