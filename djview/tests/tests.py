from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.http.request import urlencode
from django.test import SimpleTestCase
from django.test.client import MULTIPART_CONTENT
from django.urls import reverse

from djview.tests.test_app.models import TestModel

User = get_user_model()


class ContextTestCase(SimpleTestCase):
    databases = "__all__"

    def test_context(self):
        url = reverse("view1")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    def test_exception_layer(self):
        url = reverse("view2")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "message": "Something went wrong",
                "code": "SOMETHING_WENT_WRONG",
                "details": {"foo": "bar"},
            },
        )

    def test_from_http_decorator(self):
        url = reverse("view3")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 405)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    def test_method(self):
        url = reverse("view4")
        response = self.client.patch(url)
        self.assertEqual(response.status_code, 404)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

        response = self.client.put(url)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "message": "Something went wrong",
                "code": "SOMETHING_WENT_WRONG",
                "details": {"foo": "bar"},
            },
        )

    def test_model_list(self):
        TestModel.objects.all().delete()

        t = TestModel(name="test 1")
        t.image.save("test.png", ContentFile(b"test"), save=False)
        t.save()

        t2 = TestModel(name="test 2")
        t2.image.save("test2.png", ContentFile(b"test"), save=False)
        t2.save()

        url = reverse("model-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 2,
                "results": [
                    {
                        "pk": t.pk,
                        "model": "test_app.testmodel",
                        "fields": {
                            "name": t.name,
                            "image": t.image.name,
                        },
                    },
                    {
                        "pk": t2.pk,
                        "model": "test_app.testmodel",
                        "fields": {
                            "name": t2.name,
                            "image": t2.image.name,
                        },
                    },
                ],
            },
        )

        response = self.client.get(url, {"limit": 1, "offset": 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 2,
                "results": [
                    {
                        "pk": t.pk,
                        "model": "test_app.testmodel",
                        "fields": {
                            "name": t.name,
                            "image": t.image.name,
                        },
                    },
                ],
            },
        )

        response = self.client.get(url, {"limit": 1, "offset": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 2,
                "results": [
                    {
                        "pk": t2.pk,
                        "model": "test_app.testmodel",
                        "fields": {
                            "name": t2.name,
                            "image": t2.image.name,
                        },
                    },
                ],
            },
        )

    def test_model_detail(self):
        TestModel.objects.all().delete()

        t = TestModel(name="test 1")
        t.image.save("test.png", ContentFile(b"test"), save=False)
        t.save()

        url = reverse("model-detail", kwargs={"pk": t.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "pk": t.pk,
                "model": "test_app.testmodel",
                "fields": {
                    "name": t.name,
                    "image": t.image.name,
                },
            },
        )

        url = reverse("model-detail", kwargs={"pk": 1001})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "message": "not found",
                "code": 404,
                "details": {},
            },
        )

    def test_create_model(self):
        img = BytesIO(
            b"GIF89a\x01\x00\x01\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00"
            b"\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01\x00\x00"
        )
        img.name = "test.gif"

        url = reverse("model-list")
        response = self.client.post(
            url,
            {
                "name": "test",
                "image": img,
            },
        )
        response_json = response.json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response_json["model"], "test_app.testmodel")
        self.assertEqual(response_json["fields"]["name"], "test")
        self.assertIn("test", response_json["fields"]["image"])
        self.assertIn(".gif", response_json["fields"]["image"])

    def test_update_model(self):
        TestModel.objects.all().delete()

        t = TestModel(name="test 1")
        t.image.save("test.png", ContentFile(b"test"), save=False)
        t.save()

        img = BytesIO(
            b"GIF89a\x01\x00\x01\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00"
            b"\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01\x00\x00"
        )
        img.name = "test.gif"

        url = reverse("model-detail", kwargs={"pk": t.pk})

        data = self.client._encode_data(
            {
                "name": "test",
                "image": img,
            },
            content_type=MULTIPART_CONTENT,
        )
        response = self.client.patch(url, data, content_type=MULTIPART_CONTENT)
        response_json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["model"], "test_app.testmodel")
        self.assertEqual(response_json["fields"]["name"], "test")
        self.assertIn("test", response_json["fields"]["image"])
        self.assertIn(".gif", response_json["fields"]["image"])

        response = self.client.patch(
            url, {"name": "test 2"}, content_type="application/json; charset=utf-8"
        )
        response_json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["model"], "test_app.testmodel")
        self.assertEqual(response_json["fields"]["name"], "test 2")

        data = urlencode({"name": "test 3"})
        response = self.client.patch(
            url, data, content_type="application/x-www-form-urlencoded"
        )
        response_json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["model"], "test_app.testmodel")
        self.assertEqual(response_json["fields"]["name"], "test 3")

    def test_delete_model(self):
        TestModel.objects.all().delete()

        t = TestModel(name="test 1")
        t.image.save("test.png", ContentFile(b"test"), save=False)
        t.save()

        url = reverse("model-detail", kwargs={"pk": t.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(TestModel.objects.filter(pk=t.pk).exists())

    def test_permission(self):
        user = User.objects.create_user("test", "123456789")
        url = reverse("view5")

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(
            resp.json(),
            {
                "message": "you do not have permission to perform this action",
                "code": 403,
                "details": {},
            },
        )

        resp = self.client.get(url, HTTP_USER_ID=user.pk)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(
            resp.json(),
            {
                "message": "you do not have permission to perform this action",
                "code": 403,
                "details": {},
            },
        )

        perm = Permission.objects.get(
            content_type__app_label="test_app", codename="view_testmodel"
        )
        user.user_permissions.add(perm)
        resp = self.client.get(url, HTTP_USER_ID=user.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"OK")
