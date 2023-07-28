from functools import wraps
from typing import Any, Callable, Dict, Optional

from django.http.request import HttpRequest
from django.http.response import HttpResponse, HttpResponseBase, JsonResponse

from .context import _CONTEXT, Context, enter_context

Service = Callable[[Context], HttpResponseBase]
Layer = Callable[[Service], Service]
DJView = Callable[..., HttpResponseBase]
DJViewWith1Arg = Callable[[HttpRequest], HttpResponseBase]

EXCEPTION_RESULT_CONTEXT_KEY = "__exception__"


# view204 is a view that returns a 204 response.
def view204(_: Context) -> HttpResponseBase:
    return HttpResponse(status=204)


# view404 is a view that returns a 404 response.
def view404(_: Context) -> HttpResponseBase:
    return JsonResponse(
        {"message": "not found", "code": 404, "details": {}}, status=404
    )


# view403 is a view that returns a 403 response.
def view403(_: Context) -> HttpResponseBase:
    return JsonResponse(
        {
            "message": "you do not have permission to perform this action",
            "code": 403,
            "details": {},
        },
        status=403,
    )


# view400 is a view that returns a 400 response.
def view400(details: Optional[Dict[str, Any]] = None) -> Service:
    details = details or {}

    def inner(_: Context) -> HttpResponseBase:
        return JsonResponse(
            {
                "message": "failed to validate your requests",
                "code": 400,
                "details": details,
            },
            status=400,
        )

    return inner


# context_view is a decorator that wraps a view function and provides a Context object to it.
def context_view(
    initial_data: Callable[..., Dict[Any, Any]] = lambda _, **kwargs: kwargs,
) -> Callable[[Service], DJView]:
    def inner(
        func: Callable[[Context], HttpResponseBase]
    ) -> Callable[[HttpRequest], HttpResponseBase]:
        @wraps(func)
        def wrapper(request: HttpRequest, **kwargs: Any) -> HttpResponseBase:
            with enter_context(initial_data(request, **kwargs)):
                return func(_CONTEXT.set_request(request))

        return wrapper

    return inner


# into_djview is a decorator that converts a service function into a DJView.
def into_djview(service: Service) -> DJViewWith1Arg:
    @wraps(service)
    def wrapper(request: HttpRequest) -> HttpResponseBase:
        return service(_CONTEXT.set_request(request))

    return wrapper


# from_djview is a decorator that converts a DJView into a service function.
def from_djview(djview: DJViewWith1Arg) -> Service:
    @wraps(djview)
    def wrapper(ctx: Context) -> HttpResponseBase:
        return djview(ctx.request)

    return wrapper


# layers is a decorator that wraps a view function with multiple layers of middleware.
def layers(*outers: Layer) -> Layer:
    def inner(service: Service) -> Service:
        for outer in reversed(outers):
            service = outer(service)

        return service

    return inner


# into_service is a decorator that converts a service function into a service function wrapped with multiple layers of middleware.
def into_service(*outers: Layer, service: Service) -> Service:
    l = layers(*outers)
    return l(service)


# from_http_decorator is a decorator that converts a decorator that takes a DJView into a decorator that takes a service function.
def from_http_decorator(decorator: Callable[[DJViewWith1Arg], DJViewWith1Arg]) -> Layer:
    def inner(service: Service) -> Service:
        return from_djview(decorator(into_djview(service)))

    return inner


# noop_layer is a layer that does nothing.
def noop_layer(service: Service) -> Service:
    return service


# default_exception_handler is a handler that returns a JSON response with the exception message and status code.
def default_exception_handler(ctx: Context) -> HttpResponseBase:
    exception = ctx[EXCEPTION_RESULT_CONTEXT_KEY]
    status_code = (
        500 if not hasattr(exception, "status_code") else exception.status_code
    )
    code = status_code if not hasattr(exception, "code") else exception.code
    details = {} if not hasattr(exception, "details") else exception.details
    message = (
        str(exception) if status_code != 500 else "internal server error"
    )  # hide the exception message if it's a 500 error
    return JsonResponse(
        {"message": message, "code": code, "details": details}, status=status_code
    )


# exception_layer is a layer that catches exceptions and stores them in the context.
def exception_layer(
    *outers: Layer,
    service: Service = default_exception_handler,
    result_ctx_key: str = EXCEPTION_RESULT_CONTEXT_KEY,
) -> Layer:
    exception_service = into_service(*outers, service=service)

    def inner(service: Service) -> Service:
        @wraps(service)
        def wrapper(ctx: Context) -> HttpResponseBase:
            try:
                return service(ctx)
            except Exception as e:
                ctx[result_ctx_key] = e
                return exception_service(ctx)

        return wrapper

    return inner


# case_layer is a layer that only calls the service function if the condition is true.
def case_layer(
    condition: Callable[[Context], bool], *outers: Layer, service: Service
) -> Layer:
    condition_service = into_service(*outers, service=service)

    def inner(service: Service) -> Service:
        @wraps(service)
        def wrapper(ctx: Context) -> HttpResponseBase:
            if condition(ctx):
                return condition_service(ctx)

            return service(ctx)

        return wrapper

    return inner


# method_layer is a layer that only calls the service function if the request method matches the given method.
def method_layer(method: str, *outers: Layer, service: Service) -> Layer:
    return case_layer(
        lambda ctx: ctx.request.method == method, *outers, service=service
    )
