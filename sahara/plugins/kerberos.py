# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils

from sahara import conductor as cond
from sahara import context
from sahara import exceptions as exc
from sahara.i18n import _
from sahara.plugins import provisioning as base
from sahara.plugins import utils as pl_utils
from sahara.service.castellan import utils as key_manager
from sahara.utils import cluster as cl_utils
from sahara.utils import cluster_progress_ops as cpo
from sahara.utils import files


conductor = cond.API
LOG = logging.getLogger(__name__)
CONF = cfg.CONF
POLICY_FILES_DIR = '/tmp/UnlimitedPolicy'


class KDCInstallationFailed(exc.SaharaException):
    code = 'KDC_INSTALL_FAILED'
    message_template = _('KDC installation failed by reason: {reason}')

    def __init__(self, reason):
        message = self.message_template.format(reason=reason)
        super(KDCInstallationFailed, self).__init__(message)


def _config(**kwargs):
    return base.Config(
        applicable_target='Kerberos', priority=1,
        is_optional=True, scope='cluster', **kwargs)


enable_kerberos = _config(
    name='Enable Kerberos Security', config_type='bool',
    default_value=False)
use_existing_kdc = _config(
    name='Existing KDC', config_type='bool',
    default_value=False)
kdc_server_ip = _config(
    name='Server IP of KDC', config_type='string',
    default_value='192.168.0.1',
    description=_('Server IP of KDC server when using existing KDC'))
realm_name = _config(
    name='Realm Name', config_type='string',
    default_value='SAHARA-KDC',
    description=_('The name of realm to be used'))
admin_principal = _config(
    name='Admin principal', config_type='string',
    default_value='sahara/admin',
    description=_('Admin principal for existing KDC server'))
admin_password = _config(
    name='Admin password', config_type='string', default_value='')
policy_url = _config(
    name="JCE libraries", config_type='string',
    default_value=('https://tarballs.openstack.org/sahara-extra/dist/'
                   'common-artifacts/'),
    description=_('Java Cryptography Extension (JCE) '
                  'Unlimited Strength Jurisdiction Policy Files location')
)


def get_config_list():
    return [
        enable_kerberos,
        use_existing_kdc,
        kdc_server_ip,
        realm_name,
        admin_principal,
        admin_password,
        policy_url,
    ]


def get_kdc_host(cluster, server):
    if using_existing_kdc(cluster):
        return "server.%s" % CONF.node_domain
    return server.fqdn()


def is_kerberos_security_enabled(cluster):
    return pl_utils.get_config_value_or_default(
        cluster=cluster, config=enable_kerberos)


def using_existing_kdc(cluster):
    return pl_utils.get_config_value_or_default(
        cluster=cluster, config=use_existing_kdc)


def get_kdc_server_ip(cluster):
    return pl_utils.get_config_value_or_default(
        cluster=cluster, config=kdc_server_ip)


def get_realm_name(cluster):
    return pl_utils.get_config_value_or_default(
        cluster=cluster, config=realm_name)


def get_admin_principal(cluster):
    return pl_utils.get_config_value_or_default(
        cluster=cluster, config=admin_principal)


def get_admin_password(cluster):
    # TODO(vgridnev): support in follow-up improved secret storage for
    # configs
    return pl_utils.get_config_value_or_default(
        cluster=cluster, config=admin_password)


def get_policy_url(cluster):
    return pl_utils.get_config_value_or_default(
        cluster=cluster, config=policy_url)


def setup_clients(cluster, server=None, instances=None):
    if not instances:
        instances = cl_utils.get_instances(cluster)
    server_ip = None
    cpo.add_provisioning_step(
        cluster.id, _("Setting Up Kerberos clients"), len(instances))

    if not server:
        server_ip = get_kdc_server_ip(cluster)
    with context.ThreadGroup() as tg:
        for instance in instances:
            tg.spawn('setup-client-%s' % instance.instance_name,
                     _setup_client_node, cluster, instance,
                     server, server_ip)


def prepare_policy_files(cluster, instances=None):
    if instances is None:
        instances = pl_utils.get_instances(cluster)

    remote_url = get_policy_url(cluster)
    cpo.add_provisioning_step(
        cluster.id, _("Preparing policy files"), len(instances))
    with context.ThreadGroup() as tg:
        for inst in instances:
            tg.spawn(
                'policy-files',
                _prepare_policy_files, inst, remote_url)


def deploy_infrastructure(cluster, server=None):
    if not is_kerberos_security_enabled(cluster):
        LOG.debug("Kerberos security disabled for cluster")
        return
    if not using_existing_kdc(cluster):
        deploy_kdc_server(cluster, server)

    setup_clients(cluster, server)


def _execute_script(client, script):
    with client.remote() as remote:
        script_path = '/tmp/%s' % uuidutils.generate_uuid()[:8]
        remote.write_file_to(script_path, script)
        remote.execute_command('chmod +x %s' % script_path)
        remote.execute_command('bash %s' % script_path)
        remote.execute_command('rm -rf %s' % script_path)


def _get_kdc_config(cluster, os):
    if os == "ubuntu":
        data = files.get_file_text('plugins/resources/kdc_conf')
    else:
        data = files.get_file_text('plugins/resources/kdc_conf_redhat')
    return data % {
        'realm_name': get_realm_name(cluster)
    }


def _get_krb5_config(cluster, server_fqdn):
    data = files.get_file_text('plugins/resources/krb5_config')
    return data % {
        'realm_name': get_realm_name(cluster),
        'server': server_fqdn,
        'node_domain': CONF.node_domain,
    }


def _get_short_uuid():
    return "%s%s" % (uuidutils.generate_uuid()[:8],
                     uuidutils.generate_uuid()[:8])


def get_server_password(cluster):
    if using_existing_kdc(cluster):
        return get_admin_password(cluster)
    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, cluster)
    extra = cluster.extra.to_dict() if cluster.extra else {}
    passwd_key = 'admin-passwd-kdc'
    if passwd_key not in extra:
        passwd = _get_short_uuid()
        key_id = key_manager.store_secret(passwd, ctx)
        extra[passwd_key] = key_id
        cluster = conductor.cluster_update(ctx, cluster, {'extra': extra})
    passwd = key_manager.get_secret(extra.get(passwd_key), ctx)
    return passwd


def _get_configs_dir(os):
    if os == "ubuntu":
        return "/etc/krb5kdc"
    return "/var/kerberos/krb5kdc"


def _get_kdc_conf_path(os):
    return "%s/kdc.conf" % _get_configs_dir(os)


def _get_realm_create_command(os):
    if os == 'ubuntu':
        return "krb5_newrealm"
    return "kdb5_util create -s"


def _get_acl_config_path(os):
    return "%s/kadm5.acl" % _get_configs_dir(os)


def _get_acl_config():
    return "*/admin * "


def _get_start_command(os, version):
    if os == "ubuntu":
        return ("sudo service krb5-kdc restart && "
                "sudo service krb5-admin-server restart")

    if version.startswith('6'):
        return ("sudo /etc/rc.d/init.d/krb5kdc start "
                "&& sudo /etc/rc.d/init.d/kadmin start")

    if version.startswith('7'):
        return ("sudo systemctl start krb5kdc &&"
                "sudo systemctl start kadmin")

    raise ValueError(
        _("Unable to get kdc server start command"))


def _get_server_installation_script(cluster, server_fqdn, os, version):
    data = files.get_file_text(
        'plugins/resources/mit-kdc-server-init.sh.template')
    return data % {
        'kdc_conf': _get_kdc_config(cluster, os),
        'kdc_conf_path': _get_kdc_conf_path(os),
        'acl_conf': _get_acl_config(),
        'acl_conf_path': _get_acl_config_path(os),
        'realm_create': _get_realm_create_command(os),
        'krb5_conf': _get_krb5_config(cluster, server_fqdn),
        'admin_principal': get_admin_principal(cluster),
        'password': get_server_password(cluster),
        'os': os,
        'start_command': _get_start_command(os, version),
    }


@cpo.event_wrapper(True, step=_("Deploy KDC server"), param=('cluster', 0))
def deploy_kdc_server(cluster, server):
    with server.remote() as r:
        os = r.get_os_distrib()
        version = r.get_os_version()
    script = _get_server_installation_script(
        cluster, server.fqdn(), os, version)
    _execute_script(server, script)


def _push_etc_hosts_entry(client, entry):
    with client.remote() as r:
        r.execute_command('echo %s | sudo tee -a /etc/hosts' % entry)


def _get_client_installation_script(cluster, server_fqdn, os):
    data = files.get_file_text('plugins/resources/krb-client-init.sh.template')
    return data % {
        'os': os,
        'krb5_conf': _get_krb5_config(cluster, server_fqdn),
    }


@cpo.event_wrapper(True, param=('client', 1))
def _setup_client_node(cluster, client, server=None, server_ip=None):
    if server:
        server_fqdn = server.fqdn()
    elif server_ip:
        server_fqdn = "server." % CONF.node_domain
        _push_etc_hosts_entry(
            client, "%s %s %s" % (server_ip, server_fqdn, server))
    else:
        raise KDCInstallationFailed(_('Server or server ip are not provided'))
    with client.remote() as r:
        os = r.get_os_distrib()
    script = _get_client_installation_script(cluster, server_fqdn, os)
    _execute_script(client, script)


@cpo.event_wrapper(True)
def _prepare_policy_files(instance, remote_url):
    with instance.remote() as r:
        cmd = 'cut -f2 -d \"=\" /etc/profile.d/99-java.sh | head -1'
        exit_code, java_home = r.execute_command(cmd)
        java_home = java_home.strip()
        results = [
            r.execute_command(
                "ls %s/local_policy.jar" % POLICY_FILES_DIR,
                raise_when_error=False)[0] != 0,
            r.execute_command(
                "ls %s/US_export_policy.jar" % POLICY_FILES_DIR,
                raise_when_error=False)[0] != 0
        ]
        # a least one exit code is not zero
        if any(results):
            r.execute_command('mkdir %s' % POLICY_FILES_DIR)
            r.execute_command(
                "sudo curl %s/local_policy.jar -o %s/local_policy.jar" % (
                    remote_url, POLICY_FILES_DIR))
            r.execute_command(
                "sudo curl %s/US_export_policy.jar -o "
                "%s/US_export_policy.jar" % (
                    remote_url, POLICY_FILES_DIR))
        r.execute_command(
            'sudo cp %s/*.jar %s/lib/security/'
            % (POLICY_FILES_DIR, java_home))


def _get_script_for_user_creation(cluster, instance, user):
    data = files.get_file_text(
        'plugins/resources/create-principal-keytab')
    cron_file = files.get_file_text('plugins/resources/cron-file')
    cron_script = files.get_file_text('plugins/resources/cron-script')
    data = data % {
        'user': user, 'admin_principal': get_admin_principal(cluster),
        'admin_password': get_server_password(cluster),
        'principal': "%s/sahara-%s@%s" % (
            user, instance.fqdn(), get_realm_name(cluster)),
        'keytab': '%s-sahara-%s.keytab' % (user, instance.fqdn())
    }
    cron_script_location = '/tmp/sahara-kerberos/%s.sh' % _get_short_uuid()
    cron_file = cron_file % {'refresher': cron_script_location, 'user': user}
    cron_script = cron_script % {
        'principal': "%s/sahara-%s@%s" % (
            user, instance.fqdn(), get_realm_name(cluster)),
        'keytab': '%s-sahara-%s.keytab' % (user, instance.fqdn()),
        'user': user,
    }
    return data, cron_file, cron_script, cron_script_location


def _create_keytabs_for_user(instance, user):
    script, cron, cron_script, cs_location = _get_script_for_user_creation(
        instance.cluster, instance, user)
    _execute_script(instance, script)
    # setting up refresher
    with instance.remote() as r:
        tmp_location = '/tmp/%s' % _get_short_uuid()
        r.write_file_to(tmp_location, cron_script, run_as_root=True)
        r.execute_command(
            "cat {0} | sudo tee {1} "
            "&& rm -rf {0} && sudo chmod +x {1}".format(
                tmp_location, cs_location))
        r.execute_command(
            'echo "%s" | sudo tee /etc/cron.d/%s.cron' % (
                cron, _get_short_uuid()))
        # executing script
        r.execute_command('sudo bash %s' % cs_location)


@cpo.event_wrapper(
    True, step=_('Setting up keytabs for users'), param=('cluster', 0))
def create_keytabs_for_map(cluster, mapper):
    # cluster parameter is used by event log feature
    with context.ThreadGroup() as tg:
        for user, instances in mapper.items():
            for instance in instances:
                tg.spawn(
                    'create-keytabs', _create_keytabs_for_user,
                    instance, user)
