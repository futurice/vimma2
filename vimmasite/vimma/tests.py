from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db.utils import IntegrityError
from django.test import TestCase
import json
from rest_framework import status
from rest_framework.test import APITestCase

from vimma import util
from vimma.models import Permission, Role, Project, Profile, TimeZone, Schedule
from vimma.perms import ALL_PERMS, Perms


# Django validation doesn't run automatically when saving objects.
# When we'll have endpoints, we must ensure it runs there.
# We're using .full_clean() in the tests which create objects directly.


class PermissionTests(TestCase):

    def test_permission_requires_name(self):
        """
        Permission requires non-empty name.
        """
        with self.assertRaises(ValidationError):
            Permission.objects.create().full_clean()
        Permission.objects.create(name=Perms.EDIT_SCHEDULE).full_clean()

    def test_permission_unique_name(self):
        """
        Permissions have unique names.
        """
        Permission.objects.create(name=Perms.EDIT_SCHEDULE)
        with self.assertRaises(IntegrityError):
            Permission.objects.create(name=Perms.EDIT_SCHEDULE)

    def test_create_all_perms(self):
        """
        Populate the database with all permissions.
        """
        for v in ALL_PERMS.values():
            Permission.objects.create(name=v)


class RoleTests(TestCase):

    def test_role_requires_name(self):
        """
        Roles require a non-empty name.
        """
        with self.assertRaises(ValidationError):
            Role.objects.create().full_clean()
        Role.objects.create(name='Janitor').full_clean()

    def test_role_unique_name(self):
        """
        Roles have unique names.
        """
        Role.objects.create(name='President')
        Role.objects.create(name='General')
        with self.assertRaises(IntegrityError):
            Role.objects.create(name='President')

    def test_has_perm(self):
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

        nobody = util.create_vimma_user('nobody', 'n@a.com', 'pass')
        fry = util.create_vimma_user('fry', 'f@a.com', 'pass')
        fry.profile.roles.add(sched_editors)
        hubert = util.create_vimma_user('hubert', 'h@a.com', 'pass')
        hubert.profile.roles.add(sched_editors, omni_role)

        def check(user, perm, result):
            self.assertIs(util.has_perm(user, perm), result)

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
            util.has_perm(invalid, 'some-perm')


class ProjectTests(TestCase):

    def test_project_requires_name_and_email(self):
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

    def test_project_name_unique(self):
        """
        Projects must have unique names.
        """
        Project.objects.create(name='prj', email='a@b.com')
        with self.assertRaises(IntegrityError):
            Project.objects.create(name='prj', email='a@c.com')


class UserTest(TestCase):

    def test_default_user_has_no_profile(self):
        """
        Users directly created have no associated profile.
        """
        bad_user = User.objects.create_user('a', 'a@example.com', 'pass')
        with self.assertRaises(Profile.DoesNotExist):
            bad_user.profile

    def test_associated_profile(self):
        """
        When using util.create_vimma_user a profile is present.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        p = u.profile
        self.assertEqual(u.username, p.user.username)


class ScheduleTests(APITestCase):

    def test_schedule_defaults(self):
        """
        Default field values: is_special=False.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        matrix = 7 * [48 * [True]];
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(matrix))
        s.full_clean()
        self.assertFalse(s.is_special)

    def test_unique_name(self):
        """
        Schedules must have unique names.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        m = json.dumps(7*[48*[True]])
        Schedule.objects.create(name='s', timezone=tz, matrix=m)
        Schedule.objects.create(name='s2', timezone=tz, matrix=m)
        with self.assertRaises(IntegrityError):
            Schedule.objects.create(name='s', timezone=tz, matrix=m)

    def test_matrix(self):
        """
        Schedules require a 7×48 matrix with booleans.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        count = 0
        def checkInvalid(m):
            with self.assertRaises(ValidationError):
                nonlocal count
                count += 1
                Schedule.objects.create(name=str(count), timezone=tz,
                        matrix=json.dumps(m)).full_clean()

        checkInvalid('')
        checkInvalid(2 * [ True, False ])
        checkInvalid(7 * [ 12 * [True, False] ])

        m = 7 * [ 12 * [True, False, False, False] ]
        Schedule.objects.create(name='s', timezone=tz, matrix=json.dumps(m)
                ).full_clean()

    def test_requires_timezone(self):
        """
        Schedule requires a timezone.
        """
        m = json.dumps(7*[48*[True]])
        with self.assertRaises(IntegrityError):
            Schedule.objects.create(name='s', matrix=m)

    def test_api_permissions(self):
        """
        Check that reading requires no permissions, create/modify/delete does.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        util.create_vimma_user('r', 'r@example.com', 'p')
        w = util.create_vimma_user('w', 'w@example.com', 'p')
        role = Role.objects.create(name='Schedule Creators')
        role.full_clean()
        perm = Permission.objects.create(name=Perms.EDIT_SCHEDULE)
        perm.full_clean()
        role.permissions.add(perm)
        w.profile.roles.add(role)

        def get_list():
            response = self.client.get(reverse('schedule-list'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            return response.data['results']

        def get_item(id):
            response = self.client.get(reverse('schedule-detail', args=[id]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            return json.loads(response.content.decode('utf-8'))

        # Test Reader

        self.assertTrue(self.client.login(username='r', password='p'))
        self.assertEqual(len(get_list()), 0)

        m1 = json.dumps(7*[48*[False]])
        Schedule.objects.create(name='s', timezone=tz, matrix=m1).full_clean()

        # read list
        items = get_list()
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item['is_special'], False)

        # read individual item
        item = get_item(item['id'])

        # can't modify
        item['is_special'] = True
        response = self.client.put(
                reverse('schedule-detail', args=[item['id']]),
                item, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # can't delete
        response = self.client.delete(
                reverse('schedule-detail', args=[item['id']]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # can't create
        new_item = {'name': 'NewSched', 'matrix': m1, 'timezone': tz.id}
        response = self.client.post(reverse('schedule-list'), new_item,
                format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Test Writer
        self.assertTrue(self.client.login(username='w', password='p'))

        # read list
        items = get_list()
        self.assertEqual(len(items), 1)

        # modify
        item = items[0]
        item['matrix'] = json.dumps(7*[24*[True, False]])
        item['is_special'] = True
        response = self.client.put(
                reverse('schedule-detail', args=[item['id']]),
                item, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # delete
        response = self.client.delete(
                reverse('schedule-detail', args=[item['id']]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # create
        response = self.client.post(reverse('schedule-list'),
                {'name': 'NewSched', 'matrix': m1, 'timezone': tz.id},
                format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        result = json.loads(response.content.decode('utf-8'))

    def test_api_validation(self):
        """
        Check that the API runs the field validators.
        """
        w = util.create_vimma_user('w', 'w@example.com', 'p')
        role = Role.objects.create(name='Schedule Creators')
        role.full_clean()
        perm = Permission.objects.create(name=Perms.EDIT_SCHEDULE)
        perm.full_clean()
        role.permissions.add(perm)
        w.profile.roles.add(role)

        self.assertTrue(self.client.login(username='w', password='p'))
        new_item = {'name': 'NewSched', 'matrix': json.dumps([2, [True]])}
        response = self.client.post(reverse('schedule-list'), new_item,
                format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TimeZoneTests(APITestCase):

    def test_timezone_requires_name(self):
        """
        TimeZone requires non-empty name.
        """
        with self.assertRaises(ValidationError):
            TimeZone().full_clean()
        with self.assertRaises(ValidationError):
            TimeZone(name='').full_clean()
        tz = TimeZone(name='America/Los_Angeles')
        tz.full_clean()
        tz.save()

    def test_timezone_unique_name(self):
        """
        TimeZones must have unique names.
        """
        TimeZone.objects.create(name='America/Los_Angeles').full_clean()
        with self.assertRaises(IntegrityError):
            TimeZone.objects.create(name='America/Los_Angeles')

    def test_api_permissions(self):
        """
        Check that everyone can read, no one can create/modify/delete.
        """
        util.create_vimma_user('a', 'a@example.com', 'p')
        user_b = util.create_vimma_user('b', 'b@example.com', 'p')
        role = Role.objects.create(name='Omni')
        role.full_clean()
        perm = Permission.objects.create(name=Perms.OMNIPOTENT)
        perm.full_clean()
        role.permissions.add(perm)
        user_b.profile.roles.add(role)

        def get_list():
            response = self.client.get(reverse('timezone-list'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            return response.data['results']

        def get_item(id):
            response = self.client.get(reverse('timezone-detail', args=[id]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            return json.loads(response.content.decode('utf-8'))

        # Test Reading

        self.assertTrue(self.client.login(username='a', password='p'))
        self.assertEqual(len(get_list()), 0)
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        items = get_list()
        self.assertEqual(len(items), 1)

        # read individual item
        item = get_item(items[0]['id'])

        # Test Writing

        self.assertTrue(self.client.login(username='b', password='p'))
        self.assertEqual(len(get_list()), 1)

        # can't modify
        item['name'] = 'Europe/Berlin'
        response = self.client.put(
                reverse('timezone-detail', args=[item['id']]),
                item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(
                reverse('timezone-detail', args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        new_item = {'name': 'Europe/London'}
        response = self.client.post(reverse('timezone-list'), new_item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


class ApiTests(TestCase):

    def test_api_requires_login(self):
        """
        Logged in users see the API, others get Forbidden.
        """
        util.create_vimma_user('a', 'a@example.com', 'pass')
        def check(viewname):
            url = reverse(viewname)
            self.client.logout()
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            self.assertTrue(self.client.login(username='a', password='pass'))
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # putting these on several lines to more easily see test failures
        check('api-root')
        check('schedule-list')

    def test_pagination(self):
        """
        Check that the API uses pagination.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        matrix = 7*[16*[True, True, False]]
        page_size = settings.REST_FRAMEWORK['PAGINATE_BY']
        for i in range(page_size+1):
            Schedule.objects.create(name=str(i), timezone=tz, matrix=matrix)

        n, pages = 0, 0
        url = reverse('schedule-list')
        while url:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            n += len(response.data['results'])
            pages += 1
            url = response.data['next']

        self.assertEqual(n, page_size+1)
        self.assertEqual(pages, 2)


class WebViewsPermissionTests(TestCase):

    def test_login_required(self):
        """
        You must be logged in to access the webpage views.
        """
        util.create_vimma_user('a', 'a@example.com', 'pass')
        def check(viewname):
            url = reverse(viewname)
            self.client.logout()
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            self.assertTrue(self.client.login(username='a', password='pass'))
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        check('index')
