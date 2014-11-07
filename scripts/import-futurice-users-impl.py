#! /usr/bin/env python3

# https://docs.djangoproject.com/en/1.7/releases/1.7/#standalone-scripts
import django
django.setup()

import argparse
from django.contrib.auth.models import User
from django.db.models import Q
import json
import urllib.request

from secrets import FUM_API_TOKEN
from vimma.models import Permission, Role, Project
from vimma.perms import Perms
import vimma.util


IT_TEAM_ROLE_NAME = 'IT Team'


def parse_args():
    p = argparse.ArgumentParser(description='''The implementation of
        import-futurice-users.py. Run that script so it sets PATHs and
        environment variables.''')
    return p.parse_args()


def get_api_all(url, log_label='results'):
    """
    Get url and all subsequent API pages.
    """
    results = []
    while url is not None:
        req = urllib.request.Request(url,
                headers={'Authorization': 'Token ' + FUM_API_TOKEN})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        results.extend(data['results'])
        print('got {}/{} {}'.format(len(results), data['count'], log_label),
                flush=True)
        url = data['next']
    return results


def sync_users():
    def valid_user(u):
        return all(u[field] for field in
                ('username', 'email', 'first_name', 'last_name'))

    for u in filter(valid_user,
            get_api_all('https://api.fum.futurice.com/users/', 'users')):
        try:
            vimma_user = User.objects.get(username=u['username'])
            vimma_user.email = u['email']
            vimma_user.first_name = u['first_name']
            vimma_user.last_name = u['last_name']
            vimma_user.save()
        except User.DoesNotExist:
            vimma_user = vimma.util.create_vimma_user(
                    u['username'], u['email'], '',
                    first_name=u['first_name'], last_name=u['last_name'])


def sync_projects():
    for p in filter(lambda p: p['email'],
            get_api_all('https://api.fum.futurice.com/projects/', 'projects')):
        try:
            vimma_prj = Project.objects.get(email=p['email'])
            vimma_prj.name = p['name']
            vimma_prj.save()
        except Project.DoesNotExist:
            vimma_prj = Project.objects.create(name=p['name'], email=p['email'])

        fum_members = set(p['users'])
        vimma_members = {prof.user.username for prof in
                vimma_prj.profile_set.filter()}

        for u in vimma_members.difference(fum_members):
            prof = User.objects.get(username=u).profile
            vimma_prj.profile_set.remove(prof)

        for u in fum_members.difference(vimma_members):
            try:
                prof = User.objects.get(username=u).profile
                vimma_prj.profile_set.add(prof)
            except User.DoesNotExist:
                pass


def sync_admin_users():
    """
    Give some users Permissions or access to the Django admin site.
    """
    fum_groups = get_api_all('https://api.fum.futurice.com/groups/', 'groups')
    fum_admins = set()
    for g in filter(lambda g: g['name'] in {'it'}, fum_groups):
        fum_admins.update(g['users'])

    vimma_maybe_admins = {u.username for u in
            User.objects.filter(Q(is_staff=True) | Q(is_superuser=True))}
    for u in vimma_maybe_admins.difference(fum_admins):
        user = User.objects.get(username=u)
        user.is_staff = False
        user.is_superuser = False
        user.save()

    vimma_full_admins = {u.username for u in
            User.objects.filter(is_staff=True, is_superuser=True)}
    for u in fum_admins.difference(vimma_full_admins):
        try:
            user = User.objects.get(username=u)
            user.is_staff = True
            user.is_superuser = True
            user.save()
        except User.DoesNotExist:
            pass

    fum_it_team = set()
    for g in filter(lambda g: g['name'] == 'it', fum_groups):
        fum_it_team.update(g['users'])
    try:
        it_team_role = Role.objects.get(name=IT_TEAM_ROLE_NAME)
    except Role.DoesNotExist:
        it_team_role = Role.objects.create(name=IT_TEAM_ROLE_NAME)
        it_team_role.full_clean()
    for perm_name in (Perms.EDIT_SCHEDULE,):
        try:
            perm = Permission.objects.get(name=perm_name)
        except Permission.DoesNotExist:
            print('creating permission', perm_name)
            perm = Permission.objects.create(name=perm_name)
            perm.full_clean()
        it_team_role.permissions.add(perm)
    for u in fum_it_team:
        try:
            User.objects.get(username=u).profile.roles.add(it_team_role)
        except User.DoesNotExist:
            pass


if __name__ == '__main__':
    args = parse_args()

    sync_users()
    sync_projects()
    sync_admin_users()
