from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from vimma import util
from vimma.models import Project, Profile


class ProjectTests(TestCase):

    def testProjectRequiresNameAndEmail(self):
        """
        Project requires a non-empty name and email.

        Django validation doesn't run automatically when saving objects.
        When we'll have endpoints, we must ensure it runs there.
        """
        with self.assertRaises(ValidationError):
            Project.objects.create().full_clean()
        with self.assertRaises(ValidationError):
            Project.objects.create(email='a@b.com').full_clean()
        with self.assertRaises(ValidationError):
            Project.objects.create(name='user').full_clean()
        Project.objects.create(name='user', email='a@b.com').full_clean()


class UserTest(TestCase):

    def testDefaultUserHasNoProfile(self):
        """
        Users directly created have no associated profile.
        """
        badUser = User.objects.create_user('a', 'a@example.com', 'pass')
        with self.assertRaises(Profile.DoesNotExist):
            badUser.profile

    def testAssociatedProfile(self):
        """
        When using util.createUser a profile is present.
        """
        u = util.createUser('a', 'a@example.com', 'pass')
        p = u.profile
        self.assertEqual(u.username, p.user.username)
