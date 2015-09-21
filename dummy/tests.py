import datetime, urllib
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Q
from django.db.utils import IntegrityError, DataError
from django.test import TestCase
from django.utils.timezone import utc
import json
import pytz
import ipaddress
from rest_framework import status
from rest_framework.test import APITestCase

from vimma import util
from vimma.models import (
    Permission, Role,
    Project, TimeZone, Schedule,
    User, Audit,
)
from vimma.perms import ALL_PERMS, Perms
from vimma.audit import Auditor

from dummy.models import Provider, Config, VM, Expiration, PowerLog

def create_vm(name='A', tz='Europe/Helsinki'):
    tz,_ = TimeZone.objects.get_or_create(name=tz)
    s,_ = Schedule.objects.get_or_create(name='DefaultSchedule', timezone=tz, matrix=json.dumps(7 * [48 * [True]]))
    prv,_ = Provider.objects.get_or_create(name='DefaultProvider')
    config,_ = Config.objects.get_or_create(name='DefaultConfig', default_schedule=s, provider=prv)
    prj,_ = Project.objects.get_or_create(name='DefaultProject', email='default@email.com')
    return VM.objects.create(name=name, config=config, project=prj, schedule=s)

def byVm(vm):
    ct = ContentType.objects.get_for_model(vm)
    return 'content_object_type={ct.id}&object_id={vm.id}'.format(ct=ct, vm=vm)

class ProviderTests(APITestCase):

    def test_requires_name_and_type(self):
        """
        Provider requires name and type fields.
        """
        for bad_prov in (
            dict(),
            ):
            with self.assertRaises(ValidationError):
                Provider.objects.create(**bad_prov)
        Provider.objects.create(name='My Provider')

    def test_default(self):
        """
        Test the behavior of the ‘default’ field on save().
        """
        # test the code path when the first created object is already default
        p1 = Provider.objects.create(name='p1', default=True).id
        Provider.objects.get(id=p1)
        self.assertIs(Provider.objects.get(id=p1).default, True)
        Provider.objects.get(id=p1).delete()

        # First object, auto-set as default
        p1 = Provider.objects.create(name='p1').id
        Provider.objects.get(id=p1)
        self.assertIs(Provider.objects.get(id=p1).default, True)

        # second object, not default
        p2 = Provider.objects.create(name='p2').id
        Provider.objects.get(id=p2)
        self.assertIs(Provider.objects.get(id=p2).default, False)

        p = Provider.objects.get(id=p1)
        p.default = False
        p.save()

        # marked back as default on save
        self.assertIs(Provider.objects.get(id=p1).default, True)
        self.assertEqual(Provider.objects.filter(default=True).count(), 1)

        # new default object removes previous default(s)
        p3 = Provider.objects.create(name='p3', default=True).id
        Provider.objects.get(id=p3)
        self.assertIs(Provider.objects.get(id=p3).default, True)
        self.assertEqual(Provider.objects.filter(default=True).count(), 1)

        # the default flag works globally for all providers of all types
        self.assertIs(Provider.objects.get(id=p3).default, True)
        self.assertEqual(Provider.objects.filter(default=True).count(), 1)

    def test_api_permissions(self):
        """
        Users can read Provider objects. The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        prov = Provider.objects.create(name='My Provider')

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


class ProviderTests(APITestCase):

    def test_api_permissions(self):
        """
        Users can read Provider objects. The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        dummyProv = Provider.objects.create(name='My Provider')

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



class ConfigTests(APITestCase):

    def test_required_fields(self):
        """
        Config requires name, default_schedule and provider.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        p = Provider.objects.create(name='My Prov')
        for bad_vm_conf in (
            dict(provider=p),
            ):
            with self.assertRaises(ValidationError):
                Config.objects.create(**bad_vm_conf)
        for bad_vm_conf in (
            dict(),
            dict(name='My Conf'),
            dict(default_schedule=s),
            dict(name='My Conf', default_schedule=s),
            ):
            with self.assertRaises(ObjectDoesNotExist):
                Config.objects.create(**bad_vm_conf)

    def test_default_value_and_protected(self):
        """
        By default, is_special = False and PROTECTED constraints.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        p = Provider.objects.create(name='My Prov')
        vmc = Config.objects.create(name='My Conf', default_schedule=s,
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
        d = Provider.objects.create(name=' P')

        # test the code path when the first created object is already default
        d1 = Config.objects.create(name='d1', default_schedule=s,
                provider=d, default=True).id
        Config.objects.get(id=d1)
        self.assertIs(Config.objects.get(id=d1).default, True)
        Config.objects.get(id=d1).delete()

        # First object, auto-set as default
        d1 = Config.objects.create(name='d1', default_schedule=s,
                provider=d).id
        Config.objects.get(id=d1)
        self.assertIs(Config.objects.get(id=d1).default, True)

        # second object, not default
        d2 = Config.objects.create(name='d2', default_schedule=s,
                provider=d).id
        Config.objects.get(id=d2)
        self.assertIs(Config.objects.get(id=d2).default, False)

        x = Config.objects.get(id=d1)
        x.default = False
        x.save()

        # marked back as default on save
        self.assertIs(Config.objects.get(id=d1).default, True)
        self.assertEqual(Config.objects.filter(default=True).count(), 1)

        # new default object removes previous default(s)
        d3 = Config.objects.create(name='d3', default_schedule=s,
                provider=d, default=True).id
        Config.objects.get(id=d3)
        self.assertIs(Config.objects.get(id=d3).default, True)
        self.assertEqual(Config.objects.filter(default=True).count(), 1)

        # the default flag works per-provider instance
        self.assertIs(Config.objects.get(id=d3).default, True)
        self.assertEqual(Config.objects.filter(default=True).count(), 1)

        a2 = Config.objects.create(name='a2', default_schedule=s,
                provider=d).id
        Config.objects.get(id=a2)
        self.assertIs(Config.objects.get(id=d3).default, True)
        self.assertEqual(Config.objects.filter(default=True).count(), 1)

        a3 = Config.objects.create(name='a3', default_schedule=s,
                provider=d, default=True).id
        Config.objects.get(id=a3)
        self.assertIs(Config.objects.get(id=d3).default, False)
        self.assertEqual(Config.objects.filter(default=True).count(), 1)

    def test_api_permissions(self):
        """
        Users can read Config objects. The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        p = Provider.objects.create(name='My Prov')
        vmc = Config.objects.create(name='My Conf', default_schedule=s,
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


class ConfigTests(APITestCase):

    def test_required_fields(self):
        with self.assertRaises(ObjectDoesNotExist):
            Config.objects.create()

    def test_protected(self):
        """
        Check on_delete PROTECTED restriction.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        p = Provider.objects.create(name='My Prov')
        vmc = Config.objects.create(name='My Conf', default_schedule=s,
                provider=p)

        vmc.delete()
        p.delete()
        s.delete()
        tz.delete()

    def test_api_permissions(self):
        """
        Users can read Config objects. The API doesn't allow writing.
        """
        user = util.create_vimma_user('a', 'a@example.com', 'p')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        p = Provider.objects.create(name='My Prov')
        config = Config.objects.create(name='My Conf', default_schedule=s,
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



class VMTests(APITestCase):

    def test_required_fields(self):
        """
        VM requires provider, project and default_schedule.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = Provider.objects.create(name='My Prov')
        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)
        prj = Project.objects.create(name='Prj', email='a@b.com')

        for bad_vm in (
                dict(),
                dict(schedule=s),
                dict(config=config),
                dict(schedule=s, project=prj),
            ):
            with self.assertRaises(ValidationError):
                VM.objects.create(**bad_vm)

    def test_protected(self):
        """
        Test PROTECTED constraints.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = Provider.objects.create(name='My Prov')
        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)
        prj = Project.objects.create(name='Prj', email='a@b.com')
        vm = VM.objects.create(name="A", config=config, project=prj, schedule=s)

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

        prv = Provider.objects.create(name='My Prov')
        cfg = Config.objects.create(name='My Cfg', provider=prv, default_schedule=s)

        prj = Project.objects.create(name='My Prov', email='a@b.com')

        u = util.create_vimma_user('a', 'a@example.com', 'p')
        vm = VM.objects.create(name="My VM", config=cfg, project=prj, schedule=s,
                created_by=u)
        def check_creator_id(user_id):
            user = VM.objects.get(id=vm.id).created_by
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

        prv = Provider.objects.create(name='My Prov')
        cfg = Config.objects.create(name="My Config", provider=prv, default_schedule=s)
        p1 = Project.objects.create(name='Prj 1', email='p1@a.com')
        p2 = Project.objects.create(name='Prj 2', email='p2@a.com')
        p3 = Project.objects.create(name='Prj 3', email='p3@a.com')
        vm1 = VM.objects.create(name="A", config=cfg, project=p1, schedule=s)
        vm2 = VM.objects.create(name="B", config=cfg, project=p2, schedule=s)
        vm3 = VM.objects.create(name="C", config=cfg, project=p3, schedule=s)

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


class VMTests(APITestCase):

    def test_required_fields(self):
        """
        VM requires vm.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = Provider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = VM.objects.create(config=config, project=prj, schedule=s)

        # with self.assertRaises(ValidationError):
        VM(name='dummy')

    def test_protected(self):
        """
        Test PROTECTED constraint.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = Provider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = VM.objects.create(config=config, project=prj, schedule=s)

        vm.delete()
        with self.assertRaises(ProtectedError):
            prv.delete()
        prj.delete()
        with self.assertRaises(ProtectedError):
            s.delete()
        with self.assertRaises(ProtectedError):
            tz.delete()

    def test_api_permissions(self):
        """
        Users can read VM objects in their own projects, or in all
        projects with a permission. The API doesn't allow writing.
        """
        ua = util.create_vimma_user('a', 'a@example.com', 'p')
        ub = util.create_vimma_user('b', 'b@example.com', 'p')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))

        prv = Provider.objects.create(name='My Prov')

        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)

        p1 = Project.objects.create(name='Prj 1', email='p1@a.com')
        p2 = Project.objects.create(name='Prj 2', email='p2@a.com')
        p3 = Project.objects.create(name='Prj 3', email='p3@a.com')

        dvm1 = VM.objects.create(config=config, project=p1, schedule=s, name="dummy 1")
        dvm2 = VM.objects.create(config=config, project=p2, schedule=s, name="dummy 2")
        dvm3 = VM.objects.create(config=config, project=p3, schedule=s, name="dummy 3")

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
        self.assertEqual({dvm1.id, dvm2.id}, {x['id'] for x in items})

        response = self.client.get(reverse('dummyvm-detail', args=[dvm1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse('dummyvm-detail', args=[dvm3.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # filter by .vm field
        response = self.client.get(reverse('dummyvm-list') + '?id=' + str(dvm1.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({dvm1.id}, {x['id'] for x in items})

        # user B can see all VMs in all projects
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


class CreatePowerOnOffRebootDestroyVMTests(TestCase):
    def test_create_perms_and_not_found(self):
        """
        Test user permissions when creating a VM, or requested data not found.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prov = Provider.objects.create(name='My Provider')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))

        vmc = Config.objects.create(name='My Conf', default_schedule=s,
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
        prov2 = Provider.objects.create(name='My Special Provider', is_special=True)
        vmc2 = Config.objects.create(name='My Conf 2', default_schedule=s,
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

        prov = Provider.objects.create(name='My Provider')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))
        config = Config.objects.create(name='My Conf 2', default_schedule=s,
                provider=prov)

        vm = VM.objects.create(config=config, project=prj, schedule=s, name="dummy")

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
    def test_perms_and_not_found(self):
        """
        Test user permissions and ‘not found’.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prov = Provider.objects.create(name='My Provider', max_override_seconds=3600)

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))
        config = Config.objects.create(name='My Config', default_schedule=s, provider=prov)

        vm = VM.objects.create(config=config, project=prj, schedule=s)

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
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prov = Provider.objects.create(name='My Provider', max_override_seconds=3600)

        tz = TimeZone.objects.create(name='Pacific/Easter')
        s_off = Schedule.objects.create(name='Always OFF', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))
        s_on = Schedule.objects.create(name='Always On', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))

        config = Config.objects.create(name='My Config', default_schedule=s_on, provider=prov)

        vm = VM.objects.create(config=config, project=prj, schedule=s_off)

        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        expire_dt = now + datetime.timedelta(minutes=1)
        exp = Expiration.objects.create(vm=vm, expires_at=expire_dt)
        del now

        def check_overrides():
            old_state = vm.sched_override_state
            old_tstamp = vm.sched_override_tstamp
            old_vm_at_now = vm.controller().vm_at_now()

            now = datetime.datetime.utcnow().replace(tzinfo=utc)
            # if the override expired already, it has no effect
            end = now + datetime.timedelta(minutes=-1)
            vm.sched_override_tstamp = end.timestamp()
            vm.save()

            for new_state in (True, False):
                vm.sched_override_state = new_state
                vm.save()
                self.assertIs(vm.controller().vm_at_now(), old_vm_at_now)

            # if the override hasn't expired yet, it's used
            end = now + datetime.timedelta(minutes=1)
            vm.sched_override_tstamp = end.timestamp()
            vm.save()

            for new_state in (True, False):
                vm.sched_override_state = new_state
                vm.save()
                self.assertIs(vm.controller().vm_at_now(), new_state)

            vm.sched_override_state = old_state
            vm.sched_override_tstamp = old_tstamp
            vm.save()

        self.assertFalse(vm.controller().vm_at_now())
        check_overrides()

        vm.schedule = s_on
        vm.save()
        self.assertTrue(vm.controller().vm_at_now())
        check_overrides()

        # if the VM has expired, it's OFF, regardles of schedule and overrides

        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        expire_dt = now - datetime.timedelta(minutes=1)
        exp.expires_at = expire_dt
        exp.save()
        self.assertFalse(vm.controller().vm_at_now())

        end = now + datetime.timedelta(minutes=1)
        vm.sched_override_tstamp = end.timestamp()
        vm.sched_override_state = True
        vm.save()
        self.assertFalse(vm.controller().vm_at_now())

class ChangeVMScheduleTests(TestCase):
    def test_perms_and_not_found(self):
        """
        Test user permissions and ‘not found’.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prov = Provider.objects.create(name='My Provider')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s1 = Schedule.objects.create(name='s1', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))
        s2 = Schedule.objects.create(name='s2', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))
        s3 = Schedule.objects.create(name='s3', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]), is_special=True)
        config = Config.objects.create(name='My Config', default_schedule=s1, provider=prov)

        vm = VM.objects.create(config=config, project=prj, schedule=s1)

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
    def test_VM_perms_and_not_found(self):
        """
        Test user permissions and ‘not found’ for VM Expirations.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prv = Provider.objects.create(name='My Provider')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))

        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = VM.objects.create(name="My VM", config=config, project=prj, schedule=s)

        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        now_ts = int(now.timestamp())
        future_ts = int((now + datetime.timedelta(hours=1)).timestamp())
        future2_ts = int((now + datetime.timedelta(hours=2)).timestamp())
        past_ts = int((now - datetime.timedelta(hours=1)).timestamp())
        exp = Expiration.objects.create(expires_at=now, vm=vm)

        url = reverse('setExpiration')

        def checkExpiration(exp_id, timestamp):
            """
            Check that exp_id expires at timestamp.
            """
            self.assertEqual(
                int(Expiration.objects.get(id=exp_id).expires_at.timestamp()),
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

class PowerLogTests(TestCase):
    def test_required_fields(self):
        """
        Test required fields: vm, powered_on.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = Provider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = VM.objects.create(name="my-vm", config=config, project=prj, schedule=s)

        for kw in ({}, {'powered_on': True}):
            with self.assertRaises(ValidationError):
                PowerLog.objects.create(**kw)
        PowerLog.objects.create(vm=vm, powered_on=True)

    def test_on_delete_constraints(self):
        """
        Test on_delete constraints for vm field.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = Provider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = VM.objects.create(config=config, project=prj, schedule=s)

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

        prv = Provider.objects.create(name='My Prov')
        pD = Project.objects.create(name='Prj Delivery', email='p-d@pe.com')
        pS = Project.objects.create(name='Prj Smelloscope', email='p-s@pe.com')
        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)

        vmD = VM.objects.create(config=config, project=pD, schedule=s)
        vmS = VM.objects.create(config=config, project=pS, schedule=s)

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
                '?' + byVm(vmS))
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


class AuditTests(TestCase):

    def test_audit_context_manager(self):
        aud = Auditor('foo')
        with self.assertRaises(Exception):
            with aud.ctx_mgr():
                raise Exception("hello world")

        with aud.ctx_mgr():
            print("hello world")

    def test_user_audit(self):
        u = util.create_vimma_user('user', 'user@example.com', '-')
        u.auditor.info("Hello World")

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


    def test_text_length(self):
        with self.assertRaises(ValidationError):
            Audit.objects.create(level=Audit.DEBUG, text='')

        vm = create_vm(name='AuditVM')
        Audit.objects.create(level=Audit.DEBUG, text='a', content_object=vm)
        vm.auditor.debug(msg='a')


    def test_timestamp(self):
        """
        Test that timestamp is the time of creation.
        """
        vm = create_vm(name='AuditVM')
        a = Audit.objects.create(level=Audit.DEBUG, text='a', content_object=vm)
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        delta = now - a.timestamp
        self.assertTrue(delta <= datetime.timedelta(minutes=1))


    def test_min_level(self):
        """
        Check the min_level API filter.
        """
        u = util.create_vimma_user('user', 'user@example.com', '-')
        vm = create_vm(name='AuditVM')

        Audit.objects.create(level=Audit.DEBUG, user=u, text='-d', content_object=vm)
        Audit.objects.create(level=Audit.WARNING, user=u, text='-w', content_object=vm)
        # TODO: test that this really goes to standard output
        vm.auditor.error(msg='-e', user_id=u.id)

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

    def test_on_delete_constraints(self):
        """
        Test on_delete constraints for user and vm fields.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')

        vm = create_vm(name='AuditVM')

        a = Audit.objects.create(level=Audit.INFO, text='hi', user=u, content_object=vm)
        a_id = a.id
        del a

        u.delete()
        self.assertEqual(Audit.objects.get(id=a_id).user, None)
        vm.delete()
        with self.assertRaises(ObjectDoesNotExist):
            Audit.objects.get(id=a_id)

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

        prv = Provider.objects.create(name='My Prov')
        pD = Project.objects.create(name='Prj Delivery', email='p-d@pe.com')
        pS = Project.objects.create(name='Prj Smelloscope', email='p-s@pe.com')
        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)

        vmD = VM.objects.create(config=config, project=pD, schedule=s)
        vmS = VM.objects.create(config=config, project=pS, schedule=s)

        uF.projects.add(pD)
        uH.projects.add(pD, pS)

        perm = Permission.objects.create(name=Perms.READ_ALL_AUDITS)
        role = Role.objects.create(name='All Seeing')
        role.permissions.add(perm)
        uB.roles.add(role)

        vmD.auditor.info(msg='vmd-', user_id=None)
        vmS.auditor.info(msg='vms-fry', user_id=uF.pk)
        vmS.auditor.info(msg='vms-', user_id=None)

        def check_user_sees(username, text_set):
            """
            Check that username sees all audits in text_set and nothing else.
            """
            self.assertTrue(self.client.login(username=username, password='-'))
            response = self.client.get(reverse('audit-list'))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            items = response.data['results']
            self.assertEqual({x['text'] for x in items}, text_set)

        check_user_sees('Fry', {'vmd-', 'vms-fry'})
        check_user_sees('Hubert', {'vmd-', 'vms-fry', 'vms-'})
        check_user_sees('Bender', {'vmd-', 'vms-fry', 'vms-'})

        # Test Filtering
        # filter by VM
        self.assertTrue(self.client.login(username='Fry', password='-'))
        response = self.client.get(reverse('audit-list') + '?' + byVm(vmS))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({x['text'] for x in items}, {'vms-fry'})

        # filter by User
        self.assertTrue(self.client.login(username='Bender', password='-'))
        response = self.client.get(reverse('audit-list') +
                '?user=' + str(uF.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({x['text'] for x in items}, {'vms-fry'})

        # test write operations
        self.assertTrue(self.client.login(username='Fry', password='-'))
        a_id = vmS.audits.all()[0].id
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
