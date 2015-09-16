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
from vimma.models import (
    Permission, Role,
    Project, TimeZone, Schedule,
    User,
)
from vimma.perms import ALL_PERMS, Perms

from aws.models import Provider, Config, VM, PowerLog, FirewallRule, Expiration, FirewallRuleExpiration

class ProviderTests(APITestCase):
    def test_defaults(self):
        # the default flag works globally for all providers of all types
        a1 = Provider.objects.create(name='a1').id
        Provider.objects.get(id=a1)

        a2 = Provider.objects.create(name='a2', default=True).id
        Provider.objects.get(id=a2)
        self.assertIs(Provider.objects.get(id=a2).default, True)

class ProviderTests(APITestCase):

    def test_provider_delete(self):
        p = Provider.objects.create(name='My Prov', vpc_id='dummy')
        p.delete()

    def test_api_permissions(self):
        """
        Users can read Provider objects. The API doesn't allow writing.
        """
        def checkVisibility(apiDict):
            """
            Check visible and invisible fields returned by the API.
            """
            self.assertEqual(set(apiDict.keys()),
                    {'id', 'provider', 'route_53_zone'})

        user = util.create_vimma_user('a', 'a@example.com', 'p')

        awsProv = Provider.objects.create(name="My Provider", vpc_id='dummy')

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

class ConfigTests(APITestCase):

    def test_required_fields(self):
        """
        Config requires vmconfig.
        """
        region = Config.regions[0]
        vol_type = Config.VOLUME_TYPE_CHOICES[0][0]
        with self.assertRaises(ObjectDoesNotExist):
            Config.objects.create(region=region, root_device_size=10,
                    root_device_volume_type=vol_type)

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        p = Provider.objects.create(name='My Prov')
        Config.objects.create(name="My Conf", region=region, root_device_size=10,
                root_device_volume_type=vol_type, default_schedule=s, provider=p)

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
        region = Config.regions[0]
        vol_type = Config.VOLUME_TYPE_CHOICES[0][0]
        config = Config.objects.create(name="My Config", provider=p, region=region,
                root_device_size=10, root_device_volume_type=vol_type, default_schedule=s)

        config.delete()
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
        awsc = Config.objects.create(name="My Conf", provider=p, region='ap-northeast-1',
                default_schedule=s, root_device_size=10, root_device_volume_type='standard')

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
        VM requires: vm, name, region.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = Provider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = VM.objects.create(config=config, project=prj, schedule=s)

        for kwargs in ({'name': 'a'}, {'region': 'a'},
                {'name': 'a'}, {'region': 'a'},
                {'name': 'a', 'region': 'a'}):
            with self.assertRaises(ValidationError):
                VM.objects.create(**kwargs)

    def test_name_validator(self):
        """
        VM name must conform to a certain format (used in DNS name).
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = Provider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)

        vm = VM.objects.create(config=config, project=prj, schedule=s)
        for name in ('', ' ', '-', '-a', 'a-', '.', 'dev.vm'):
            with self.assertRaises(ValidationError):
                VM.objects.create(config=config, region='a', name=name)
        vm.delete()

        for name in ('a', '5', 'a-b', 'build-server', 'x-0-dev'):
            VM.objects.create(config=config, project=prj, schedule=s, name=name)

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

    def test_ip_address(self):
        """
        Test the IP address default, check that it can't be None.
        """
        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))
        prv = Provider.objects.create(name='My Prov')
        prj = Project.objects.create(name='Prj', email='a@b.com')
        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)

        vm = VM.objects.create(config=config, project=prj, schedule=s)
        self.assertEqual(vm.ip_address, '')

        vm = VM.objects.create(config=config, project=prj, schedule=s, name='ip', region='a', ip_address='192.168.0.1')
        with self.assertRaises(ValidationError):
            VM.objects.create(name='ip', region='a', ip_address=None)

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

        prv = Provider.objects.create(name='My Provider')
        p1 = Project.objects.create(name='Prj 1', email='p1@a.com')
        p2 = Project.objects.create(name='Prj 2', email='p2@a.com')
        p3 = Project.objects.create(name='Prj 3', email='p3@a.com')

        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)

        avm1 = VM.objects.create(name='1', region='a', config=config, project=p1, schedule=s)
        avm2 = VM.objects.create(name='2', region='b', config=config, project=p2, schedule=s)
        avm3 = VM.objects.create(name='3', region='c', config=config, project=p3, schedule=s)

        ua.projects.add(p1, p2)
        ub.projects.add(p1)

        perm = Permission.objects.create(name=Perms.READ_ANY_PROJECT)
        role = Role.objects.create(name='All Seeing')
        role.permissions.add(perm)
        ub.roles.add(role)

        # user A can only see VMs in his projects
        self.assertTrue(self.client.login(username='a', password='p'))
        response = self.client.get(reverse('awsvm-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({avm1.id, avm2.id}, {x['id'] for x in items})

        response = self.client.get(reverse('awsvm-detail', args=[avm1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(reverse('awsvm-detail', args=[avm3.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.get(reverse('awsvm-detail', args=[avm1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({avm1.id}, {response.data['id']})

        # filter by .name field
        response = self.client.get(reverse('awsvm-list') +
                '?name=' + urllib.parse.quote(avm1.name))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.data['results']
        self.assertEqual({avm1.id}, {x['id'] for x in items})

        # user B can see all VMs in all projects
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
        response = self.client.delete(reverse('awsvm-detail', args=[item['id']]))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # can't create
        del item['id']
        response = self.client.post(reverse('awsvm-list'),
                item, format='json')
        self.assertEqual(response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED)

class SetExpirationTests(TestCase):
    def test_FirewallRule_perms_and_not_found(self):
        """
        Test user permissions and ‘not found’ for FirewallRule Expirations.
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prv = Provider.objects.create(name='My Provider', vpc_id='dummy')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))
        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)

        vm = VM.objects.create(name="my-vm", config=config, project=prj, schedule=s)
        fw_rule = FirewallRule.objects.create(vm=vm,
                ip_protocol=FirewallRule.PROTO_TCP,
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
    def test_perms_and_not_found(self):
        """
        Test user permissions and ‘not found’ (for VMs when creating,
        for rules when deleting).
        """
        u = util.create_vimma_user('a', 'a@example.com', 'pass')
        self.assertTrue(self.client.login(username='a', password='pass'))
        prj = Project.objects.create(name='prj', email='prj@x.com')

        prv = Provider.objects.create(name='My Provider', vpc_id='dummy')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [False]]))

        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)
        vm = VM.objects.create(config=config, project=prj, schedule=s)

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

class ExpirationTests(TestCase):
    def test_api_permissions_vm(self):
        """
        Users can read Expiration and Expiration objects
        for the vms in one of their projects.

        The API is read-only.
        """
        uF = util.create_vimma_user('Fry', 'fry@pe.com', '-')
        uH = util.create_vimma_user('Hubert', 'hubert@pe.com', '-')
        uB = util.create_vimma_user('Bender', 'bender@pe.com', '-')

        tz = TimeZone.objects.create(name='Europe/Helsinki')
        s = Schedule.objects.create(name='s', timezone=tz,
                matrix=json.dumps(7 * [48 * [True]]))

        prv = Provider.objects.create(name='My Prov')
        config = Config.objects.create(name='My Config', default_schedule=s, provider=prv)

        pD = Project.objects.create(name='Prj Delivery', email='p-d@pe.com')
        pS = Project.objects.create(name='Prj Smelloscope', email='p-s@pe.com')

        vmD = VM.objects.create(config=config, project=pD, schedule=s)
        vmS = VM.objects.create(config=config, project=pS, schedule=s)

        uF.projects.add(pD)
        uH.projects.add(pD, pS)

        perm = Permission.objects.create(name=Perms.READ_ANY_PROJECT)
        role = Role.objects.create(name='All Seeing')
        role.permissions.add(perm)
        uB.roles.add(role)

        now = datetime.datetime.utcnow().replace(tzinfo=utc)

        vm_expD = Expiration.objects.create(expires_at=now, vm=vmD)
        vm_expS = Expiration.objects.create(expires_at=now, vm=vmS)

        fw_rule_D = FirewallRule.objects.create(vm=vmD, from_port=80, to_port=80, cidr_ip="10.10.0.0/24", ip_protocol=FirewallRule.PROTO_TCP)
        fw_rule_S = FirewallRule.objects.create(vm=vmS, from_port=80, to_port=81, cidr_ip="11.11.1.1/24", ip_protocol=FirewallRule.PROTO_TCP)

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

        # filter Expiration by .vm field
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

class FirewallRule_FirewallRule_Tests(TestCase):

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
            FirewallRule(from_port=80, to_port=80, cidr_ip="10.10.0.0/24", ip_protocol=FirewallRule.PROTO_TCP),
            FirewallRule(from_port=80, to_port=80, cidr_ip="10.10.0.1/32", ip_protocol=FirewallRule.PROTO_TCP),
            FirewallRule(from_port=80, to_port=80, cidr_ip="1.2.3.4/27", ip_protocol=FirewallRule.PROTO_TCP),
            FirewallRule(from_port=80, to_port=80, cidr_ip="192.168.0.0/16", ip_protocol=FirewallRule.PROTO_TCP),
            FirewallRule(from_port=80, to_port=80, cidr_ip="192.168.0.0/23", ip_protocol=FirewallRule.PROTO_TCP),
        ]

        special = [
            FirewallRule(from_port=80, to_port=80, cidr_ip="10.10.0.0/23", ip_protocol=FirewallRule.PROTO_TCP),
            FirewallRule(from_port=80, to_port=80, cidr_ip="0.0.0.0/0", ip_protocol=FirewallRule.PROTO_TCP),
            FirewallRule(from_port=80, to_port=80, cidr_ip="10.10.0.0/8", ip_protocol=FirewallRule.PROTO_TCP),
            FirewallRule(from_port=80, to_port=80, cidr_ip="192.168.0.0/15", ip_protocol=FirewallRule.PROTO_TCP),
        ]

        for rule in non_special:
            self.assertFalse(rule.is_special())

        for rule in special:
            self.assertTrue(rule.is_special())

    def test_api_permissions(self):
        """
        Users can read FirewallRule and FirewallRule objects
        for VMs in one of their projects.
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

        fw_ruleD = FirewallRule.objects.create(vm=vmD,
                ip_protocol=FirewallRule.PROTO_TCP,
                from_port=80, to_port=80, cidr_ip='1.2.3.4/0')
        fw_ruleS = FirewallRule.objects.create(vm=vmS,
                ip_protocol=FirewallRule.PROTO_TCP,
                from_port=80, to_port=80, cidr_ip='1.2.3.4/0')

        uF.projects.add(pD)
        uH.projects.add(pD, pS)

        perm = Permission.objects.create(name=Perms.OMNIPOTENT)
        role = Role.objects.create(name='all powerful')
        role.permissions.add(perm)
        uB.roles.add(role)

        def check_user_sees(username, aws_fw_id_set):
            self.assertTrue(self.client.login(username=username, password='-'))
            for view_root, id_set in (
                    ('awsfirewallrule', aws_fw_id_set),
                    ):
                response = self.client.get(reverse(view_root + '-list'))
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                items = response.data['results']
                self.assertEqual({x['id'] for x in items}, id_set)

        check_user_sees('Fry', {fw_ruleD.id, fw_ruleD.id})
        check_user_sees('Hubert', {fw_ruleD.id, fw_ruleS.id})
        check_user_sees('Bender', {fw_ruleD.id, fw_ruleS.id})

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

        # filter FirewallRule by .firewallrule field
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
