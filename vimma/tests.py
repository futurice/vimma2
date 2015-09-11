import datetime
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
    Permission, Role, Project, TimeZone, Schedule,
    Provider, VMConfig, User, VM,
    Audit, PowerLog, Expiration, VMExpiration,
    FirewallRule, FirewallRuleExpiration,
)
from vimma.perms import ALL_PERMS, Perms

from dummy.models import DummyProvider, DummyVMConfig, DummyVM
from aws.models import AWSProvider, AWSVMConfig, AWSVM, AWSFirewallRule

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
        Project requires a non-empty name and email.
        """
        with self.assertRaises(ValidationError):
            obj = Project.objects.create()
            obj.delete()
        with self.assertRaises(ValidationError):
            Project.objects.create(email='a@b.com')
        with self.assertRaises(ValidationError):
            Project.objects.create(name='prj1')
        Project.objects.create(name='prj2', email='a@b.com')

    def test_project_name_unique(self):
        """
        Projects must have unique names.
        """
        Project.objects.create(name='prj', email='a@b.com')
        with self.assertRaises(ValidationError):
            Project.objects.create(name='prj', email='a@c.com')

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
            'first_name', 'last_name', 'email', 'projects', 'content_type'})

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
            'username', 'email', 'projects', 'content_type'})

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

        response = self.client.get('{}?id={}'.format(
            reverse('user-list'), u_a.id))
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


class ProviderTests(APITestCase):

    def test_requires_name_and_type(self):
        """
        Provider requires name and type fields.
        """
        for bad_prov in (
            dict(),
            ):
            with self.assertRaises(ValidationError):
                DummyProvider.objects.create(**bad_prov)
        DummyProvider.objects.create(name='My Provider')

    def test_default(self):
        """
        Test the behavior of the ‘default’ field on save().
        """
        # test the code path when the first created object is already default
        p1 = DummyProvider.objects.create(name='p1', default=True).id
        DummyProvider.objects.get(id=p1)
        self.assertIs(DummyProvider.objects.get(id=p1).default, True)
        DummyProvider.objects.get(id=p1).delete()

        # First object, auto-set as default
        p1 = DummyProvider.objects.create(name='p1').id
        DummyProvider.objects.get(id=p1)
        self.assertIs(DummyProvider.objects.get(id=p1).default, True)

        # second object, not default
        p2 = DummyProvider.objects.create(name='p2').id
        DummyProvider.objects.get(id=p2)
        self.assertIs(DummyProvider.objects.get(id=p2).default, False)

        p = DummyProvider.objects.get(id=p1)
        p.default = False
        p.save()

        # marked back as default on save
        self.assertIs(DummyProvider.objects.get(id=p1).default, True)
        self.assertEqual(DummyProvider.objects.filter(default=True).count(), 1)

        # new default object removes previous default(s)
        p3 = DummyProvider.objects.create(name='p3', default=True).id
        DummyProvider.objects.get(id=p3)
        self.assertIs(DummyProvider.objects.get(id=p3).default, True)
        self.assertEqual(DummyProvider.objects.filter(default=True).count(), 1)

        # the default flag works globally for all providers of all types
        a1 = AWSProvider.objects.create(name='a1').id
        AWSProvider.objects.get(id=a1)
        self.assertIs(DummyProvider.objects.get(id=p3).default, True)
        self.assertEqual(DummyProvider.objects.filter(default=True).count(), 1)

        a2 = AWSProvider.objects.create(name='a2', default=True).id
        AWSProvider.objects.get(id=a2)
        self.assertIs(AWSProvider.objects.get(id=a2).default, True)
        self.assertEqual(DummyProvider.objects.filter(default=True).count(), 1)

    def test_api_permissions(self):
        """
        Users can read Provider objects. The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        prov = DummyProvider.objects.create(name='My DummyProvider')

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('dummyprovider-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(len(items), 1)

        response = self.client.get(reverse('dummyprovider-detail', args=[prov.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data

        # can't modify
        item['name'] = 'Renamed'
        response = self.client.put(reverse('dummyprovider-detail',
            args=[item['id']]), item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('dummyprovider-detail',
            args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('dummyprovider-list'), item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


class DummyProviderTests(APITestCase):

    def test_api_permissions(self):
        """
        Users can read DummyProvider objects. The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        dummyProv = DummyProvider.objects.create(name='My Provider')

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('dummyprovider-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(len(items), 1)

        response = self.client.get(reverse('dummyprovider-detail',
            args=[dummyProv.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data

        # can't modify
        response = self.client.put(reverse('dummyprovider-detail',
            args=[item['id']]), item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('dummyprovider-detail',
            args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('dummyprovider-list'), item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


class AWSProviderTests(APITestCase):

    def test_provider_delete(self):
        p = AWSProvider.objects.create(name='My Prov', vpc_id='dummy')
        p.delete()

    def test_api_permissions(self):
        """
        Users can read AWSProvider objects. The API doesn't allow writing.
        """
        def checkVisibility(apiDict):
            """
            Check visible and invisible fields returned by the API.
            """
            self.assertEqual(set(apiDict.keys()),
                    {'id', 'provider', 'route_53_zone'})

        user = util.create_vimma_user('a', 'a@example.com', 'p')

        awsProv = AWSProvider.objects.create(name="My Provider", vpc_id='dummy')

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('awsprovider-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(len(items), 1)
        # checkVisibility(items[0])

        response = self.client.get(reverse('awsprovider-detail',
            args=[awsProv.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data
        # checkVisibility(item)

        # can't modify
        response = self.client.put(reverse('awsprovider-detail',
            args=[item['id']]), item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('awsprovider-detail',
            args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('awsprovider-list'), item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


class VMConfigTests(APITestCase):

    def test_required_fields(self):
        """
        VMConfig requires name, default_schedule and provider.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        p = DummyProvider.objects.create(name='My Prov')
        for bad_vm_conf in (
            dict(provider=p),
            ):
            with self.assertRaises(ValidationError):
                DummyVMConfig.objects.create(**bad_vm_conf)
        for bad_vm_conf in (
            dict(),
            dict(name='My Conf'),
            dict(default_schedule=s),
            dict(name='My Conf', default_schedule=s),
            ):
            with self.assertRaises(ObjectDoesNotExist):
                DummyVMConfig.objects.create(**bad_vm_conf)

    def test_default_value_and_protected(self):
        """
        By default, is_special = False and PROTECTED constraints.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        p = DummyProvider.objects.create(name='My Prov')
        vmc = DummyVMConfig.objects.create(name='My Conf', default_schedule=s,
                provider=p)
        self.assertIs(vmc.is_special, False)

        with self.assertRaises(ProtectedError):
            p.delete()
        with self.assertRaises(ProtectedError):
            s.delete()

        vmc.delete()
        p.delete()
        s.delete()
        tz.delete()

    def test_default(self):
        """
        Test the behavior of the ‘default’ field on save().
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        d = DummyProvider.objects.create(name='Dummy P')

        # test the code path when the first created object is already default
        d1 = DummyVMConfig.objects.create(name='d1', default_schedule=s,
                provider=d, default=True).id
        DummyVMConfig.objects.get(id=d1)
        self.assertIs(DummyVMConfig.objects.get(id=d1).default, True)
        DummyVMConfig.objects.get(id=d1).delete()

        # First object, auto-set as default
        d1 = DummyVMConfig.objects.create(name='d1', default_schedule=s,
                provider=d).id
        DummyVMConfig.objects.get(id=d1)
        self.assertIs(DummyVMConfig.objects.get(id=d1).default, True)

        # second object, not default
        d2 = DummyVMConfig.objects.create(name='d2', default_schedule=s,
                provider=d).id
        DummyVMConfig.objects.get(id=d2)
        self.assertIs(DummyVMConfig.objects.get(id=d2).default, False)

        x = DummyVMConfig.objects.get(id=d1)
        x.default = False
        x.save()

        # marked back as default on save
        self.assertIs(DummyVMConfig.objects.get(id=d1).default, True)
        self.assertEqual(DummyVMConfig.objects.filter(default=True).count(), 1)

        # new default object removes previous default(s)
        d3 = DummyVMConfig.objects.create(name='d3', default_schedule=s,
                provider=d, default=True).id
        DummyVMConfig.objects.get(id=d3)
        self.assertIs(DummyVMConfig.objects.get(id=d3).default, True)
        self.assertEqual(DummyVMConfig.objects.filter(default=True).count(), 1)

        # the default flag works per-provider instance
        a = AWSProvider.objects.create(name='AWS P')
        a1 = AWSVMConfig.objects.create(name='a1', default_schedule=s,
                provider=a).id
        AWSVMConfig.objects.get(id=a1)
        self.assertIs(DummyVMConfig.objects.get(id=d3).default, True)
        self.assertIs(AWSVMConfig.objects.get(id=a1).default, True)
        self.assertEqual(DummyVMConfig.objects.filter(default=True).count(), 1)

        a2 = DummyVMConfig.objects.create(name='a2', default_schedule=s,
                provider=d).id
        DummyVMConfig.objects.get(id=a2)
        self.assertIs(DummyVMConfig.objects.get(id=d3).default, True)
        self.assertIs(AWSVMConfig.objects.get(id=a1).default, True)
        self.assertEqual(DummyVMConfig.objects.filter(default=True).count(), 1)

        a3 = DummyVMConfig.objects.create(name='a3', default_schedule=s,
                provider=d, default=True).id
        DummyVMConfig.objects.get(id=a3)
        self.assertIs(DummyVMConfig.objects.get(id=d3).default, False)
        self.assertEqual(DummyVMConfig.objects.filter(default=True).count(), 1)

    def test_api_permissions(self):
        """
        Users can read VMConfig objects. The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        p = DummyProvider.objects.create(name='My Prov')
        vmc = DummyVMConfig.objects.create(name='My Conf', default_schedule=s,
                provider=p)

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('dummyvmconfig-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(len(items), 1)

        response = self.client.get(reverse('dummyvmconfig-detail',
            args=[vmc.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data

        # can't modify
        response = self.client.put(reverse('dummyvmconfig-detail',
            args=[item['id']]), item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('dummyvmconfig-detail',
            args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('dummyvmconfig-list'), item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


class DummyVMConfigTests(APITestCase):

    def test_required_fields(self):
        with self.assertRaises(ObjectDoesNotExist):
            DummyVMConfig.objects.create()

    def test_protected(self):
        """
        Check on_delete PROTECTED restriction.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        p = DummyProvider.objects.create(name='My Prov')
        vmc = DummyVMConfig.objects.create(name='My Conf', default_schedule=s,
                provider=p)

        vmc.delete()
        p.delete()
        s.delete()
        tz.delete()

    def test_api_permissions(self):
        """
        Users can read DummyVMConfig objects. The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        p = DummyProvider.objects.create(name='My Prov')
        config = DummyVMConfig.objects.create(name='My Conf', default_schedule=s,
                provider=p)

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('dummyvmconfig-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(len(items), 1)

        response = self.client.get(reverse('dummyvmconfig-detail',
            args=[config.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data

        # can't modify
        response = self.client.put(reverse('dummyvmconfig-detail',
            args=[item['id']]), item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('dummyvmconfig-detail',
            args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('dummyvmconfig-list'), item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


class AWSVMConfigTests(APITestCase):

    def test_required_fields(self):
        """
        AWSVMConfig requires vmconfig.
        """
        region = AWSVMConfig.regions[0]
        vol_type = AWSVMConfig.VOLUME_TYPE_CHOICES[0][0]
        with self.assertRaises(ObjectDoesNotExist):
            AWSVMConfig.objects.create(region=region, root_device_size=10,
                    root_device_volume_type=vol_type)

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        p = AWSProvider.objects.create(name='My Prov')
        AWSVMConfig.objects.create(name="My Conf", region=region, root_device_size=10,
                root_device_volume_type=vol_type, vmconfig=vmc, default_schedule=s, provider=p)

    def test_protected(self):
        """
        Check on_delete PROTECTED restriction.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        p = AWSProvider.objects.create(name='My Prov')
        vmc = AWSVMConfig.objects.create(name='My Conf', default_schedule=s,
                provider=p)
        region = AWSVMConfig.regions[0]
        vol_type = AWSVMConfig.VOLUME_TYPE_CHOICES[0][0]
        config = AWSVMConfig.objects.create(provider=p, region=region,
                root_device_size=10, root_device_volume_type=vol_type)

        config.delete()
        vmc.delete()
        p.delete()
        s.delete()
        tz.delete()

    def test_api_permissions(self):
        """
        Users can read AWSVMConfig objects. The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        p = AWSProvider.objects.create(name='My Prov')
        awsc = AWSVMConfig.objects.create(name="My Conf", provider=p, region='ap-northeast-1',
                default_schedule=s, root_device_size=10, root_device_volume_type='Magnetic')

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('awsvmconfig-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(len(items), 1)

        response = self.client.get(reverse('awsvmconfig-detail',
            args=[awsc.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data

        # can't modify
        response = self.client.put(reverse('awsvmconfig-detail',
            args=[item['id']]), item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('awsvmconfig-detail',
            args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('awsvmconfig-list'), item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


class VMTests(APITestCase):

    def test_required_fields(self):
        """
        VM requires provider, project and default_schedule.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = DummyProvider.objects.create(name='My Prov')
        config = DummyVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)
        prj = Project.objects.create(name='Prj', email='a@b.com')

        for bad_vm in (
                dict(),
                dict(schedule=s),
                dict(config=config),
                dict(schedule=s, project=prj),
            ):
            with self.assertRaises(ValidationError):
                DummyVM.objects.create(**bad_vm)

    def test_protected(self):
        """
        Test PROTECTED constraints.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = DummyProvider.objects.create(name='My Prov')
        config = DummyVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)
        prj = Project.objects.create(name='Prj', email='a@b.com')
        vm = DummyVM.objects.create(name="A", config=config, project=prj, schedule=s)

        for func in (prv.delete, prj.delete, s.delete):
            with self.assertRaises(ProtectedError):
                func()

    def test_set_null_foreign_keys(self):
        """
        Test foreign keys with on_delete=SET_NULL.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))

        prv = DummyProvider.objects.create(name='My Prov')
        cfg = DummyVMConfig.objects.create(name='My Cfg', provider=prv, default_schedule=s)

        prj = Project.objects.create(name='My Prov', email='a@b.com')

        u = util.create_vimma_user('a', 'a@example.com', 'p')
        vm = DummyVM.objects.create(name="My VM", config=cfg, project=prj, schedule=s,
                created_by=u)
        def check_creator_id(user_id):
            user = DummyVM.objects.get(id=vm.id).created_by
            if user == None:
                self.assertTrue(user_id is None)
            else:
                self.assertEqual(user_id, user.id)

        check_creator_id(u.id)
        u.delete()
        check_creator_id(None)

    def test_api_permissions(self):
        """
        Users can read VM objects in their own projects, or in all projects
        with a permission. The API doesn't allow writing.
        """
        ua = util.create_vimma_user('a', 'a@example.com', 'p')
        ub = util.create_vimma_user('b', 'b@example.com', 'p')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))

        prv = DummyProvider.objects.create(name='My Prov')
        cfg = DummyVMConfig.objects.create(name="My Config", provider=prv, default_schedule=s)
        p1 = Project.objects.create(name='Prj 1', email='p1@a.com')
        p2 = Project.objects.create(name='Prj 2', email='p2@a.com')
        p3 = Project.objects.create(name='Prj 3', email='p3@a.com')
        vm1 = DummyVM.objects.create(name="A", config=cfg, project=p1, schedule=s)
        vm2 = DummyVM.objects.create(name="B", config=cfg, project=p2, schedule=s)
        vm3 = DummyVM.objects.create(name="C", config=cfg, project=p3, schedule=s)

        ua.projects.add(p1, p2)
        ub.projects.add(p1)

        perm = Permission.objects.create(name=Perms.READ_ANY_PROJECT)
        role = Role.objects.create(name='All Seeing')
        role.permissions.add(perm)
        ub.roles.add(role)

        # user A can only see VMs in his projects
        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('dummyvm-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({vm1.id, vm2.id}, {x['id'] for x in items})

        response = self.client.get(reverse('dummyvm-detail', args=[vm1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse('dummyvm-detail', args=[vm3.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # filter by project name
        response = self.client.get(reverse('dummyvm-list') +
                '?project=' + str(p1.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({vm1.id}, {x['id'] for x in items})

        # user B can see all VMs in all projects
        self.assertTrue(self.client.login(username='b', password='p'))
        response = self.client.get(reverse('dummyvm-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({vm1.id, vm2.id, vm3.id}, {x['id'] for x in items})

        for vm_id in (vm1.id, vm3.id):
            response = self.client.get(reverse('dummyvm-detail', args=[vm_id]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            item = response.data


        # can't modify
        response = self.client.put(reverse('dummyvm-detail', args=[item['id']]),
                item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('dummyvm-detail', args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('dummyvm-list'), item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


class DummyVMTests(APITestCase):

    def test_required_fields(self):
        """
        DummyVM requires vm.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = DummyProvider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = DummyVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = DummyVM.objects.create(config=config, project=prj, schedule=s)

        # with self.assertRaises(ValidationError):
        DummyVM(name='dummy')

    def test_protected(self):
        """
        Test PROTECTED constraint.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = DummyProvider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = DummyVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = DummyVM.objects.create(config=config, project=prj, schedule=s)

        vm.delete()
        prv.delete()
        prj.delete()
        s.delete()
        tz.delete()

    def test_api_permissions(self):
        """
        Users can read DummyVM objects in their own projects, or in all
        projects with a permission. The API doesn't allow writing.
        """
        ua = util.create_vimma_user('a', 'a@example.com', 'p')
        ub = util.create_vimma_user('b', 'b@example.com', 'p')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))

        prv = DummyProvider.objects.create(name='My Prov')

        config = DummyVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)

        p1 = Project.objects.create(name='Prj 1', email='p1@a.com')
        p2 = Project.objects.create(name='Prj 2', email='p2@a.com')
        p3 = Project.objects.create(name='Prj 3', email='p3@a.com')

        dvm1 = DummyVM.objects.create(config=config, project=p1, schedule=s, name="dummy 1")
        dvm2 = DummyVM.objects.create(config=config, project=p2, schedule=s, name="dummy 2")
        dvm3 = DummyVM.objects.create(config=config, project=p3, schedule=s, name="dummy 3")

        ua.projects.add(p1, p2)
        ub.projects.add(p1)

        perm = Permission.objects.create(name=Perms.READ_ANY_PROJECT)
        role = Role.objects.create(name='All Seeing')
        role.permissions.add(perm)
        ub.roles.add(role)

        # user A can only see DummyVMs in his projects
        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('dummyvm-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({dvm1.id, dvm2.id}, {x['id'] for x in items})

        response = self.client.get(reverse('dummyvm-detail', args=[dvm1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse('dummyvm-detail', args=[dvm3.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # filter by .vm field
        response = self.client.get(reverse('dummyvm-list') +
                '?vm=' + str(dvm1.vm.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({dvm1.id}, {x['id'] for x in items})

        # user B can see all DummyVMs in all projects
        self.assertTrue(self.client.login(username='b', password='p'))
        response = self.client.get(reverse('dummyvm-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({dvm1.id, dvm2.id, dvm3.id}, {x['id'] for x in items})

        for dvm_id in (dvm1.id, dvm3.id):
            response = self.client.get(reverse('dummyvm-detail', args=[dvm_id]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            item = response.data


        # can't modify
        response = self.client.put(reverse('dummyvm-detail', args=[item['id']]),
                item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('dummyvm-detail',
            args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('dummyvm-list'),
                item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


class AWSVMTests(APITestCase):

    def test_required_fields(self):
        """
        AWSVM requires: vm, name, region.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = AWSProvider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = AWSVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = AWSVM.objects.create(config=config, project=prj, schedule=s)

        for kwargs in ({'vm': vm}, {'name': 'a'}, {'region': 'a'},
                {'vm': vm, 'name': 'a'}, {'vm': vm, 'region': 'a'},
                {'name': 'a', 'region': 'a'}):
            with self.assertRaises(ValidationError):
                AWSVM(**kwargs)

        AWSVM.objects.create(name='a', region='a')

    def test_name_validator(self):
        """
        AWSVM name must conform to a certain format (used in DNS name).
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = AWSProvider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = AWSVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)

        vm = AWSVM.objects.create(config=config, project=prj, schedule=s)
        for name in ('', ' ', '-', '-a', 'a-', '.', 'dev.vm'):
            with self.assertRaises(ValidationError):
                AWSVM.objects.create(config=config, region='a', name=name)
        vm.delete()

        for name in ('a', '5', 'a-b', 'build-server', 'x-0-dev'):
            AWSVM.objects.create(config=config, project=prj, schedule=s, name=name)

    def test_protected(self):
        """
        Test PROTECTED constraint.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = AWSProvider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = AWSVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = AWSVM.objects.create(config=config, project=prj, schedule=s)

    def test_ip_address(self):
        """
        Test the IP address default, check that it can't be None.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = AWSProvider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = AWSVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)

        vm = AWSVM.objects.create(config=config, project=prj, schedule=s)
        self.assertEqual(awsvm.ip_address, '')

        vm = AWSVM.objects.create(config=config, project=prj, schedule=s, name='ip', region='a', ip_address='192.168.0.1')
        with self.assertRaises(IntegrityError):
            AWSVM.objects.create(vm=vm, name='ip', region='a',
                    ip_address=None)

    def test_api_permissions(self):
        """
        Users can read AWSVM objects in their own projects, or in all
        projects with a permission. The API doesn't allow writing.
        """
        ua = util.create_vimma_user('a', 'a@example.com', 'p')
        ub = util.create_vimma_user('b', 'b@example.com', 'p')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))

        prv = AWSProvider.objects.create(name='My Provider')
        p1 = Project.objects.create(name='Prj 1', email='p1@a.com')
        p2 = Project.objects.create(name='Prj 2', email='p2@a.com')
        p3 = Project.objects.create(name='Prj 3', email='p3@a.com')

        config = AWSVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)

        avm1 = AWSVM.objects.create(name='1', region='a', config=config, project=p1, schedule=s)
        avm2 = AWSVM.objects.create(name='2', region='b', config=config, project=p2, schedule=s)
        avm3 = AWSVM.objects.create(name='3', region='c', config=config, project=p3, schedule=s)

        ua.projects.add(p1, p2)
        ub.projects.add(p1)

        perm = Permission.objects.create(name=Perms.READ_ANY_PROJECT)
        role = Role.objects.create(name='All Seeing')
        role.permissions.add(perm)
        ub.roles.add(role)

        # user A can only see AWSVMs in his projects
        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('awsvm-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({avm1.id, avm2.id}, {x['id'] for x in items})

        response = self.client.get(reverse('awsvm-detail', args=[avm1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse('awsvm-detail', args=[avm3.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # filter by .vm field
        response = self.client.get(reverse('awsvm-list') +
                '?vm=' + str(avm1.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({avm1.id}, {x['id'] for x in items})

        # filter by .name field
        # TODO: escape query param value
        response = self.client.get(reverse('awsvm-list') +
                '?name=' + avm1.name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({avm1.id}, {x['id'] for x in items})

        # user B can see all AWSVMs in all projects
        self.assertTrue(self.client.login(username='b', password='p'))
        response = self.client.get(reverse('awsvm-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({avm1.id, avm2.id, avm3.id}, {x['id'] for x in items})

        for avm_id in (avm1.id, avm3.id):
            response = self.client.get(reverse('awsvm-detail', args=[avm_id]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            item = response.data


        # can't modify
        response = self.client.put(reverse('awsvm-detail', args=[item['id']]),
                item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('awsvm-detail',
            args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('awsvm-list'),
                item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


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

    def test_create_perms_and_not_found(self):
        """
        Test user permissions when creating a VM, or requested data not found.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prov = DummyProvider.objects.create(name='My Provider')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))

        vmc = DummyVMConfig.objects.create(name='My Conf', default_schedule=s,
                provider=prov)

        url = reverse('createVM')
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({
                    'project': prj.id,
                    'vmconfig': vmc.id,
                    'schedule': s.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        u.projects.add(prj)
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({
                    'project': prj.id,
                    'vmconfig': vmc.id,
                    'schedule': s.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # non-existent object IDs
        for data in ({'project': 100, 'vmconfig': vmc.id, 'schedule': s.id},
                {'project': prj.id, 'vmconfig': 100, 'schedule': s.id},
                {'project': prj.id, 'vmconfig': vmc.id, 'schedule': 100}):
            response = self.client.post(url, content_type='application/json',
                    data=json.dumps(data))
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # can create VM in own project
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({
                    'project': prj.id,
                    'vmconfig': vmc.id,
                    'schedule': s.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # can't use special schedule
        s2 = Schedule.objects.create(name='s2', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]), is_special=True)
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({
                    'project': prj.id,
                    'vmconfig': vmc.id,
                    'schedule': s2.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # can use special schedule if it's the vm config's default
        vmc.default_schedule=s2
        vmc.save()
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({
                    'project': prj.id,
                    'vmconfig': vmc.id,
                    'schedule': s2.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # can use special schedule if the user has permission
        vmc.default_schedule=s
        vmc.save()
        perm = Permission.objects.create(name=Perms.USE_SPECIAL_SCHEDULE)
        role = Role.objects.create(name='SpecSched Role')
        role.permissions.add(perm)
        u.roles.add(role)
        s3 = Schedule.objects.create(name='s3', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]), is_special=True)
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({
                    'project': prj.id,
                    'vmconfig': vmc.id,
                    'schedule': s3.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # can't use special vmconfig
        vmc.is_special = True
        vmc.save()
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({
                    'project': prj.id,
                    'vmconfig': vmc.id,
                    'schedule': s.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # can use special vmconfig if the user has permission
        perm = Permission.objects.create(name=Perms.USE_SPECIAL_VM_CONFIG)
        role = Role.objects.create(name='SpecVmConfig Role')
        role.permissions.add(perm)
        u.roles.add(role)
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({
                    'project': prj.id,
                    'vmconfig': vmc.id,
                    'schedule': s.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # can't use special provider
        prov2 = DummyProvider.objects.create(name='My Special Provider', is_special=True)
        vmc2 = DummyVMConfig.objects.create(name='My Conf 2', default_schedule=s,
                provider=prov2)
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({
                    'project': prj.id,
                    'vmconfig': vmc2.id,
                    'schedule': s.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # can use special provider if the user has permission
        perm = Permission.objects.create(name=Perms.USE_SPECIAL_PROVIDER)
        role = Role.objects.create(name='Special Provider Role')
        role.permissions.add(perm)
        u.roles.add(role)
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({
                    'project': prj.id,
                    'vmconfig': vmc2.id,
                    'schedule': s.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_powerOnOffRebootDestroy_perms_and_not_found(self):
        """
        Test user permissions & ‘not found’ for the above VM operations.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prov = DummyProvider.objects.create(name='My Provider')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))
        config = DummyVMConfig.objects.create(name='My Conf 2', default_schedule=s,
                provider=prov)

        vm = DummyVM.objects.create(config=config, project=prj, schedule=s, name="dummy")

        url_names = ('powerOnVM', 'powerOffVM', 'rebootVM', 'destroyVM')

        # non-existent VM ID
        for url in map(reverse, url_names):
            response = self.client.post(url, content_type='application/json',
                    data=json.dumps({'vmid': 100}))
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # can perform the actions in own project
        u.projects.add(prj)
        for url in map(reverse, url_names):
            response = self.client.post(url, content_type='application/json',
                    data=json.dumps({'vmid': vm.id}))
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # forbidden outside own projects
        u.projects.remove(prj)
        for url in map(reverse, url_names):
            response = self.client.post(url, content_type='application/json',
                    data=json.dumps({'vmid': vm.id}))
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # ok if omnipotent
        perm = Permission.objects.create(name=Perms.OMNIPOTENT)
        role = Role.objects.create(name='all powerful')
        role.permissions.add(perm)
        u.roles.add(role)
        for url in map(reverse, url_names):
            response = self.client.post(url, content_type='application/json',
                    data=json.dumps({'vmid': vm.id}))
            self.assertEqual(response.status_code, status.HTTP_200_OK)


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

    def test_perms_and_not_found(self):
        """
        Test user permissions and ‘not found’.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prov = DummyProvider.objects.create(name='My Provider', max_override_seconds=3600)

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))
        config = DummyVMConfig.objects.create(name='My Config', default_schedule=s, provider=prov)

        vm = DummyVM.objects.create(config=config, project=prj, schedule=s)

        url = reverse('overrideSchedule')

        # non-existent VM ID
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'vmid': 100, 'state': None}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # can override schedules in own project
        u.projects.add(prj)
        for data in ({'state': None}, {'state': True, 'seconds': 3600},
                {'state': False, 'seconds': 600}):
            data.update({'vmid': vm.id})
            response = self.client.post(url, content_type='application/json',
                    data=json.dumps(data))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        # but not exceeding max seconds
        response = self.client.post(url, content_type='application/json',
            data=json.dumps({'vmid': vm.id, 'state': True, 'seconds': 3601}))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # forbidden outside own projects
        u.projects.remove(prj)
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'vmid': vm.id, 'state': None}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # ok if omnipotent
        perm = Permission.objects.create(name=Perms.OMNIPOTENT)
        role = Role.objects.create(name='all powerful')
        role.permissions.add(perm)
        u.roles.add(role)
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'vmid': vm.id, 'state': None}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_vm_at_now(self):
        """
        Test the util.vm_at_now helper.
        """
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prov = DummyProvider.objects.create(name='My Provider', max_override_seconds=3600)

        tz = TimeZone.objects.create(name='Pacific/Easter')
        s_off = Schedule.objects.create(name='Always OFF', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))
        s_on = Schedule.objects.create(name='Always On', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))

        config = DummyVMConfig.objects.create(name='My Config', default_schedule=s_on, provider=prov)

        vm = DummyVM.objects.create(config=config, project=prj, schedule=s_off)

        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        expire_dt = now + datetime.timedelta(minutes=1)
        exp = VMExpiration.objects.create(vm=vm, expires_at=expire_dt)
        del now

        def check_overrides():
            old_state = vm.sched_override_state
            old_tstamp = vm.sched_override_tstamp
            old_vm_at_now = util.vm_at_now(vm.id)

            now = datetime.datetime.utcnow().replace(tzinfo=utc)
            # if the override expired already, it has no effect
            end = now + datetime.timedelta(minutes=-1)
            vm.sched_override_tstamp = end.timestamp()
            vm.save()

            for new_state in (True, False):
                vm.sched_override_state = new_state
                vm.save()
                self.assertIs(util.vm_at_now(vm.id), old_vm_at_now)

            # if the override hasn't expired yet, it's used
            end = now + datetime.timedelta(minutes=1)
            vm.sched_override_tstamp = end.timestamp()
            vm.save()

            for new_state in (True, False):
                vm.sched_override_state = new_state
                vm.save()
                self.assertIs(util.vm_at_now(vm.id), new_state)

            vm.sched_override_state = old_state
            vm.sched_override_tstamp = old_tstamp
            vm.save()

        self.assertFalse(util.vm_at_now(vm.id))
        check_overrides()

        vm.schedule = s_on
        vm.save()
        self.assertTrue(util.vm_at_now(vm.id))
        check_overrides()

        # if the VM has expired, it's OFF, regardles of schedule and overrides

        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        expire_dt = now - datetime.timedelta(minutes=1)
        exp.expires_at = expire_dt
        exp.save()
        self.assertFalse(util.vm_at_now(vm.id))

        end = now + datetime.timedelta(minutes=1)
        vm.sched_override_tstamp = end.timestamp()
        vm.sched_override_state = True
        vm.save()
        self.assertFalse(util.vm_at_now(vm.id))


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

    def test_perms_and_not_found(self):
        """
        Test user permissions and ‘not found’.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prov = DummyProvider.objects.create(name='My Provider')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s1 = Schedule.objects.create(name='s1', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))
        s2 = Schedule.objects.create(name='s2', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))
        s3 = Schedule.objects.create(name='s3', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]), is_special=True)
        config = DummyVMConfig.objects.create(name='My Config', default_schedule=s1, provider=prov)

        vm = DummyVM.objects.create(config=config, project=prj, schedule=s1)

        url = reverse('changeVMSchedule')

        def checkScheduleId(vm_id, schedule_id):
            """
            Check that vm_id has schedule_id.
            """
            self.assertEqual(VM.objects.get(id=vm_id).schedule.id, schedule_id)

        # non-existent VM ID or Schedule ID
        for data in (
                {'vmid': -100, 'scheduleid': s2.id},
                {'vmid': vm.id, 'scheduleid': -100},
                ):
            response = self.client.post(url, content_type='application/json',
                    data=json.dumps(data))
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        checkScheduleId(vm.id, s1.id)

        # can't change schedules outside own projects
        response = self.client.post(url, content_type='application/json',
            data=json.dumps({'vmid': vm.id, 'scheduleid': s2.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        checkScheduleId(vm.id, s1.id)
        # ok in own projects
        u.projects.add(prj)
        response = self.client.post(url, content_type='application/json',
            data=json.dumps({'vmid': vm.id, 'scheduleid': s2.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        checkScheduleId(vm.id, s2.id)

        # can't change to ‘special’ schedule
        response = self.client.post(url, content_type='application/json',
            data=json.dumps({'vmid': vm.id, 'scheduleid': s3.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        checkScheduleId(vm.id, s2.id)

        # ok if user has the required permission
        perm = Permission.objects.create(name=Perms.USE_SPECIAL_SCHEDULE)
        role = Role.objects.create(name='users of special schedules')
        role.permissions.add(perm)
        u.roles.add(role)
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'vmid': vm.id, 'scheduleid': s3.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        checkScheduleId(vm.id, s3.id)


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

    def test_VM_perms_and_not_found(self):
        """
        Test user permissions and ‘not found’ for VM Expirations.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prv = DummyProvider.objects.create(name='My Provider')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))

        config = DummyVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = DummyVM.objects.create(name="My VM", config=config, project=prj, schedule=s)

        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        now_ts = int(now.timestamp())
        future_ts = int((now + datetime.timedelta(hours=1)).timestamp())
        future2_ts = int((now + datetime.timedelta(hours=2)).timestamp())
        past_ts = int((now - datetime.timedelta(hours=1)).timestamp())
        exp = VMExpiration.objects.create(expires_at=now, vm=vm)

        url = reverse('setExpiration')

        def checkExpiration(exp_id, timestamp):
            """
            Check that exp_id expires at timestamp.
            """
            self.assertEqual(
                int(VMExpiration.objects.get(id=exp_id).expires_at.timestamp()),
                timestamp)

        checkExpiration(exp.id, now_ts)

        # non-existent Expiration ID
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'id': -100, 'timestamp': future_ts}))
        self.assertEqual(response.status_code,
                status.HTTP_404_NOT_FOUND)
        checkExpiration(exp.id, now_ts)

        # can't change vm expiration outside own projects
        response = self.client.post(url, content_type='application/json',
            data=json.dumps({'id': exp.id, 'timestamp': future_ts}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        checkExpiration(exp.id, now_ts)

        # ok in own projects
        u.projects.add(prj)
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'id': exp.id, 'timestamp': future_ts}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        checkExpiration(exp.id, future_ts)

        # can't set in the past
        response = self.client.post(url, content_type='application/json',
            data=json.dumps({'id': exp.id, 'timestamp': past_ts}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        checkExpiration(exp.id, future_ts)

        # also ok if user has the required permission
        u.projects.remove(prj)
        perm = Permission.objects.create(name=Perms.OMNIPOTENT)
        role = Role.objects.create(name='your God')
        role.permissions.add(perm)
        u.roles.add(role)
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'id': exp.id, 'timestamp': future2_ts}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        checkExpiration(exp.id, future2_ts)

        # superuser can set beyond a certain limit
        superuser_ts = int((now + datetime.timedelta(
            seconds=settings.DEFAULT_VM_EXPIRY_SECS+65)).timestamp())
        response = self.client.post(url, content_type='application/json',
            data=json.dumps({'id': exp.id, 'timestamp': superuser_ts}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        checkExpiration(exp.id, superuser_ts)

        # can't set beyond a certain limit
        u.roles.remove(role)
        bad_ts = int((now + datetime.timedelta(
            seconds=settings.DEFAULT_VM_EXPIRY_SECS+60)).timestamp())
        response = self.client.post(url, content_type='application/json',
            data=json.dumps({'id': exp.id, 'timestamp': bad_ts}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        checkExpiration(exp.id, superuser_ts)

    def test_FirewallRule_perms_and_not_found(self):
        """
        Test user permissions and ‘not found’ for FirewallRule Expirations.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prv = AWSProvider.objects.create(name='My Provider', vpc_id='dummy')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))
        config = AWSVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)

        vm = AWSVM.objects.create(name="my-vm", config=config, project=prj, schedule=s)
        fw_rule = FirewallRule.objects.create(vm=vm)
        AWSFirewallRule.objects.create(firewallrule=fw_rule,
                ip_protocol=AWSFirewallRule.PROTO_TCP,
                from_port=80, to_port=80, cidr_ip='1.2.3.4/32')

        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        now_ts = int(now.timestamp())
        future_ts = int((now + datetime.timedelta(hours=1)).timestamp())
        future2_ts = int((now + datetime.timedelta(hours=2)).timestamp())
        past_ts = int((now - datetime.timedelta(hours=1)).timestamp())
        exp = FirewallRuleExpiration.objects.create(expires_at=now,
                firewallrule=fw_rule)

        url = reverse('setExpiration')

        def checkExpiration(exp_id, timestamp):
            """
            Check that exp_id expires at timestamp.
            """
            self.assertEqual(
                int(FirewallRuleExpiration.objects.get(id=exp_id).expires_at.timestamp()),
                timestamp)

        checkExpiration(exp.id, now_ts)

        # non-existent Expiration ID
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'id': -100, 'timestamp': future_ts}))
        self.assertEqual(response.status_code,
                status.HTTP_404_NOT_FOUND)
        checkExpiration(exp.id, now_ts)

        # can't change vm expiration outside own projects
        response = self.client.post(url, content_type='application/json',
            data=json.dumps({'id': exp.id, 'timestamp': future_ts}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        checkExpiration(exp.id, now_ts)

        # ok in own projects
        u.projects.add(prj)
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'id': exp.id, 'timestamp': future_ts}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        checkExpiration(exp.id, future_ts)

        # can't set in the past
        response = self.client.post(url, content_type='application/json',
            data=json.dumps({'id': exp.id, 'timestamp': past_ts}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        checkExpiration(exp.id, future_ts)

        # also ok if user has the required permission
        u.projects.remove(prj)
        perm = Permission.objects.create(name=Perms.OMNIPOTENT)
        role = Role.objects.create(name='your God')
        role.permissions.add(perm)
        u.roles.add(role)
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({'id': exp.id, 'timestamp': future2_ts}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        checkExpiration(exp.id, future2_ts)

        # superuser can set beyond a certain limit
        max_secs = max(settings.NORMAL_FIREWALL_RULE_EXPIRY_SECS,
                settings.SPECIAL_FIREWALL_RULE_EXPIRY_SECS)
        superuser_ts = int((now + datetime.timedelta(
            seconds=max_secs+65*60)).timestamp())
        response = self.client.post(url, content_type='application/json',
            data=json.dumps({'id': exp.id, 'timestamp': superuser_ts}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        checkExpiration(exp.id, superuser_ts)

        # can't set beyond a certain limit
        u.roles.remove(role)
        max_secs = max(settings.NORMAL_FIREWALL_RULE_EXPIRY_SECS,
                settings.SPECIAL_FIREWALL_RULE_EXPIRY_SECS)
        bad_ts = int((now + datetime.timedelta(
            seconds=max_secs+60*60)).timestamp())
        response = self.client.post(url, content_type='application/json',
            data=json.dumps({'id': exp.id, 'timestamp': bad_ts}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        checkExpiration(exp.id, superuser_ts)


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

    def test_perms_and_not_found(self):
        """
        Test user permissions and ‘not found’ (for VMs when creating,
        for rules when deleting).
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prv = AWSProvider.objects.create(name='My Provider', vpc_id='dummy')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))

        config = AWSVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = AWSVM.objects.create(config=config, project=prj, schedule=s)

        create_url, delete_url = map(reverse,
                ('createFirewallRule', 'deleteFirewallRule'))

        # non-existent vm ID (create) or firewall rule id (delete)
        response = self.client.post(create_url,
                content_type='application/json',
                data=json.dumps({'vmid': -100, 'data': None}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.post(delete_url,
                content_type='application/json', data=json.dumps({'id': -100}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # can't change firewall rules outside own projects
        response = self.client.post(create_url,
                content_type='application/json',
                data=json.dumps({'vmid': vm.id, 'data': None}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        fw_rule = FirewallRule.objects.create()
        vm.firewallrules.add(fw_rule)

        response = self.client.post(delete_url,
                content_type='application/json',
                data=json.dumps({'id': fw_rule.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # ok in own projects
        u.projects.add(prj)
        response = self.client.post(create_url,
                content_type='application/json',
                data=json.dumps({'vmid': vm.id, 'data': None}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(delete_url,
                content_type='application/json',
                data=json.dumps({'id': fw_rule.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # also ok if user has the required permission
        u.projects.remove(prj)
        perm = Permission.objects.create(name=Perms.OMNIPOTENT)
        role = Role.objects.create(name='all powerful')
        role.permissions.add(perm)
        u.roles.add(role)

        u.projects.add(prj)
        response = self.client.post(create_url,
                content_type='application/json',
                data=json.dumps({'vmid': vm.id, 'data': None}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(delete_url,
                content_type='application/json',
                data=json.dumps({'id': fw_rule.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


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


class AuditTests(TestCase):

    def test_required_fields(self):
        """
        Test required fields: level, text.
        """
        Audit.objects.create(level=Audit.DEBUG, text='hello')
        with self.assertRaises(ValidationError):
            Audit.objects.create()
        with self.assertRaises(ValidationError):
            Audit.objects.create(level=Audit.DEBUG)
        with self.assertRaises(ValidationError):
            Audit.objects.create(text='hello')

    def test_on_delete_constraints(self):
        """
        Test on_delete constraints for user and vm fields.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = DummyProvider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = DummyVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)

        vm = DummyVM.objects.create(config=config, project=prj, schedule=s)

        a = Audit.objects.create(level=Audit.INFO, text='hi',
                user=u, vm=vm)
        a_id = a.id
        del a

        u.delete()
        self.assertEqual(Audit.objects.get(id=a_id).user, None)
        vm.delete()
        self.assertEqual(Audit.objects.get(id=a_id).vm, None)

    def test_text_length(self):
        """
        Test that 0 < text length ≤ max_length.
        """
        with self.assertRaises(ValidationError):
            Audit.objects.create(level=Audit.DEBUG, text='')

        Audit.objects.create(level=Audit.DEBUG, text='a')
        Audit.objects.create(level=Audit.DEBUG,
                text='a'*Audit.TEXT_MAX_LENGTH)

        # SQLite3 raises ValidationError, PostgreSQL raises DataError
        with self.assertRaises((ValidationError, DataError)):
            Audit.objects.create(level=Audit.DEBUG,
                    text='a'*(Audit.TEXT_MAX_LENGTH+1))


    def test_timestamp(self):
        """
        Test that timestamp is the time of creation.
        """
        a = Audit.objects.create(level=Audit.DEBUG, text='a')
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        delta = now - a.timestamp
        self.assertTrue(delta <= datetime.timedelta(minutes=1))


    def test_api_permissions(self):
        """
        Users can read Audit objects if they are in the ‘user’ field or a VM
        in one of their projects is in the ‘vm’ field.
        The API is read-only.
        """
        uF = util.create_vimma_user('Fry', 'fry@pe.com', '-')
        uH = util.create_vimma_user('Hubert', 'hubert@pe.com', '-')
        uB = util.create_vimma_user('Bender', 'bender@pe.com', '-')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))

        prv = DummyProvider.objects.create(name='My Prov')
        pD = Project.objects.create(name='Prj Delivery', email='p-d@pe.com')
        pS = Project.objects.create(name='Prj Smelloscope', email='p-s@pe.com')
        config = DummyVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)

        vmD = DummyVM.objects.create(config=config, project=pD, schedule=s)
        vmS = DummyVM.objects.create(config=config, project=pS, schedule=s)

        uF.projects.add(pD)
        uH.projects.add(pD, pS)

        perm = Permission.objects.create(name=Perms.READ_ALL_AUDITS)
        role = Role.objects.create(name='All Seeing')
        role.permissions.add(perm)
        uB.roles.add(role)

        Audit.objects.create(level=Audit.INFO, vm=vmD, user=None,
                text='vmd-')
        Audit.objects.create(level=Audit.INFO, vm=None, user=uF,
                text='-fry')
        Audit.objects.create(level=Audit.INFO, vm=vmS, user=uF,
                text='vms-fry')
        Audit.objects.create(level=Audit.INFO, vm=vmS, user=None,
                text='vms-')
        Audit.objects.create(level=Audit.INFO, vm=None, user=None,
                text='-')

        def check_user_sees(username, text_set):
            """
            Check that username sees all audits in text_set and nothing else.
            """
            self.assertTrue(self.client.login(username=username, password='-'))
            response = self.client.get(reverse('audit-list'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            items = response.data['results']
            self.assertEqual({x['text'] for x in items}, text_set)

        check_user_sees('Fry', {'vmd-', '-fry', 'vms-fry'})
        check_user_sees('Hubert', {'vmd-', 'vms-fry', 'vms-'})
        check_user_sees('Bender', {'vmd-', '-fry', 'vms-fry', 'vms-', '-'})

        # Test Filtering

        # filter by .vm field
        self.assertTrue(self.client.login(username='Fry', password='-'))
        response = self.client.get(reverse('audit-list') + '?vm=' + str(vmS.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({x['text'] for x in items}, {'vms-fry'})

        # filter by .user field
        self.assertTrue(self.client.login(username='Bender', password='-'))
        response = self.client.get(reverse('audit-list') +
                '?user=' + str(uF.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({x['text'] for x in items}, {'-fry', 'vms-fry'})

        # test write operations

        self.assertTrue(self.client.login(username='Fry', password='-'))
        a_id = Audit.objects.filter(vm=vmS, user=uF)[0].id
        response = self.client.get(reverse('audit-detail', args=[a_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data

        # can't modify
        response = self.client.put(reverse('audit-detail', args=[a_id]),
                item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('audit-detail', args=[a_id]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('audit-list'), item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_min_level(self):
        """
        Check the min_level API filter.
        """
        u = util.create_vimma_user('user', 'user@example.com', '-')

        Audit.objects.create(level=Audit.DEBUG, user=u, text='-d')
        Audit.objects.create(level=Audit.WARNING, user=u,
                text='-w')
        Audit.objects.create(level=Audit.ERROR, user=u, text='-e')

        def check_results(min_level, text_set):
            """
            Check that username sees all audits in text_set and nothing else.
            """
            self.assertTrue(self.client.login(username=u.username,
                password='-'))
            response = self.client.get(reverse('audit-list'),
                    {'min_level': min_level})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            items = response.data['results']
            self.assertEqual({x['text'] for x in items}, text_set)

        def check_filtering():
            check_results(Audit.DEBUG, {'-d', '-w', '-e'})
            check_results(Audit.WARNING, {'-w', '-e'})
            check_results(Audit.ERROR, {'-e'})

        check_filtering()

        # regression: filtering by min_level not working for omnipotent user
        perm_omni = Permission.objects.create(name=Perms.OMNIPOTENT)
        omni_role = Role.objects.create(name='Omni Role')
        omni_role.permissions.add(perm_omni)
        u.roles.add(omni_role)
        check_filtering()


class PowerLogTests(TestCase):

    def test_required_fields(self):
        """
        Test required fields: vm, powered_on.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = DummyProvider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = DummyVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = DummyVM.objects.create(name="My-VM", config=config, project=prj, schedule=s)

        for kw in ({}, {'vm': vm}, {'powered_on': True}):
            with transaction.atomic():
                with self.assertRaises(IntegrityError):
                    PowerLog.objects.create(**kw)
        PowerLog.objects.create(vm=vm, powered_on=True)

    def test_on_delete_constraints(self):
        """
        Test on_delete constraints for vm field.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = DummyProvider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = DummyVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = DummyVM.objects.create(config=config, project=prj, schedule=s)

        pl = PowerLog.objects.create(vm=vm, powered_on=False)
        pl_id = pl.id
        del pl
        vm.delete()

        with self.assertRaises(ObjectDoesNotExist):
            PowerLog.objects.get(id=pl_id)

    def test_api_permissions(self):
        """
        Users can read PowerLog objects if the VM is in one of their projects.
        The API is read-only.
        """
        uF = util.create_vimma_user('Fry', 'fry@pe.com', '-')
        uH = util.create_vimma_user('Hubert', 'hubert@pe.com', '-')
        uB = util.create_vimma_user('Bender', 'bender@pe.com', '-')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))

        prv = DummyProvider.objects.create(name='My Prov')
        pD = Project.objects.create(name='Prj Delivery', email='p-d@pe.com')
        pS = Project.objects.create(name='Prj Smelloscope', email='p-s@pe.com')
        config = DummyVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)

        vmD = DummyVM.objects.create(config=config, project=pD, schedule=s)
        vmS = DummyVM.objects.create(config=config, project=pS, schedule=s)

        uF.projects.add(pD)
        uH.projects.add(pD, pS)

        perm = Permission.objects.create(name=Perms.READ_ALL_POWER_LOGS)
        role = Role.objects.create(name='All Seeing')
        role.permissions.add(perm)
        uB.roles.add(role)

        plD1 = PowerLog.objects.create(vm=vmD, powered_on=True)
        plD2 = PowerLog.objects.create(vm=vmD, powered_on=True)
        plS1 = PowerLog.objects.create(vm=vmS, powered_on=False)
        plS2 = PowerLog.objects.create(vm=vmS, powered_on=True)

        def check_user_sees(username, powerlog_id_set):
            """
            Check that username sees all powerlogs in the set and nothing else.
            """
            self.assertTrue(self.client.login(username=username, password='-'))
            response = self.client.get(reverse('powerlog-list'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            items = response.data['results']
            self.assertEqual({x['id'] for x in items}, powerlog_id_set)

        check_user_sees('Fry', {plD1.id, plD2.id})
        check_user_sees('Hubert', {plD1.id, plD2.id, plS1.id, plS2.id})
        check_user_sees('Bender', {plD1.id, plD2.id, plS1.id, plS2.id})

        # Test Filtering

        # filter by .vm field
        self.assertTrue(self.client.login(username='Fry', password='-'))
        response = self.client.get(reverse('powerlog-list') +
                '?vm=' + str(vmS.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({x['id'] for x in items}, set())

        self.assertTrue(self.client.login(username='Hubert', password='-'))
        response = self.client.get(reverse('powerlog-list') +
                '?vm=' + str(vmS.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({x['id'] for x in items}, {plS1.id, plS2.id})

        # test write operations

        self.assertTrue(self.client.login(username='Fry', password='-'))
        response = self.client.get(reverse('powerlog-detail', args=[plD1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data

        # can't modify
        response = self.client.put(reverse('powerlog-detail', args=[plD1.id]),
                item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('powerlog-detail',
            args=[plD1.id]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('powerlog-list'), item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


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

    def test_api_permissions_vm(self):
        """
        Users can read Expiration and VMExpiration objects
        for the vms in one of their projects.

        The API is read-only.
        """
        uF = util.create_vimma_user('Fry', 'fry@pe.com', '-')
        uH = util.create_vimma_user('Hubert', 'hubert@pe.com', '-')
        uB = util.create_vimma_user('Bender', 'bender@pe.com', '-')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))

        prv = AWSProvider.objects.create(name='My Prov')
        config = AWSVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)

        pD = Project.objects.create(name='Prj Delivery', email='p-d@pe.com')
        pS = Project.objects.create(name='Prj Smelloscope', email='p-s@pe.com')

        vmD = AWSVM.objects.create(config=config, project=pD, schedule=s)

        vmD = AWSVM.objects.create(config=config, project=pD, schedule=s)
        vmS = AWSVM.objects.create(config=config, project=pS, schedule=s)

        uF.projects.add(pD)
        uH.projects.add(pD, pS)

        perm = Permission.objects.create(name=Perms.READ_ANY_PROJECT)
        role = Role.objects.create(name='All Seeing')
        role.permissions.add(perm)
        uB.roles.add(role)

        now = datetime.datetime.utcnow().replace(tzinfo=utc)

        vm_expD = VMExpiration.objects.create(expires_at=now, vm=vmD)
        vm_expS = VMExpiration.objects.create(expires_at=now, vm=vmS)

        fw_rule_D = AWSFirewallRule.objects.create()
        vmD.firewallrules.add(fw_rule_D)
        fw_rule_S = AWSFirewallRule.objects.create()
        vmS.firewallrules.add(fw_rule_S)

        fw_expD = FirewallRuleExpiration.objects.create(
                expires_at=now, firewallrule=fw_rule_D)
        fw_expS = FirewallRuleExpiration.objects.create(
                expires_at=now, firewallrule=fw_rule_S)

        def check_user_sees(username, vm_exp_id_set, fw_rule_exp_id_set):
            """
            Check that username sees all expirations, vm expirations
            and firewall rule expirations in the sets and nothing else.
            """
            self.assertTrue(self.client.login(username=username, password='-'))
            for (view_name, id_set) in (
                    ('vmexpiration-list', vm_exp_id_set),
                    ('firewallruleexpiration-list', fw_rule_exp_id_set),
                    ):
                response = self.client.get(reverse(view_name))
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                items = response.data['results']
                self.assertEqual({x['id'] for x in items}, id_set)

        check_user_sees('Fry', {vm_expD.id}, {fw_expD.id})
        check_user_sees('Hubert', {vm_expD.id, vm_expS.id}, {fw_expD.id, fw_expS.id})
        check_user_sees('Bender', {vm_expD.id, vm_expS.id}, {fw_expD.id, fw_expS.id})

        # Test Filtering

        # filter VMExpiration by .vm field
        self.assertTrue(self.client.login(username='Fry', password='-'))
        response = self.client.get(reverse('vmexpiration-list') +
                '?vm=' + str(vmS.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({x['id'] for x in items}, set())

        self.assertTrue(self.client.login(username='Hubert', password='-'))
        response = self.client.get(reverse('vmexpiration-list') +
                '?vm=' + str(vmS.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({x['id'] for x in items}, {vm_expS.id})

        # filter FirewallRuleExpiration by .firewallrule field
        self.assertTrue(self.client.login(username='Fry', password='-'))
        response = self.client.get(reverse('firewallruleexpiration-list') +
                '?firewallrule=' + str(fw_rule_S.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({x['id'] for x in items}, set())

        self.assertTrue(self.client.login(username='Hubert', password='-'))
        response = self.client.get(reverse('firewallruleexpiration-list') +
                '?firewallrule=' + str(fw_rule_S.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({x['id'] for x in items}, {fw_expS.id})

        # test write operations

        self.assertTrue(self.client.login(username='Fry', password='-'))
        for (view_root, arg) in (
                ('vmexpiration', vm_expD.id),
                ('firewallruleexpiration', fw_expD.id),
                ):
            response = self.client.get(reverse(view_root + '-detail',
                args=[arg]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            item = response.data

            # can't modify
            response = self.client.put(reverse(view_root + '-detail',
                args=[arg]),
                    item, format='json')
            self.assertEqual(response.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED)

            # can't delete
            response = self.client.delete(reverse(view_root + '-detail',
                args=[arg]))
            self.assertEqual(response.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED)

            # can't create
            del item['id']
            response = self.client.post(reverse(view_root + '-list'), item,
                    format='json')
            self.assertEqual(response.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED)


class FirewallRule_AWSFirewallRule_Tests(TestCase):

    def setUp(self):
        self.saved_trusted_nets = settings.TRUSTED_NETWORKS
        settings.TRUSTED_NETWORKS = ['192.168.0.0/16']

    def tearDown(self):
        settings.TRUSTED_NETWORKS = self.saved_trusted_nets

    def test_firewall_special_check(self):
        """
        Test if firewall rules are flagged as special correctly.
        """
        non_special = [
            AWSFirewallRule(from_port=80, to_port=80, cidr_ip="10.10.0.0/24", ip_protocol=AWSFirewallRule.PROTO_TCP),
            AWSFirewallRule(from_port=80, to_port=80, cidr_ip="10.10.0.1/32", ip_protocol=AWSFirewallRule.PROTO_TCP),
            AWSFirewallRule(from_port=80, to_port=80, cidr_ip="1.2.3.4/27", ip_protocol=AWSFirewallRule.PROTO_TCP),
            AWSFirewallRule(from_port=80, to_port=80, cidr_ip="192.168.0.0/16", ip_protocol=AWSFirewallRule.PROTO_TCP),
            AWSFirewallRule(from_port=80, to_port=80, cidr_ip="192.168.0.0/23", ip_protocol=AWSFirewallRule.PROTO_TCP),
        ]

        special = [
            AWSFirewallRule(from_port=80, to_port=80, cidr_ip="10.10.0.0/23", ip_protocol=AWSFirewallRule.PROTO_TCP),
            AWSFirewallRule(from_port=80, to_port=80, cidr_ip="0.0.0.0/0", ip_protocol=AWSFirewallRule.PROTO_TCP),
            AWSFirewallRule(from_port=80, to_port=80, cidr_ip="10.10.0.0/8", ip_protocol=AWSFirewallRule.PROTO_TCP),
            AWSFirewallRule(from_port=80, to_port=80, cidr_ip="192.168.0.0/15", ip_protocol=AWSFirewallRule.PROTO_TCP),
        ]

        for rule in non_special:
            self.assertFalse(rule.is_special())

        for rule in special:
            self.assertTrue(rule.is_special())

    def test_api_permissions(self):
        """
        Users can read FirewallRule and AWSFirewallRule objects
        for VMs in one of their projects.
        The API is read-only.
        """
        uF = util.create_vimma_user('Fry', 'fry@pe.com', '-')
        uH = util.create_vimma_user('Hubert', 'hubert@pe.com', '-')
        uB = util.create_vimma_user('Bender', 'bender@pe.com', '-')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))

        prv = AWSProvider.objects.create(name='My Prov')
        pD = Project.objects.create(name='Prj Delivery', email='p-d@pe.com')
        pS = Project.objects.create(name='Prj Smelloscope', email='p-s@pe.com')

        config = AWSVMConfig.objects.create(name='My Config', default_schedule=s, provider=prv)

        vmD = AWSVM.objects.create(config=config, project=pD, schedule=s)
        vmS = AWSVM.objects.create(config=config, project=pS, schedule=s)

        fw_ruleD = FirewallRule.objects.create(vm=vmD)
        aws_fw_ruleD = AWSFirewallRule.objects.create(firewallrule=fw_ruleD,
                ip_protocol=AWSFirewallRule.PROTO_TCP,
                from_port=80, to_port=80, cidr_ip='1.2.3.4/0')
        fw_ruleS = FirewallRule.objects.create(vm=vmS)
        aws_fw_ruleS = AWSFirewallRule.objects.create(firewallrule=fw_ruleS,
                ip_protocol=AWSFirewallRule.PROTO_TCP,
                from_port=80, to_port=80, cidr_ip='1.2.3.4/0')

        uF.projects.add(pD)
        uH.projects.add(pD, pS)

        perm = Permission.objects.create(name=Perms.OMNIPOTENT)
        role = Role.objects.create(name='all powerful')
        role.permissions.add(perm)
        uB.roles.add(role)

        def check_user_sees(username, fw_id_set, aws_fw_id_set):
            """
            Check that username sees all FirewallRule and AWSFirewallRule
            in the sets and nothing else.
            """
            self.assertTrue(self.client.login(username=username, password='-'))
            for view_root, id_set in (
                    ('firewallrule', fw_id_set),
                    ('awsfirewallrule', aws_fw_id_set),
                    ):
                response = self.client.get(reverse(view_root + '-list'))
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                items = response.data['results']
                self.assertEqual({x['id'] for x in items}, id_set)

        check_user_sees('Fry', {fw_ruleD.id}, {aws_fw_ruleD.id})
        check_user_sees('Hubert', {fw_ruleD.id, fw_ruleS.id},
                {aws_fw_ruleD.id, aws_fw_ruleS.id})
        check_user_sees('Bender', {fw_ruleD.id, fw_ruleS.id},
                {aws_fw_ruleD.id, aws_fw_ruleS.id})

        # Test Filtering

        # filter FirewallRule by .vm field
        self.assertTrue(self.client.login(username='Fry', password='-'))
        response = self.client.get(reverse('firewallrule-list') +
                '?vm=' + str(vmS.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({x['id'] for x in items}, set())

        self.assertTrue(self.client.login(username='Hubert', password='-'))
        response = self.client.get(reverse('firewallrule-list') +
                '?vm=' + str(vmS.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({x['id'] for x in items}, {fw_ruleS.id})

        # filter AWSFirewallRule by .firewallrule field
        self.assertTrue(self.client.login(username='Fry', password='-'))
        response = self.client.get(reverse('awsfirewallrule-list') +
                '?firewallrule=' + str(fw_ruleS.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({x['id'] for x in items}, set())

        self.assertTrue(self.client.login(username='Hubert', password='-'))
        response = self.client.get(reverse('awsfirewallrule-list') +
                '?firewallrule=' + str(fw_ruleS.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({x['id'] for x in items}, {aws_fw_ruleS.id})

        # test write operations

        self.assertTrue(self.client.login(username='Fry', password='-'))
        response = self.client.get(reverse('firewallrule-detail',
            args=[fw_ruleD.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fw_item = response.data

        self.assertTrue(self.client.login(username='Fry', password='-'))
        response = self.client.get(reverse('awsfirewallrule-detail',
            args=[aws_fw_ruleD.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        aws_fw_item = response.data

        # can't modify
        response = self.client.put(reverse('firewallrule-detail',
            args=[fw_ruleD.id]), fw_item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)
        response = self.client.put(reverse('awsfirewallrule-detail',
            args=[aws_fw_ruleD.id]), aws_fw_item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('firewallrule-detail',
            args=[fw_ruleD.id]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)
        response = self.client.delete(reverse('awsfirewallrule-detail',
            args=[aws_fw_ruleD.id]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del fw_item['id']
        response = self.client.post(reverse('firewallrule-list'), fw_item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)
        del aws_fw_item['id']
        response = self.client.post(reverse('awsfirewallrule-list'),
                aws_fw_item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)
