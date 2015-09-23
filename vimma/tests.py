import datetime, urllib
from django.conf import settings
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.utils import IntegrityError, DataError
from django.test import TestCase
from django.utils.timezone import utc
import json
import pytz
import ipaddress
from rest_framework import status
from rest_framework.test import APITestCase

from vimma import util
from vimma.actions import Actions
from vimma import expiry
from vimma.models import (
    Permission, Role,
    Project, TimeZone, Schedule, Provider,
    User,
)
from vimma.perms import ALL_PERMS, Perms

class PermissionTests(TestCase):

    def test_permission_requires_name(self):
        """
        Permission requires non-empty name.
        """
        with self.assertRaises(ValidationError):
            Permission.objects.create()
        Permission.objects.create(name=Perms.EDIT_SCHEDULE)

    def test_permission_unique_name(self):
        """
        Permissions have unique names.
        """
        Permission.objects.create(name=Perms.EDIT_SCHEDULE)
        with self.assertRaises(ValidationError):
            Permission.objects.create(name=Perms.EDIT_SCHEDULE)

    def test_create_all_perms(self):
        """
        Populate the database with all permissions.
        """
        for v in ALL_PERMS:
            Permission.objects.create(name=v)


class RoleTests(TestCase):

    def test_role_requires_name(self):
        """
        Roles require a non-empty name.
        """
        with self.assertRaises(ValidationError):
            Role.objects.create()
        Role.objects.create(name='Janitor')

    def test_role_unique_name(self):
        """
        Roles have unique names.
        """
        Role.objects.create(name='President')
        Role.objects.create(name='General')
        with self.assertRaises(ValidationError):
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
        fry.roles.add(sched_editors)
        hubert = util.create_vimma_user('hubert', 'h@a.com', 'pass')
        hubert.roles.add(sched_editors, omni_role)

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


class ProjectTests(APITestCase):

    def test_project_requires_name_and_email(self):
        """
        Project requires a non-empty name
        """
        with self.assertRaises(ValidationError):
            obj = Project.objects.create()
            obj.delete()
        Project.objects.create(name='prj2', email='a@b.com')

    def test_project_name_unique(self):
        """
        Projects must have unique names.
        """
        Project.objects.create(name='prj', email='a@b.com')
        with self.assertRaises(ValidationError):
            Project.objects.create(email='a@c.com')

    def test_api_permissions(self):
        """
        Users can read projects they're members of. A permission lets them
        read all projects. The API doesn't allow writing.
        """
        user_a = util.create_vimma_user('a', 'a@example.com', 'p')
        user_b = util.create_vimma_user('b', 'b@example.com', 'p')

        role = Role.objects.create(name='All Seeing')
        perm = Permission.objects.create(name=Perms.READ_ANY_PROJECT)
        role.permissions.add(perm)

        user_b.roles.add(role)

        prj_a = Project.objects.create(name='PrjA', email='a@prj.com')
        prj_b = Project.objects.create(name='PrjB', email='b@prj.com')
        user_a.projects.add(prj_a)
        user_b.projects.add(prj_b)

        def get_list():
            response = self.client.get(reverse('project-list'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            return response.data['results']

        def get_item(id):
            response = self.client.get(reverse('project-detail', args=[id]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            return json.loads(response.content.decode('utf-8'))

        # Regular users can only read their projects
        self.assertTrue(self.client.login(username='a', password='p'))
        items = get_list()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['id'], prj_a.id)

        response = self.client.get(reverse('project-detail', args=[prj_b.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Privileged users can see all projects
        self.assertTrue(self.client.login(username='b', password='p'))
        items = get_list()
        self.assertEqual({p['id'] for p in items}, {prj_a.id, prj_b.id})

        # can't modify
        item = get_item(prj_b.id)
        item['name'] = 'Renamed'
        response = self.client.put(reverse('project-detail', args=[prj_b.id]),
                item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('project-detail',
            args=[prj_b.id]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('project-list'), item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


class UserTest(APITestCase):

    def test_API(self):
        """
        Everyone can read all users. Only some fields are exposed.
        The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(len(items), 1)

        response = self.client.get(reverse('user-detail',
            args=[user.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data

        # check fields
        self.assertEqual(set(item.keys()), {'id', 'username',
            'first_name', 'last_name', 'email', 'projects', 'content_type', 'roles',})

        # can't modify
        response = self.client.put(reverse('user-detail',
            args=[item['id']]), item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('user-detail',
            args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('user-list'), item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


class ProfileTest(APITestCase):

    def test_API(self):
        """
        Everyone can read all users. Only some fields are exposed.
        The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(len(items), 1)

        response = self.client.get(reverse('user-detail',
            args=[user.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data

        # check fields
        self.assertEqual(set(item.keys()), {'id', 'first_name', 'last_name',
            'username', 'email', 'projects', 'content_type', 'roles',})

        # can't modify
        response = self.client.put(reverse('user-detail',
            args=[item['id']]), item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('user-detail',
            args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('user-list'), item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_API_filter(self):
        """
        Filter users by: project, user.
        """
        u_a = util.create_vimma_user('a', 'a@example.com', 'p')
        u_b = util.create_vimma_user('b', 'b@example.com', 'p')
        u_c = util.create_vimma_user('c', 'c@example.com', 'p')

        p1 = Project.objects.create(name='P1', email='p1@x.com')
        p2 = Project.objects.create(name='P2', email='p2@x.com')
        p3 = Project.objects.create(name='P3', email='p3@x.com')

        u_a.projects.add(p1, p2)
        u_b.projects.add(p2, p3)
        u_c.projects.add(p3)

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get('{}?projects={}'.format(
            reverse('user-list'), p2.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(set(i['id'] for i in items),
                {u_a.id, u_b.id})

        response = self.client.get(reverse('user-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(set(i['id'] for i in items),
                {u_a.id, u_b.id, u_c.id})

        response = self.client.get('{}?id={}'.format(reverse('user-list'), u_a.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(set(i['id'] for i in items), {u_a.id})


class ScheduleTests(APITestCase):

    def test_schedule_defaults(self):
        """
        Default field values: is_special=False.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        matrix = 7 * [48 * [True]];
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(matrix))
        self.assertIs(s.is_special, False)

    def test_unique_name(self):
        """
        Schedules must have unique names.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        m = json.dumps(7*[48*[True]])
        Schedule.objects.create(name='s', timezone=tz, matrix=m)
        Schedule.objects.create(name='s2', timezone=tz, matrix=m)
        with self.assertRaises(ValidationError):
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
                        matrix=json.dumps(m))

        checkInvalid('')
        checkInvalid(2 * [ True, False ])
        checkInvalid(7 * [ 12 * [True, False] ])

        m = 7 * [ 12 * [True, False, False, False] ]
        Schedule.objects.create(name='s', timezone=tz, matrix=json.dumps(m)
                )

    def test_schedule_requires_timezone(self):
        m = json.dumps(7*[48*[True]])
        with self.assertRaises(ValidationError):
            Schedule.objects.create(name='s', matrix=m)

    def test_api_permissions(self):
        """
        Check that reading requires no permissions, create/modify/delete does.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        util.create_vimma_user('r', 'r@example.com', 'p')
        w = util.create_vimma_user('w', 'w@example.com', 'p')
        role = Role.objects.create(name='Schedule Creators')
        perm = Permission.objects.create(name=Perms.EDIT_SCHEDULE)
        role.permissions.add(perm)
        w.roles.add(role)

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
        Schedule.objects.create(name='s', timezone=tz, matrix=m1)

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
        perm = Permission.objects.create(name=Perms.EDIT_SCHEDULE)
        role.permissions.add(perm)
        w.roles.add(role)

        self.assertTrue(self.client.login(username='w', password='p'))
        new_item = {'name': 'NewSched', 'matrix': json.dumps([2, [True]])}
        response = self.client.post(reverse('schedule-list'), new_item,
                format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_schedule_at_tstamp(self):
        """
        Check the util.schedule_at_tstamp function.
        """
        for tz_name in ['America/Los_Angeles', 'Europe/Madrid', 'Asia/Tokyo']:
            tz = pytz.timezone(tz_name)
            tz_obj = TimeZone.objects.create(name=tz_name)
            matrix = 5*[8*2*[False] + 8*2*[True] + 8*2*[False]]+ 2*[48*[False]]
            s = Schedule.objects.create(name='Weekdays 8am→4pm, ' + tz_name,
                    timezone=tz_obj, matrix=json.dumps(matrix))

            for naive in [
                    datetime.datetime(2014, 2, 3, 8),
                    datetime.datetime(2014, 2, 4, 14),
                    datetime.datetime(2014, 2, 7, 8, 30),
                    datetime.datetime(2014, 2, 7, 15, 59, 59),
                    ]:
                aware = tz.localize(naive)
                tstamp = aware.timestamp()
                self.assertIs(util.schedule_at_tstamp(s, tstamp), True)

            for naive in [
                    datetime.datetime(2014, 2, 2, 13),
                    datetime.datetime(2014, 2, 3, 7, 59, 59),
                    datetime.datetime(2014, 2, 3, 16),
                    datetime.datetime(2014, 2, 3, 22),
                    datetime.datetime(2014, 2, 4, 7, 20),
                    datetime.datetime(2014, 2, 4, 17, 30),
                    datetime.datetime(2014, 2, 8),
                    datetime.datetime(2014, 2, 8, 11),
                    ]:
                aware = tz.localize(naive)
                tstamp = aware.timestamp()
                self.assertIs(util.schedule_at_tstamp(s, tstamp), False)


class TimeZoneTests(APITestCase):

    def test_timezone_requires_name(self):
        """
        TimeZone requires non-empty name.
        """
        with self.assertRaises(ValidationError):
            TimeZone.objects.create()
        with self.assertRaises(ValidationError):
            TimeZone.objects.create(name='')
        tz = TimeZone(name='America/Los_Angeles')
        tz.save()

    def test_timezone_unique_name(self):
        """
        TimeZones must have unique names.
        """
        TimeZone.objects.create(name='America/Los_Angeles')
        with self.assertRaises(ValidationError):
            TimeZone.objects.create(name='America/Los_Angeles')

    def test_api_permissions(self):
        """
        Check that everyone can read, no one can create/modify/delete.
        """
        util.create_vimma_user('a', 'a@example.com', 'p')
        user_b = util.create_vimma_user('b', 'b@example.com', 'p')
        role = Role.objects.create(name='Omni')
        perm = Permission.objects.create(name=Perms.OMNIPOTENT)
        role.permissions.add(perm)
        user_b.roles.add(role)

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
        page_size = settings.REST_FRAMEWORK['PAGE_SIZE']
        for i in range(page_size+1):
            Schedule.objects.create(name=str(i), timezone=tz, matrix=json.dumps(matrix))

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
        def check_login_required(viewname):
            url = reverse(viewname)
            self.client.logout()
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            self.assertTrue(self.client.login(username='a', password='pass'))
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        def check_public(viewname):
            url = reverse(viewname)
            self.client.logout()
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        for viewname in ('index', 'base_js'):
            check_login_required(viewname)

        # allow unauthenticated access to 'test' for easy browser automation
        for viewname in ('test',):
            check_public(viewname)



class CreatePowerOnOffRebootDestroyVMTests(TestCase):
    """
    Test the above operations on a VM, as the permissions are related.
    """

    def test_login_required(self):
        """
        The user must be logged in.
        """
        for view_name in ('createVM', 'powerOnVM', 'powerOffVM', 'rebootVM',
                'destroyVM'):
            response = self.client.get(reverse(view_name))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unsupported_methods(self):
        """
        Only POST is supported (e.g. GET, PUT, DELETE are not).
        """
        util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        for url in map(reverse, ('createVM', 'powerOnVM', 'powerOffVM',
            'rebootVM', 'destroyVM')):
            for meth in self.client.get, self.client.put, self.client.delete:
                response = meth(url)
                self.assertEqual(response.status_code,
                        status.HTTP_405_METHOD_NOT_ALLOWED)

class OverrideScheduleTests(TestCase):
    """
    Test the overrideSchedule endpoint and util.* helper.
    """

    def test_login_required(self):
        """
        The user must be logged in.
        """
        response = self.client.get(reverse('overrideSchedule'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unsupported_methods(self):
        """
        Only POST is supported (e.g. GET, PUT, DELETE are not).
        """
        util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        url = reverse('overrideSchedule')
        for meth in self.client.get, self.client.put, self.client.delete:
            response = meth(url)
            self.assertEqual(response.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED)


class ChangeVMScheduleTests(TestCase):
    """
    Test the changeVMSchedule endpoint.
    """

    def test_login_required(self):
        """
        The user must be logged in.
        """
        response = self.client.get(reverse('changeVMSchedule'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unsupported_methods(self):
        """
        Only POST is supported (e.g. GET, PUT, DELETE are not).
        """
        util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        url = reverse('changeVMSchedule')
        for meth in self.client.get, self.client.put, self.client.delete:
            response = meth(url)
            self.assertEqual(response.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED)


class SetExpirationTests(TestCase):
    """
    Test the setExpiration endpoint.
    """

    def test_login_required(self):
        """
        The user must be logged in.
        """
        response = self.client.get(reverse('setExpiration'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unsupported_methods(self):
        """
        Only POST is supported (e.g. GET, PUT, DELETE are not).
        """
        util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        url = reverse('setExpiration')
        for meth in self.client.get, self.client.put, self.client.delete:
            response = meth(url)
            self.assertEqual(response.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED)


class CreateDeleteFirewallRuleTests(TestCase):
    """
    Test the create- and delete- firewall rule endpoints.
    """

    def test_login_required(self):
        """
        The user must be logged in.
        """
        for view_name in ('createFirewallRule', 'deleteFirewallRule'):
            response = self.client.get(reverse(view_name))
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unsupported_methods(self):
        """
        Only POST is supported (e.g. GET, PUT, DELETE are not).
        """
        util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        for view_name in ('createFirewallRule', 'deleteFirewallRule'):
            url = reverse(view_name)
            for meth in self.client.get, self.client.put, self.client.delete:
                response = meth(url)
                self.assertEqual(response.status_code,
                        status.HTTP_405_METHOD_NOT_ALLOWED)



class CanDoTests(TestCase):

    def test_create_vm_in_project(self):
        prj1 = Project.objects.create(name='prj1', email='prj1@x.com')
        prj2 = Project.objects.create(name='prj2', email='prj2@x.com')
        u1 = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertFalse(util.can_do(u1, Actions.CREATE_VM_IN_PROJECT, prj1))
        self.assertFalse(util.can_do(u1, Actions.CREATE_VM_IN_PROJECT, prj2))
        u1.projects.add(prj1)
        self.assertTrue(util.can_do(u1, Actions.CREATE_VM_IN_PROJECT, prj1))
        self.assertFalse(util.can_do(u1, Actions.CREATE_VM_IN_PROJECT, prj2))

        perm = Permission.objects.create(name=Perms.OMNIPOTENT)
        role = Role.objects.create(name='all powerful')
        role.permissions.add(perm)
        u1.roles.add(role)
        self.assertTrue(util.can_do(u1, Actions.CREATE_VM_IN_PROJECT, prj1))
        self.assertTrue(util.can_do(u1, Actions.CREATE_VM_IN_PROJECT, prj2))


class ExpirationTests(TestCase):

    def test_needs_notification(self):
        """
        Test the expiry.needs_notification function.
        """
        now = datetime.datetime.utcnow().replace(tzinfo=utc)

        # Pass ‘notif_intervals’ which is not sorted in ascending order or has
        # duplicates.
        for ints in (
                [-1, -2],
                [5, 0, 2],
                [3, 4, 4],
                ):
            with self.assertRaises(ValueError):
                expiry.needs_notification(now, None, ints)

        for exp, last_notif, ints in (
            (now, None, [-10]),
            (now-datetime.timedelta(seconds=10), None, [5]),
            (now+datetime.timedelta(seconds=10),
                now-datetime.timedelta(seconds=5), [-100, -11]),
            ):
            self.assertTrue(expiry.needs_notification(exp, last_notif, ints))

        for exp, last_notif, ints in (
            (now, None, []),
            (now+datetime.timedelta(seconds=10),
                now-datetime.timedelta(seconds=5), [-100, -3]),
            ):
            self.assertFalse(expiry.needs_notification(exp, last_notif, ints))


class ProviderTests(TestCase):
    def test_provider_choices(self):
        for k in ['aws','dummy']:
            self.assertEquals(k in Provider.choices().keys())

