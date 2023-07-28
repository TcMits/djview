from functools import wraps
from typing import Callable

from django.contrib.auth import authenticate
from django.contrib.auth.models import AnonymousUser
from django.http.response import HttpResponseBase

from djview.context import Context
from djview.views import Layer, Service, case_layer, view403

USER_CONTEXT_KEY = "__user__"


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
def permission_layer(*rules: Callable[[Context], bool]) -> Layer:
    return case_layer(
        lambda ctx: any((not rule(ctx) for rule in rules)),
        service=view403,
    )


# is_authenticated_layer is a decorator that wraps a view function with authentication middleware that returns a 403 if the user is not authenticated.
def is_authenticated_layer(user_ctx_key: str = USER_CONTEXT_KEY) -> Layer:
    def rule(ctx: Context) -> bool:
        return ctx[user_ctx_key].is_authenticated

    return permission_layer(rule)


# has_permissions_layer is a decorator that wraps a view function with authentication middleware that returns a 403 if the user does not have the specified permissions.
def has_permissions_layer(
    *permissions: str, user_ctx_key: str = USER_CONTEXT_KEY
) -> Layer:
    return permission_layer(
        *(
            lambda ctx, perm=permission: ctx[user_ctx_key].has_perm(perm)
            for permission in permissions
        )
    )
