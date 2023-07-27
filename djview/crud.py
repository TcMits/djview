import codecs
import itertools
import json
from io import BytesIO
from typing import Any, Callable, Dict, Iterable, Optional, OrderedDict, Tuple, Type

from django import forms
from django.conf import settings
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model
from django.http import HttpResponse
from django.http.request import (
    ImmutableList,
    MultiPartParser,
    MultiValueDict,
    QueryDict,
)
from django.http.response import HttpResponseBase
from django.test.client import JSON_CONTENT_TYPE_RE

from djview.context import Context
from djview.views import Service, view204, view400, view404

Filterer = Callable[[Context, Optional[Iterable[Any]]], Iterable[Any]]
Serializer = Callable[[Context, Any], Tuple[str, Any]]
Mutator = Callable[[Context, Any], Tuple[Any, Optional[HttpResponseBase]]]

META_CONTEXT_KEY = "__meta__"


# detail_service returns a service function that returns a JSON response for a single model instance.
def detail_service(serializer: Serializer, *filterers: Filterer) -> Service:
    def inner(ctx: Context) -> HttpResponseBase:
        instances = None
        for filterer in filterers:
            instances = filterer(ctx, instances)

        instance = None
        for instance in instances:
            break

        if instance is None:
            return view404(ctx)

        content_type, content = serializer(ctx, instance)
        return HttpResponse(content=content, content_type=content_type)

    return inner


# list_service returns a service function that returns a JSON response for a list of model instances.
def list_service(serializer: Serializer, *filterers: Filterer) -> Service:
    def inner(ctx: Context) -> HttpResponseBase:
        instances = None
        for filterer in filterers:
            instances = filterer(ctx, instances)

        content_type, content = serializer(ctx, instances)
        return HttpResponse(content=content, content_type=content_type)

    return inner


# update_service returns a service function that updates a model instance and returns a JSON response for it.
def create_service(mutater: Mutator, serializer: Serializer) -> Service:
    def inner(ctx: Context) -> HttpResponseBase:
        instance, error = mutater(ctx, None)
        if error is not None:
            return error

        content_type, content = serializer(ctx, instance)
        return HttpResponse(content=content, content_type=content_type, status=201)

    return inner


# update_service returns a service function that updates a model instance and returns a JSON response for it.
def update_service(
    mutater: Mutator, serializer: Serializer, *filterers: Filterer
) -> Service:
    def inner(ctx: Context) -> HttpResponseBase:
        instances = None
        for filterer in filterers:
            instances = filterer(ctx, instances)

        instance = None
        for instance in instances:
            break

        if instance is None:
            return view404(ctx)

        instance, error = mutater(ctx, instance)
        if error is not None:
            return error

        content_type, content = serializer(ctx, instance)
        return HttpResponse(content=content, content_type=content_type)

    return inner


# delete_service returns a service function that deletes a model instance and returns a JSON response for it.
def delete_service(mutater: Mutator, *filterers: Filterer) -> Service:
    def inner(ctx: Context) -> HttpResponseBase:
        instances = None
        for filterer in filterers:
            instances = filterer(ctx, instances)

        instance = None
        for instance in instances:
            break

        if instance is None:
            return view404(ctx)

        _, error = mutater(ctx, instance)
        if error is not None:
            return error

        return view204(ctx)

    return inner


def model_serializer(_: Context, instance: Any) -> Tuple[str, Any]:
    return "application/json", serializers.serialize("json", [instance])[1:-1]


def model_list_serializer(meta_key: str = META_CONTEXT_KEY) -> Serializer:
    def inner(ctx: Context, instances: Any) -> Tuple[str, Any]:
        meta: Optional[Dict[str, Any]] = ctx.get(meta_key)
        if meta is not None:
            content = OrderedDict(
                {
                    **meta,
                    "results": serializers.serialize("python", instances),
                }
            )

            return "application/json", json.dumps(content, cls=DjangoJSONEncoder)

        return "application/json", serializers.serialize("json", instances)

    return inner


def model_all_filterer(model: Type[Model]) -> Filterer:
    def inner(_ctx: Context, _: Optional[Iterable[Any]]) -> Iterable[Any]:
        return model.objects.all()

    return inner


def model_set_meta_count_filterer(meta_key: str = META_CONTEXT_KEY) -> Filterer:
    def inner(ctx: Context, instances: Optional[Iterable[Any]]) -> Iterable[Any]:
        meta: Dict[str, Any] = ctx.get(meta_key, {})
        meta["count"] = instances.count()
        ctx[meta_key] = meta

        return instances

    return inner


def limit_offset_filterer(
    limit_kwarg: str = "limit", offset_kwarg: str = "offset"
) -> Filterer:
    def inner(ctx: Context, instances: Optional[Iterable[Any]]) -> Iterable[Any]:
        try:
            limit = int(ctx.request.GET.get(limit_kwarg, 10))
        except (TypeError, ValueError):
            limit = 10

        try:
            offset = int(ctx.request.GET.get(offset_kwarg, 0))
        except (TypeError, ValueError):
            offset = 0

        return itertools.islice(instances, offset, offset + min(limit, 500))

    return inner


def model_pk_filterer(pk_kwarg: str = "pk") -> Filterer:
    def inner(ctx: Context, instances: Optional[Iterable[Any]]) -> Iterable[Any]:
        pk = ctx[pk_kwarg]
        return instances.filter(pk=pk)

    return inner


def model_mutator(form: Type[forms.ModelForm]) -> Mutator:
    default_encoding = settings.DEFAULT_CHARSET

    def inner(ctx: Context, instance: Any) -> Tuple[Any, Optional[HttpResponseBase]]:
        encoding = ctx.request.encoding or default_encoding
        body_reader = (
            BytesIO(ctx.request.body) if hasattr(ctx.request, "_body") else ctx.request
        )
        data, files = QueryDict(encoding=encoding), MultiValueDict()

        if ctx.request.content_type.startswith("multipart"):
            data, files = MultiPartParser(
                ctx.request.META,
                body_reader,
                ImmutableList(ctx.request.upload_handlers),
                encoding,
            ).parse()
        elif JSON_CONTENT_TYPE_RE.match(ctx.request.content_type):
            data, files = (
                json.load(codecs.getreader(encoding)(body_reader)),
                MultiValueDict(),
            )
        elif ctx.request.content_type == "application/x-www-form-urlencoded":
            data, files = (
                QueryDict(body_reader.read(), encoding=encoding),
                MultiValueDict(),
            )

        form_instance = form(data=data, files=files, instance=instance)
        if form_instance.is_valid():
            return form_instance.save(), None

        return None, view400(form_instance.errors.get_json_data())(ctx)

    return inner


def model_delete_mutator(
    _: Context, instance: Any
) -> Tuple[Any, Optional[HttpResponseBase]]:
    instance.delete()
    return instance, None
