#! /usr/bin/env python3

# https://docs.djangoproject.com/en/1.7/releases/1.7/#standalone-scripts
import django
django.setup()

import argparse
from django.contrib.auth.models import User
import json
import urllib.request

from secrets import FUM_API_TOKEN
import vimma.util


def parse_args():
    p = argparse.ArgumentParser(description='''The implementation of
        import-futurice-users.py. Run that script so it sets PATHs and
        environment variables.''')
    return p.parse_args()


def get_fum_users():
    users = []
    url = 'https://api.fum.futurice.com/users/'
    while url is not None:
        req = urllib.request.Request(url,
                headers={'Authorization': 'Token ' + FUM_API_TOKEN})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        users.extend(data['results'])
        print('got {} users so far'.format(len(users)), flush=True)
        url = data['next']
    return users


if __name__ == '__main__':
    args = parse_args()

    def valid_user(u):
        return all(u[field] for field in
                ('username', 'email', 'first_name', 'last_name'))

    for u in filter(valid_user, get_fum_users()):
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
