from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db.utils import IntegrityError
from django.test import TestCase
import json
from rest_framework import status
from rest_framework.test import APITestCase

from vimma import util
from vimma.models import Permission, Role, Project, Profile, Schedule
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


class ScheduleTests(APITestCase):

    def testScheduleDefaults(self):
        """
        Default field values: isSpecial=False.
        """
        matrix = 7 * [48 * [True]];
        s = Schedule.objects.create(name='s', matrix=json.dumps(matrix))
        s.full_clean()
        self.assertFalse(s.isSpecial)

    def testUniqueName(self):
        """
        Schedules must have unique names.
        """
        m = json.dumps(7*[48*[True]])
        Schedule.objects.create(name='s', matrix=m)
        Schedule.objects.create(name='s2', matrix=m)
        with self.assertRaises(IntegrityError):
            Schedule.objects.create(name='s', matrix=m)

    def testMatrix(self):
        """
        Schedules require a 7×48 matrix with booleans.
        """
        count = 0
        def checkInvalid(m):
            with self.assertRaises(ValidationError):
                nonlocal count
                count += 1
                Schedule.objects.create(name=str(count),
                        matrix=json.dumps(m)).full_clean()

        checkInvalid('')
        checkInvalid(2 * [ True, False ])
        checkInvalid(7 * [ 12 * [True, False] ])

        m = 7 * [ 12 * [True, False, False, False] ]
        Schedule.objects.create(name='s', matrix=json.dumps(m)).full_clean()

    def testApiPermissions(self):
        """
        Check that reading requires no permissions, create/modify/delete does.
        """
        util.createUser('r', 'r@example.com', 'p')
        w = util.createUser('w', 'w@example.com', 'p')
        role = Role.objects.create(name='Schedule Creators')
        role.full_clean()
        perm = Permission.objects.create(name=Perms.EDIT_SCHEDULE)
        perm.full_clean()
        role.permissions.add(perm)
        w.profile.roles.add(role)

        def getList():
            response = self.client.get(reverse('schedule-list'))
            self.assertIs(response.status_code, status.HTTP_200_OK)
            return json.loads(response.content.decode('utf-8'))

        def getItem(id):
            response = self.client.get(reverse('schedule-detail', args=[id]))
            self.assertIs(response.status_code, status.HTTP_200_OK)
            return json.loads(response.content.decode('utf-8'))

        # Test Reader

        self.assertTrue(self.client.login(username='r', password='p'))
        self.assertIs(len(getList()), 0)

        m1 = json.dumps(7*[48*[False]])
        Schedule.objects.create(name='s', matrix=m1).full_clean()

        # read list
        items = getList()
        self.assertIs(len(items), 1)
        item = items[0]
        self.assertEqual(item['isSpecial'], False)

        # read individual item
        item = getItem(item['id'])

        # can't modify
        item['isSpecial'] = True
        response = self.client.put(
                reverse('schedule-detail', args=[item['id']]),
                item, format='json')
        self.assertIs(response.status_code, status.HTTP_403_FORBIDDEN)

        # can't delete
        response = self.client.delete(
                reverse('schedule-detail', args=[item['id']]))
        self.assertIs(response.status_code, status.HTTP_403_FORBIDDEN)

        # can't create
        newItem = {'name': 'NewSched', 'matrix': m1}
        response = self.client.post(reverse('schedule-list'), newItem,
                format='json')
        self.assertIs(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test Writer
        self.assertTrue(self.client.login(username='w', password='p'))

        # read list
        items = getList()
        self.assertIs(len(items), 1)

        # modify
        item = items[0]
        item['matrix'] = json.dumps(7*[24*[True, False]])
        item['isSpecial'] = True
        response = self.client.put(
                reverse('schedule-detail', args=[item['id']]),
                item, format='json')
        self.assertIs(response.status_code, status.HTTP_200_OK)

        # delete
        response = self.client.delete(
                reverse('schedule-detail', args=[item['id']]))
        self.assertIs(response.status_code, status.HTTP_204_NO_CONTENT)

        # create
        response = self.client.post(reverse('schedule-list'),
                {'name': 'NewSched', 'matrix': m1}, format='json')
        self.assertIs(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))

    def testApiValidation(self):
        """
        Check that the API runs the field validators.
        """
        w = util.createUser('w', 'w@example.com', 'p')
        role = Role.objects.create(name='Schedule Creators')
        role.full_clean()
        perm = Permission.objects.create(name=Perms.EDIT_SCHEDULE)
        perm.full_clean()
        role.permissions.add(perm)
        w.profile.roles.add(role)

        self.assertTrue(self.client.login(username='w', password='p'))
        newItem = {'name': 'NewSched', 'matrix': json.dumps([2, [True]])}
        response = self.client.post(reverse('schedule-list'), newItem,
                format='json')
        self.assertIs(response.status_code, status.HTTP_400_BAD_REQUEST)


class ApiTests(TestCase):

    def testApiRequiresLogin(self):
        """
        Logged in users see the API, others get Forbidden.
        """
        util.createUser('a', 'a@example.com', 'pass')
        def check(viewname):
            url = reverse(viewname)
            self.client.logout()
            response = self.client.get(url)
            self.assertIs(response.status_code, status.HTTP_403_FORBIDDEN)

            self.assertTrue(self.client.login(username='a', password='pass'))
            response = self.client.get(url)
            self.assertIs(response.status_code, status.HTTP_200_OK)

        # putting these on several lines to more easily see test failures
        check('api-root')
        check('schedule-list')
