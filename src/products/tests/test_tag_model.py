from django.core.exceptions import ValidationError
from django.test import TestCase

from products.models import Tag


class TagTestCase(TestCase):

    def test_successful_tag_creation(self):
        tag = Tag.objects.create(name="Test Tag")
        tag.full_clean()
        self.assertEqual(Tag.objects.count(), 1)

    def test_failure_tag_creation_without_name(self):
        with self.assertRaises(ValidationError):
            tag = Tag(name="")
            tag.full_clean()
            tag.save()
        self.assertEqual(Tag.objects.count(), 0)
