from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase

from vimma import util
from vimma.models import Permission, Role, Project, Profile
from vimma.perms import ALL_PERMS, Perms


# Django validation doesn't run automatically when saving objects.
# When we'll have endpoints, we must ensure it runs there.
# We're using .full_clean() in the tests which create objects directly.


class PermissionTests(TestCase):

    def testPermissionRequiresName(self):
        """
        Permission requires non-empty name.
        """
        with self.assertRaises(ValidationError):
            Permission.objects.create().full_clean()
        Permission.objects.create(name=Perms.EDIT_SCHEDULE).full_clean()

    def testPermissionUniqueName(self):
        """
        Permissions have unique names.
        """
        Permission.objects.create(name=Perms.EDIT_SCHEDULE)
        with self.assertRaises(IntegrityError):
            Permission.objects.create(name=Perms.EDIT_SCHEDULE)

    def testCreateAllPerms(self):
        """
        Populate the database with all permissions.
        """
        for v in ALL_PERMS.values():
            Permission.objects.create(name=v)


class RoleTests(TestCase):

    def testRoleRequiresName(self):
        """
        Roles require a non-empty name.
        """
        with self.assertRaises(ValidationError):
            Role.objects.create().full_clean()
        Role.objects.create(name='Janitor').full_clean()

    def testRoleUniqueName(self):
        """
        Roles have unique names.
        """
        Role.objects.create(name='President')
        Role.objects.create(name='General')
        with self.assertRaises(IntegrityError):
            Role.objects.create(name='President')

    def testHasPerm(self):
        """
        Test assigning Permissions to users via Roles.
        """
        perm_sched = Permission.objects.create(name=Perms.EDIT_SCHEDULE)
        perm_x = Permission.objects.create(name='X')
        perm_omni = Permission.objects.create(name=Perms.OMNIPOTENT)

        sched_editors = Role.objects.create(name='Schedule Editors')
        sched_editors.permissions.add(perm_sched)
        omni_role = Role.objects.create(name='Omni Role')
        omni_role.permissions.add(perm_omni)

        nobody = util.createUser('nobody', 'n@a.com', 'pass')
        fry = util.createUser('fry', 'f@a.com', 'pass')
        fry.profile.roles.add(sched_editors)
        hubert = util.createUser('hubert', 'h@a.com', 'pass')
        hubert.profile.roles.add(sched_editors, omni_role)

        def check(user, perm, result):
            self.assertIs(util.hasPerm(user, perm), result)

        # make individual function calls, not one single call with a list,
        # to see which test fails.

        check(nobody, Perms.EDIT_SCHEDULE, False)
        check(nobody, Perms.OMNIPOTENT, False)
        check(nobody, 'X', False)
        check(nobody, 'Y', False)

        check(fry, Perms.EDIT_SCHEDULE, True)
        check(fry, Perms.OMNIPOTENT, False)
        check(fry, 'X', False)
        check(fry, 'Y', False)

        check(hubert, Perms.EDIT_SCHEDULE, True)
        check(hubert, Perms.OMNIPOTENT, True)
        check(hubert, 'X', True)
        check(hubert, 'Y', True)

        # Incorrectly created user: has no Profile
        invalid = User.objects.create_user('invalid', 'a@b.com', 'pw')
        with self.assertRaises(Profile.DoesNotExist):
            util.hasPerm(invalid, 'some-perm')


class ProjectTests(TestCase):

    def testProjectRequiresNameAndEmail(self):
        """
        Project requires a non-empty name and email.
        """
        with self.assertRaises(ValidationError):
            obj = Project.objects.create()
            try:
                obj.full_clean()
            finally:
                # prevent ‘unique’ name clash with the next .create()
                obj.delete()
        with self.assertRaises(ValidationError):
            Project.objects.create(email='a@b.com').full_clean()
        with self.assertRaises(ValidationError):
            Project.objects.create(name='prj1').full_clean()
        Project.objects.create(name='prj2', email='a@b.com').full_clean()

    def testProjectNameUnique(self):
        """
        Projects must have unique names.
        """
        Project.objects.create(name='prj', email='a@b.com')
        with self.assertRaises(IntegrityError):
            Project.objects.create(name='prj', email='a@c.com')


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
