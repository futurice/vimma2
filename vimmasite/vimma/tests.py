import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db.models.deletion import ProtectedError
from django.db.utils import IntegrityError
from django.test import TestCase
import json
import pytz
from rest_framework import status
from rest_framework.test import APITestCase

from vimma import util
from vimma.actions import Actions
from vimma.models import (
    Permission, Role, Project, Profile, TimeZone, Schedule,
    Provider, DummyProvider, AWSProvider,
    VMConfig, DummyVMConfig, AWSVMConfig,
    VM, DummyVM, AWSVM,
)
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


class ProjectTests(APITestCase):

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

    def test_api_permissions(self):
        """
        Users can read projects they're members of. A permission lets them
        read all projects. The API doesn't allow writing.
        """
        user_a = util.create_vimma_user('a', 'a@example.com', 'p')
        user_b = util.create_vimma_user('b', 'b@example.com', 'p')

        role = Role.objects.create(name='All Seeing')
        role.full_clean()
        perm = Permission.objects.create(name=Perms.READ_ANY_PROJECT)
        perm.full_clean()
        role.permissions.add(perm)

        user_b.profile.roles.add(role)

        prj_a = Project.objects.create(name='PrjA', email='a@prj.com')
        prj_b = Project.objects.create(name='PrjB', email='b@prj.com')
        user_a.profile.projects.add(prj_a)
        user_b.profile.projects.add(prj_b)

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
            'first_name', 'last_name', 'email'})

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
        Everyone can read all profiles. Only some fields are exposed.
        The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('profile-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(len(items), 1)

        response = self.client.get(reverse('profile-detail',
            args=[user.profile.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data

        # check fields
        self.assertEqual(set(item.keys()), {'id', 'user', 'projects'})

        # can't modify
        response = self.client.put(reverse('profile-detail',
            args=[item['id']]), item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('profile-detail',
            args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('profile-list'), item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_API_filter(self):
        """
        Filter profiles by: project, user.
        """
        u_a = util.create_vimma_user('a', 'a@example.com', 'p')
        u_b = util.create_vimma_user('b', 'b@example.com', 'p')
        u_c = util.create_vimma_user('c', 'c@example.com', 'p')

        p1 = Project.objects.create(name='P1', email='p1@x.com')
        p1.full_clean()
        p2 = Project.objects.create(name='P2', email='p2@x.com')
        p2.full_clean()
        p3 = Project.objects.create(name='P3', email='p3@x.com')
        p3.full_clean()

        u_a.profile.projects.add(p1, p2)
        u_b.profile.projects.add(p2, p3)
        u_c.profile.projects.add(p3)

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get('{}?projects={}'.format(
            reverse('profile-list'), p2.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(set(i['id'] for i in items),
                {u_a.profile.id, u_b.profile.id})

        response = self.client.get(reverse('profile-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(set(i['id'] for i in items),
                {u_a.profile.id, u_b.profile.id, u_c.profile.id})

        response = self.client.get('{}?user={}'.format(
            reverse('profile-list'), u_a.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(set(i['id'] for i in items), {u_a.profile.id})


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
        self.assertIs(s.is_special, False)

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

    def test_schedule_at_tstamp(self):
        """
        Check the util.schedule_at_tstamp function.
        """
        for tz_name in ['America/Los_Angeles', 'Europe/Madrid', 'Asia/Tokyo']:
            tz = pytz.timezone(tz_name)
            tz_obj = TimeZone.objects.create(name=tz_name)
            tz_obj.full_clean()
            matrix = 5*[8*2*[False] + 8*2*[True] + 8*2*[False]]+ 2*[48*[False]]
            s = Schedule.objects.create(name='Weekdays 8am→4pm, ' + tz_name,
                    timezone=tz_obj, matrix=json.dumps(matrix))
            s.full_clean()

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


class ProviderTests(APITestCase):

    def test_requires_name_and_type(self):
        """
        Provider requires name and type fields.
        """
        for bad_prov in (
            Provider(),
            Provider(name='My Provider'),
            Provider(type=Provider.TYPE_DUMMY),
            Provider(name='My Provider', type='no-such-type'),
            ):
            with self.assertRaises(ValidationError):
                bad_prov.full_clean()
        Provider.objects.create(name='My Provider',
                type=Provider.TYPE_DUMMY).full_clean()

    def test_api_permissions(self):
        """
        Users can read Provider objects. The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        prov = Provider.objects.create(name='My Provider',
                type=Provider.TYPE_DUMMY)
        prov.full_clean()

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('provider-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(len(items), 1)

        response = self.client.get(reverse('provider-detail', args=[prov.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data

        # can't modify
        item['name'] = 'Renamed'
        response = self.client.put(reverse('provider-detail',
            args=[item['id']]), item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('provider-detail',
            args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('provider-list'), item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


class DummyProviderTests(APITestCase):

    def test_requires_provider(self):
        """
        DummyProvider requires non-null Provider.
        """
        with self.assertRaises(IntegrityError):
            DummyProvider.objects.create()

    def test_protect_provider_delete(self):
        """
        Can't delete a Provider still used by a DummyProvider.
        """
        p = Provider.objects.create(name='My Prov', type=Provider.TYPE_DUMMY)
        d = DummyProvider.objects.create(provider=p)
        with self.assertRaises(ProtectedError):
            p.delete()
        d.delete()
        p.delete()

    def test_api_permissions(self):
        """
        Users can read DummyProvider objects. The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        prov = Provider.objects.create(name='My Provider',
                type=Provider.TYPE_DUMMY)
        prov.full_clean()
        dummyProv = DummyProvider.objects.create(provider=prov)
        dummyProv.full_clean()

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

    def test_requires_provider(self):
        """
        AWSProvider requires non-null Provider.
        """
        with self.assertRaises(IntegrityError):
            AWSProvider.objects.create()

    def test_protect_provider_delete(self):
        """
        Can't delete a Provider still used by a AWSProvider.
        """
        p = Provider.objects.create(name='My Prov', type=Provider.TYPE_AWS)
        a = AWSProvider.objects.create(provider=p)
        with self.assertRaises(ProtectedError):
            p.delete()
        a.delete()
        p.delete()

    def test_api_permissions(self):
        """
        Users can read AWSProvider objects. The API doesn't allow writing.
        """
        def checkVisibility(apiDict):
            """
            Check visible and invisible fields returned by the API.
            """
            self.assertTrue('id' in apiDict)
            self.assertFalse('access_key_id' in apiDict)
            self.assertFalse('access_key_secret' in apiDict)

        user = util.create_vimma_user('a', 'a@example.com', 'p')

        prov = Provider.objects.create(name='My Provider',
                type=Provider.TYPE_AWS)
        prov.full_clean()
        awsProv = AWSProvider.objects.create(provider=prov)
        awsProv.full_clean()

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('awsprovider-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(len(items), 1)
        checkVisibility(items[0])

        response = self.client.get(reverse('awsprovider-detail',
            args=[awsProv.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data
        checkVisibility(item)

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
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()
        p = Provider.objects.create(name='My Prov', type=Provider.TYPE_DUMMY)
        p.full_clean()
        for bad_vm_conf in (
            VMConfig(),
            VMConfig(name='My Conf'),
            VMConfig(default_schedule=s),
            VMConfig(provider=p),
            VMConfig(name='My Conf', default_schedule=s),
            ):
            with self.assertRaises(ValidationError):
                bad_vm_conf.full_clean()

    def test_default_value_and_protected(self):
        """
        By default, requires_permission = False and PROTECTED constraints.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()
        p = Provider.objects.create(name='My Prov', type=Provider.TYPE_DUMMY)
        p.full_clean()
        vmc = VMConfig.objects.create(name='My Conf', default_schedule=s,
                provider=p)
        vmc.full_clean()
        self.assertIs(vmc.requires_permission, False)

        with self.assertRaises(ProtectedError):
            p.delete()
        with self.assertRaises(ProtectedError):
            s.delete()

        vmc.delete()
        p.delete()
        s.delete()
        tz.delete()

    def test_api_permissions(self):
        """
        Users can read VMConfig objects. The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()
        p = Provider.objects.create(name='My Prov', type=Provider.TYPE_DUMMY)
        p.full_clean()
        vmc = VMConfig.objects.create(name='My Conf', default_schedule=s,
                provider=p)
        vmc.full_clean()

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('vmconfig-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(len(items), 1)

        response = self.client.get(reverse('vmconfig-detail',
            args=[vmc.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data

        # can't modify
        response = self.client.put(reverse('vmconfig-detail',
            args=[item['id']]), item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('vmconfig-detail',
            args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('vmconfig-list'), item,
                format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


class DummyVMConfigTests(APITestCase):

    def test_required_fields(self):
        """
        DummyVMConfig requires vmconfig.
        """
        with self.assertRaises(ValidationError):
            DummyVMConfig().full_clean()

    def test_protected(self):
        """
        Check on_delete PROTECTED restriction.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()
        p = Provider.objects.create(name='My Prov', type=Provider.TYPE_DUMMY)
        p.full_clean()
        vmc = VMConfig.objects.create(name='My Conf', default_schedule=s,
                provider=p)
        vmc.full_clean()
        dummyc = DummyVMConfig.objects.create(vmconfig=vmc)
        dummyc.full_clean()

        with self.assertRaises(ProtectedError):
            vmc.delete()

        dummyc.delete()
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
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()
        p = Provider.objects.create(name='My Prov', type=Provider.TYPE_DUMMY)
        p.full_clean()
        vmc = VMConfig.objects.create(name='My Conf', default_schedule=s,
                provider=p)
        vmc.full_clean()
        dummyc = DummyVMConfig.objects.create(vmconfig=vmc)
        dummyc.full_clean()

        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('dummyvmconfig-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual(len(items), 1)

        response = self.client.get(reverse('dummyvmconfig-detail',
            args=[dummyc.id]))
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
        with self.assertRaises(ValidationError):
            AWSVMConfig().full_clean()

    def test_protected(self):
        """
        Check on_delete PROTECTED restriction.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()
        p = Provider.objects.create(name='My Prov', type=Provider.TYPE_AWS)
        p.full_clean()
        vmc = VMConfig.objects.create(name='My Conf', default_schedule=s,
                provider=p)
        vmc.full_clean()
        awsc = AWSVMConfig.objects.create(vmconfig=vmc)
        awsc.full_clean()

        with self.assertRaises(ProtectedError):
            vmc.delete()

        awsc.delete()
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
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()
        p = Provider.objects.create(name='My Prov', type=Provider.TYPE_AWS)
        p.full_clean()
        vmc = VMConfig.objects.create(name='My Conf', default_schedule=s,
                provider=p)
        vmc.full_clean()
        awsc = AWSVMConfig.objects.create(vmconfig=vmc)
        awsc.full_clean()

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
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()
        prv = Provider.objects.create(name='My Prov', type=Provider.TYPE_DUMMY)
        prv.full_clean()
        prj = Project.objects.create(name='Prj', email='a@b.com')
        prj.full_clean()

        for bad_vm in (
                VM(),
                VM(provider=prv), VM(project=prj), VM(schedule=s),
                VM(provider=prv, project=prj),
                VM(provider=prv, schedule=s), VM(project=prj, schedule=s),
            ):
            with self.assertRaises(ValidationError):
                bad_vm.full_clean()

    def test_protected(self):
        """
        Test PROTECTED constraints.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()
        prv = Provider.objects.create(name='My Prov', type=Provider.TYPE_DUMMY)
        prv.full_clean()
        prj = Project.objects.create(name='Prj', email='a@b.com')
        prj.full_clean()
        vm = VM.objects.create(provider=prv, project=prj, schedule=s)
        vm.full_clean()

        for func in (prv.delete, prj.delete, s.delete):
            with self.assertRaises(ProtectedError):
                func()

        vm.delete()
        prv.delete()
        prj.delete()
        s.delete()
        tz.delete()

    def test_api_permissions(self):
        """
        Users can read VM objects in their own projects, or in all projects
        with a permission. The API doesn't allow writing.
        """
        ua = util.create_vimma_user('a', 'a@example.com', 'p')
        ub = util.create_vimma_user('b', 'b@example.com', 'p')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()

        prv = Provider.objects.create(name='My Prov', type=Provider.TYPE_DUMMY)
        prv.full_clean()
        p1 = Project.objects.create(name='Prj 1', email='p1@a.com')
        p1.full_clean()
        p2 = Project.objects.create(name='Prj 2', email='p2@a.com')
        p2.full_clean()
        p3 = Project.objects.create(name='Prj 3', email='p3@a.com')
        p3.full_clean()
        vm1 = VM.objects.create(provider=prv, project=p1, schedule=s)
        vm1.full_clean()
        vm2 = VM.objects.create(provider=prv, project=p2, schedule=s)
        vm2.full_clean()
        vm3 = VM.objects.create(provider=prv, project=p3, schedule=s)
        vm3.full_clean()

        ua.profile.projects.add(p1, p2)
        ub.profile.projects.add(p1)

        perm = Permission.objects.create(name=Perms.READ_ANY_PROJECT)
        perm.full_clean()
        role = Role.objects.create(name='All Seeing')
        role.full_clean()
        role.permissions.add(perm)
        ub.profile.roles.add(role)

        # user A can only see VMs in his projects
        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('vm-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({vm1.id, vm2.id}, {x['id'] for x in items})

        response = self.client.get(reverse('vm-detail', args=[vm1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse('vm-detail', args=[vm3.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # filter by project name
        response = self.client.get(reverse('vm-list') +
                '?project=' + str(p1.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({vm1.id}, {x['id'] for x in items})

        # user B can see all VMs in all projects
        self.assertTrue(self.client.login(username='b', password='p'))
        response = self.client.get(reverse('vm-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({vm1.id, vm2.id, vm3.id}, {x['id'] for x in items})

        for vm_id in (vm1.id, vm3.id):
            response = self.client.get(reverse('vm-detail', args=[vm_id]))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            item = response.data


        # can't modify
        response = self.client.put(reverse('vm-detail', args=[item['id']]),
                item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't delete
        response = self.client.delete(reverse('vm-detail', args=[item['id']]))
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('vm-list'), item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)


class DummyVMTests(APITestCase):

    def test_required_fields(self):
        """
        DummyVM requires vm.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()
        prv = Provider.objects.create(name='My Prov', type=Provider.TYPE_DUMMY)
        prv.full_clean()
        prj = Project.objects.create(name='Prj', email='a@b.com')
        prj.full_clean()
        vm = VM.objects.create(provider=prv, project=prj, schedule=s)

        with self.assertRaises(ValidationError):
            DummyVM(name='dummy').full_clean()

        DummyVM.objects.create(vm=vm, name='dummy').full_clean()

    def test_protected(self):
        """
        Test PROTECTED constraint.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()
        prv = Provider.objects.create(name='My Prov', type=Provider.TYPE_DUMMY)
        prv.full_clean()
        prj = Project.objects.create(name='Prj', email='a@b.com')
        prj.full_clean()
        vm = VM.objects.create(provider=prv, project=prj, schedule=s)
        vm.full_clean()
        dummyVm = DummyVM.objects.create(vm=vm, name='dummy')
        dummyVm.full_clean()

        with self.assertRaises(ProtectedError):
            vm.delete()

        dummyVm.delete()
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
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()

        prv = Provider.objects.create(name='My Prov', type=Provider.TYPE_DUMMY)
        prv.full_clean()
        p1 = Project.objects.create(name='Prj 1', email='p1@a.com')
        p1.full_clean()
        p2 = Project.objects.create(name='Prj 2', email='p2@a.com')
        p2.full_clean()
        p3 = Project.objects.create(name='Prj 3', email='p3@a.com')
        p3.full_clean()

        vm1 = VM.objects.create(provider=prv, project=p1, schedule=s)
        vm1.full_clean()
        vm2 = VM.objects.create(provider=prv, project=p2, schedule=s)
        vm2.full_clean()
        vm3 = VM.objects.create(provider=prv, project=p3, schedule=s)
        vm3.full_clean()

        dvm1 = DummyVM.objects.create(vm=vm1, name='dummy 1')
        dvm1.full_clean()
        dvm2 = DummyVM.objects.create(vm=vm2, name='dummy 2')
        dvm2.full_clean()
        dvm3 = DummyVM.objects.create(vm=vm3, name='dummy 3')
        dvm3.full_clean()

        ua.profile.projects.add(p1, p2)
        ub.profile.projects.add(p1)

        perm = Permission.objects.create(name=Perms.READ_ANY_PROJECT)
        perm.full_clean()
        role = Role.objects.create(name='All Seeing')
        role.full_clean()
        role.permissions.add(perm)
        ub.profile.roles.add(role)

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
        self.assertEqual({dvm1.vm.id}, {x['id'] for x in items})

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
        AWSVM requires vm.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()
        prv = Provider.objects.create(name='My Prov', type=Provider.TYPE_AWS)
        prv.full_clean()
        prj = Project.objects.create(name='Prj', email='a@b.com')
        prj.full_clean()
        vm = VM.objects.create(provider=prv, project=prj, schedule=s)

        with self.assertRaises(ValidationError):
            AWSVM().full_clean()

        AWSVM.objects.create(vm=vm).full_clean()

    def test_protected(self):
        """
        Test PROTECTED constraint.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()
        prv = Provider.objects.create(name='My Prov', type=Provider.TYPE_AWS)
        prv.full_clean()
        prj = Project.objects.create(name='Prj', email='a@b.com')
        prj.full_clean()
        vm = VM.objects.create(provider=prv, project=prj, schedule=s)
        vm.full_clean()
        awsVm = AWSVM.objects.create(vm=vm)
        awsVm.full_clean()

        with self.assertRaises(ProtectedError):
            vm.delete()

        awsVm.delete()
        vm.delete()
        prv.delete()
        prj.delete()
        s.delete()
        tz.delete()

    def test_api_permissions(self):
        """
        Users can read AWSVM objects in their own projects, or in all
        projects with a permission. The API doesn't allow writing.
        """
        ua = util.create_vimma_user('a', 'a@example.com', 'p')
        ub = util.create_vimma_user('b', 'b@example.com', 'p')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        s.full_clean()

        prv = Provider.objects.create(name='My Prov', type=Provider.TYPE_AWS)
        prv.full_clean()
        p1 = Project.objects.create(name='Prj 1', email='p1@a.com')
        p1.full_clean()
        p2 = Project.objects.create(name='Prj 2', email='p2@a.com')
        p2.full_clean()
        p3 = Project.objects.create(name='Prj 3', email='p3@a.com')
        p3.full_clean()

        vm1 = VM.objects.create(provider=prv, project=p1, schedule=s)
        vm1.full_clean()
        vm2 = VM.objects.create(provider=prv, project=p2, schedule=s)
        vm2.full_clean()
        vm3 = VM.objects.create(provider=prv, project=p3, schedule=s)
        vm3.full_clean()

        avm1 = AWSVM.objects.create(vm=vm1)
        avm1.full_clean()
        avm2 = AWSVM.objects.create(vm=vm2)
        avm2.full_clean()
        avm3 = AWSVM.objects.create(vm=vm3)
        avm3.full_clean()

        ua.profile.projects.add(p1, p2)
        ub.profile.projects.add(p1)

        perm = Permission.objects.create(name=Perms.READ_ANY_PROJECT)
        perm.full_clean()
        role = Role.objects.create(name='All Seeing')
        role.full_clean()
        role.permissions.add(perm)
        ub.profile.roles.add(role)

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
                '?vm=' + str(avm1.vm.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({avm1.vm.id}, {x['id'] for x in items})

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


class CreateVMTests(TestCase):

    def test_login_required(self):
        """
        The user must be logged in.
        """
        response = self.client.get(reverse('createVM'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unsupported_methods(self):
        """
        Only POST is supported (e.g. GET, PUT, DELETE are not).
        """
        util.create_vimma_user('a', 'a@example.com', 'pass')
        url = reverse('createVM')
        self.assertTrue(self.client.login(username='a', password='pass'))
        for meth in self.client.get, self.client.put, self.client.delete:
            response = meth(url)
            self.assertEqual(response.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_perms_and_not_found(self):
        """
        Test user permissions when creating a VM, or requested data not found.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        prj = Project.objects.create(name='prj', email='prj@x.com')
        prj.full_clean()

        prov = Provider.objects.create(name='My Provider',
                type=Provider.TYPE_DUMMY)
        prov.full_clean()
        dummyProv = DummyProvider.objects.create(provider=prov)
        dummyProv.full_clean()

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        tz.full_clean()
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))
        s.full_clean()

        vmc = VMConfig.objects.create(name='My Conf', default_schedule=s,
                provider=prov)
        vmc.full_clean()
        dummyc = DummyVMConfig.objects.create(vmconfig=vmc)
        dummyc.full_clean()

        url = reverse('createVM')
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({
                    'project': prj.id,
                    'vmconfig': vmc.id,
                    'schedule': s.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        u.profile.projects.add(prj)
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
        s2.full_clean()
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
        perm = Permission.objects.create(name=Perms.USE_SPECIAL_SCHEDULE)
        perm.full_clean()
        role = Role.objects.create(name='SpecSched Role')
        role.full_clean()
        role.permissions.add(perm)
        u.profile.roles.add(role)
        s3 = Schedule.objects.create(name='s3', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]), is_special=True)
        s3.full_clean()
        response = self.client.post(url, content_type='application/json',
                data=json.dumps({
                    'project': prj.id,
                    'vmconfig': vmc.id,
                    'schedule': s3.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CanDoTests(TestCase):

    def test_create_vm_in_project(self):
        prj1 = Project.objects.create(name='prj1', email='prj1@x.com')
        prj1.full_clean()
        prj2 = Project.objects.create(name='prj2', email='prj2@x.com')
        prj2.full_clean()
        u1 = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertFalse(util.can_do(u1, Actions.CREATE_VM_IN_PROJECT, prj1))
        self.assertFalse(util.can_do(u1, Actions.CREATE_VM_IN_PROJECT, prj2))
        u1.profile.projects.add(prj1)
        self.assertTrue(util.can_do(u1, Actions.CREATE_VM_IN_PROJECT, prj1))
        self.assertFalse(util.can_do(u1, Actions.CREATE_VM_IN_PROJECT, prj2))

        perm = Permission.objects.create(name=Perms.OMNIPOTENT)
        role = Role.objects.create(name='all powerful')
        role.permissions.add(perm)
        u1.profile.roles.add(role)
        self.assertTrue(util.can_do(u1, Actions.CREATE_VM_IN_PROJECT, prj1))
        self.assertTrue(util.can_do(u1, Actions.CREATE_VM_IN_PROJECT, prj2))
