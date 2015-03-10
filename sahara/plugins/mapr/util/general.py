# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import uuid

from sahara.conductor import objects
from sahara import context
import sahara.utils.files as files


def unique_list(iterable, mapper=lambda i: i):
    result = []

    for item in iterable:
        value = mapper(item)
        if value not in result:
            result.append(value)

    return result


def _run_as(user, command):
    if not user:
        return command
    return 'sudo -u %(user)s %(command)s' % {'user': user, 'command': command}


def unique_file_name(base='/tmp'):
    return '%(base)s/%(uuid)s' % {'base': base, 'uuid': uuid.uuid4()}


def remove(instance, path, recursive=True, run_as=None):
    with instance.remote() as r:
        args = {'recursive': '-r' if recursive else '', 'path': path}
        r.execute_command(_run_as(run_as, 'rm %(recursive)s %(path)s' % args))


def create_archive(instance, path, archive=None, run_as=None):
    if not archive:
        archive = unique_file_name('/tmp')
    args = {'archive': archive, 'path': path}
    tar = 'tar cf %(archive)s -C %(path)s .' % args
    with instance.remote() as r:
        r.execute_command(_run_as(run_as, tar))
    return archive


def unpack_archive(instance, src, dest, cleanup=False, run_as=None):
    with instance.remote() as r:
        r.execute_command(_run_as(run_as, 'mkdir -p %s' % dest))
        untar = 'tar xf %(src)s -C %(dest)s' % {'src': src, 'dest': dest}
        r.execute_command(_run_as(run_as, untar))
        if cleanup:
            r.execute_command(_run_as(run_as, 'rm -r %s' % src))


def copy_file(s_path, s_instance, d_path, d_instance, run_as=None):
    with s_instance.remote() as sr:
        data = sr.read_file_from(s_path, run_as_root=(run_as == 'root'))
    with d_instance.remote() as dr:
        dr.write_file_to(d_path, data, run_as_root=(run_as == 'root'))


def copy_dir(s_path, s_instance, d_path, d_instance, run_as=None):
    s_path = create_archive(s_instance, s_path, run_as=run_as)
    tmp_path = unique_file_name('/tmp')
    copy_file(s_path, s_instance, tmp_path, d_instance, run_as)
    unpack_archive(d_instance, tmp_path, d_path, True, run_as)
    remove(s_instance, s_path, True, run_as)


def copy(s_path, s_instance, d_path, d_instance, run_as=None):
    if is_directory(s_instance, s_path):
        copy_dir(s_path, s_instance, d_path, d_instance, run_as)
    else:
        copy_file(s_path, s_instance, d_path, d_instance, run_as)


def run_script(instance, script, run_as=None, *args, **kwargs):
    with instance.remote() as r:
        path = '/tmp/%s.sh' % uuid.uuid4()
        script = files.get_file_text(script) % kwargs
        r.write_file_to(path, script, run_as_root=(run_as == 'root'))
        r.execute_command(_run_as(run_as, 'chmod +x %s' % path))
        r.execute_command(_run_as(run_as, '%s %s' % (path, ' '.join(args))))
        # FIXME(aosadchyi): reuse existing remote
        remove(instance, path, run_as=run_as)


def execute_on_instances(instances, function, *args, **kwargs):
    with context.ThreadGroup() as tg:
        for instance in instances:
            t_name = '%s-execution' % function.__name__
            tg.spawn(t_name, function, instance, *args, **kwargs)


def _replace(args, position, value):
    return args[:position] + (value,) + args[position + 1:]


def remote_command(position):
    def wrap(func):
        def wrapped(*args, **kwargs):
            target = args[position]
            if isinstance(target, objects.Instance):
                with target.remote() as remote:
                    return func(*_replace(args, position, remote), **kwargs)
            return func(*args, **kwargs)

        return wrapped

    return wrap


def execute_command(instances, command, run_as=None):
    def _execute_command(instance):
        with instance.remote() as remote:
            remote.execute_command(_run_as(run_as, command), timeout=1800)

    execute_on_instances(instances, _execute_command)


@remote_command(0)
def is_directory(remote, path):
    command = '[ -d %s ]' % path
    ec = remote.execute_command(command, True, raise_when_error=False)[0]
    return not ec


@remote_command(0)
def chown(remote, owner, path):
    args = {'owner': owner, 'path': path}
    remote.execute_command('chown -R %(owner)s %(path)s' % args, True)


@remote_command(0)
def chmod(remote, mode, path):
    args = {'mode': mode, 'path': path}
    remote.execute_command('chmod -R %(mode)s %(path)s' % args, True)


@remote_command(0)
def mkdir(remote, path, mode=None, owner=''):
    args = {'mode': '-m %s' % mode if mode else '', 'path': path}
    remote.execute_command('mkdir -p %(mode)s %(path)s' % args, bool(owner))
    if owner:
        chown(remote, owner, path)


@remote_command(0)
def write_file(remote, path, data, mode=None, owner=''):
    remote.write_file_to(path, data, run_as_root=bool(owner))
    if mode:
        chmod(remote, mode, path)
    if owner:
        chown(remote, owner, path)


@remote_command(0)
def install_ssh_key(remote, user, private_key, public_key):
    ssh_dir = '/home/%s/.ssh' % user
    owner = '%s:%s' % (user, user)
    if not is_directory(remote, ssh_dir):
        mkdir(remote, ssh_dir, 700, owner)
    write_file(remote, '%s/id_rsa.pub' % ssh_dir, public_key, 644, owner)
    write_file(remote, '%s/id_rsa' % ssh_dir, private_key, 600, owner)


@remote_command(0)
def authorize_key(remote, user, public_key):
    authorized_keys = '/home/%s/.ssh/authorized_keys' % user
    remote.append_to_file(authorized_keys, public_key, run_as_root=True)
