# djview

djview is a Django app that enables developers to add layers to Django views, providing a flexible and modular way to enhance the functionality of their applications. Inspired by the concept of Tower.rs, djview allows you to organize your Django views into layers, making it easier to manage complex applications with multiple concerns.

## Installation

Install using `pip`
```sh
pip install https://github.com/TcMits/djview.git@v0.1.0
```

## Basic usage

```python
@context_view()
@layers(
    exception_layer(),
    authentication_layer(),
    is_authenticated_layer(),
    has_permissions_layer("test_app.view_testmodel"),
)
def view(_: Context) -> HttpResponse:
    return HttpResponse("OK")


urlpatterns = [
    path("view/", view, name="view"),
]
```

You can see more advanced examples in tests folder
