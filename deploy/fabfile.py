import datetime
from fabric.api import task, env
from fabric.context_managers import cd, prefix, settings, shell_env
from fabric.operations import sudo
import os, os.path


env.hosts = env.hosts or ['vimma2.futurice.com']
# SSH into the remote host as the '-u' cmd line arg (or your local username),
# which can sudo (stop&start services), then change to vimma_user who owns the
# source code.
vimma_user = 'vimma2'

stamp = datetime.datetime.utcnow().isoformat().replace(':', '').replace('-', '')
stamp = stamp[:stamp.rfind('.')] + 'Z'
home_dir = '/home/vimma2'
config_dir = os.path.join(home_dir, 'config')
repo_link = os.path.join(home_dir, 'vimma2')
env_link = os.path.join(home_dir, 'env')
repo_dir = os.path.join(home_dir, 'vimma2-' + stamp)
env_dir = os.path.join(home_dir, 'env-' + stamp)

git_clone_url = 'https://github.com/futurice/vimma2.git'


@task
def stop_services():
    sudo('service supervisor stop')
    sudo('service apache2 stop')


@task
def start_services():
    sudo('service supervisor start')
    sudo('service apache2 start')


def clone_repository():
    with settings(sudo_user=vimma_user):
        sudo('git clone ' + git_clone_url + ' ' + repo_dir)


def make_env():
    with settings(sudo_user=vimma_user):
        sudo('virtualenv -p python3 ' + env_dir)
        with prefix('source ' + env_dir + '/bin/activate'):
            sudo('pip install -r ' + repo_dir + '/req.txt')


def run_tests():
    with settings(cd(home_dir), sudo_user=vimma_user):
        with prefix('source ' + env_dir + '/bin/activate'):
            with shell_env(PYTHONPATH=config_dir):
                sudo(repo_dir + '/vimmasite/manage.py migrate')
                sudo(repo_dir + '/vimmasite/manage.py test vimma ' +
                        '--settings=test_settings --noinput')
                sudo(repo_dir + '/vimmasite/manage.py create_vimma_permissions')


def prepare_repository():
    """
    Collect static files, bower install.
    """
    with settings(cd(home_dir), sudo_user=vimma_user):
        # otherwise bower tries to access ~/.config for the original SSH user
        with shell_env(HOME=home_dir):
            sudo(repo_dir + '/scripts/bower-reset.py')
        with prefix('source ' + env_dir + '/bin/activate'):
            with shell_env(PYTHONPATH=config_dir):
                sudo('mkdir -p ' + repo_dir + '/vimmasite/static')
                sudo(repo_dir + '/vimmasite/manage.py collectstatic ' +
                        '--noinput --clear')


def move_symlinks():
    with settings(sudo_user=vimma_user):
        sudo('rm -f ' + env_link + ' ' + repo_link)
        sudo('ln -s ' + env_dir + ' ' + env_link)
        sudo('ln -s ' + repo_dir + ' ' + repo_link)


@task
def deploy():
    stop_services()
    clone_repository()
    make_env()
    prepare_repository()
    run_tests()
    move_symlinks()
    start_services()
