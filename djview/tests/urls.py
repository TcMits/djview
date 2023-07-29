from django.http import HttpResponse
from django.urls import path
from django.views.decorators.http import require_http_methods

from djview.auth import (
    authentication_layer,
    has_permissions_layer,
    is_authenticated_layer,
)
from djview.context import Context
from djview.crud import (
    create_service,
    delete_service,
    detail_service,
    limit_offset_filterer,
    list_service,
    model_all_filterer,
    model_delete_mutator,
    model_list_serializer,
    model_mutator,
    model_pk_filterer,
    model_serializer,
    model_set_meta_count_filterer,
    update_service,
)
from djview.tests.test_app.forms import TestModelForm
from djview.tests.test_app.models import TestModel
from djview.views import (
    context_view,
    exception_layer,
    from_http_decorator,
    into_service,
    layers,
    method_layer,
    noop_layer,
    view404,
)


@context_view()
@layers(noop_layer)
def view1(ctx: Context) -> HttpResponse:
    assert ctx.exists()
    assert ctx.request is not None
    assert ctx.data is not None

    return HttpResponse("OK")


@context_view()
@layers(exception_layer())
def view2(_: Context) -> HttpResponse:
    exception = Exception("Something went wrong")
    exception.status_code = 500
    exception.code = "SOMETHING_WENT_WRONG"
    exception.status_code = 500
    exception.details = {"foo": "bar"}

    raise exception


@context_view()
@layers(from_http_decorator(require_http_methods(["GET"])))
def view3(_: Context) -> HttpResponse:
    return HttpResponse("OK")


def view4(_: Context) -> HttpResponse:
    return HttpResponse("OK")


@context_view()
@layers(
    exception_layer(),
    authentication_layer(),
    is_authenticated_layer(),
    has_permissions_layer("test_app.view_testmodel"),
)
def view5(_: Context) -> HttpResponse:
    return HttpResponse("OK")


urlpatterns = [
    path("view1/", view1, name="view1"),
    path("view2/", view2, name="view2"),
    path("view3/", view3, name="view3"),
    path(
        "view4/",
        context_view()(
            into_service(
                from_http_decorator(require_http_methods(["GET", "PUT", "PATCH"])),
                method_layer("GET", service=view4),
                method_layer("PUT", exception_layer(), service=view2),
                service=view404,
            )
        ),
        name="view4",
    ),
    path(
        "models/",
        context_view()(
            into_service(
                exception_layer(),
                method_layer(
                    "GET",
                    service=list_service(
                        model_list_serializer(),
                        model_all_filterer(TestModel),
                        model_set_meta_count_filterer(),
                        limit_offset_filterer(),
                    ),
                ),
                method_layer(
                    "POST",
                    service=create_service(
                        model_mutator(TestModelForm),
                        model_serializer(),
                    ),
                ),
                service=view404,
            )
        ),
        name="model-list",
    ),
    path(
        "models/<int:pk>/",
        context_view()(
            into_service(
                exception_layer(),
                method_layer(
                    "GET",
                    service=detail_service(
                        model_serializer(),
                        model_all_filterer(TestModel),
                        model_pk_filterer(),
                    ),
                ),
                method_layer(
                    "PATCH",
                    service=update_service(
                        model_mutator(TestModelForm),
                        model_serializer(),
                        model_all_filterer(TestModel),
                        model_pk_filterer(),
                    ),
                ),
                method_layer(
                    "DELETE",
                    service=delete_service(
                        model_delete_mutator,
                        model_all_filterer(TestModel),
                        model_pk_filterer(),
                    ),
                ),
                service=view404,
            )
        ),
        name="model-detail",
    ),
    path("view5/", view5, name="view5"),
]
