from django import forms

from djview.tests.test_app.models import TestModel


class TestModelForm(forms.ModelForm):
    class Meta:
        model = TestModel
        fields = "__all__"
