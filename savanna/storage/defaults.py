# Copyright (c) 2013 Mirantis Inc.
#
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

from savanna.storage.storage import create_node_type, \
    create_node_template, create_node_process
from savanna.openstack.common import log as logging

LOG = logging.getLogger(__name__)


def setup_defaults(reset_db=False, gen_templates=False):
    nt_jt_nn = None
    nt_jt = None
    nt_nn = None
    nt_tt_dn = None

    if reset_db:
        # setup default processes
        p_jt = create_node_process('job_tracker',
                                   [('heap_size', True, None),
                                    ('mapred.job.tracker.handler.count',
                                     False, None)])
        p_nn = create_node_process('name_node',
                                   [('heap_size', True, None),
                                    ('dfs.namenode.handler.count',
                                     False, None),
                                    ('dfs.block.size', False, None),
                                    ('dfs.replication', False, None)])
        p_tt = create_node_process('task_tracker',
                                   [('heap_size', True, None),
                                    ('mapred.child.java.opts', False, None),
                                    ('mapred.map.tasks', False, None),
                                    ('mapred.tasktracker.map.tasks.maximum',
                                     False, None),
                                    ('mapred.reduce.tasks', False, None),
                                    ('mapred.tasktracker.reduce.tasks.maximum',
                                     False, None)])

        p_dn = create_node_process('data_node',
                                   [('heap_size', True, None),
                                    ('dfs.datanode.max.xcievers', False, None),
                                    ('dfs.block.size', False, None),
                                    ('dfs.replication', False, None),
                                    ('dfs.datanode.handler.count',
                                     False, None)])

        for p in [p_jt, p_nn, p_tt, p_dn]:
            LOG.info('New NodeProcess: \'%s\'', p.name)

        # setup default node types
        nt_jt_nn = create_node_type('JT+NN', [p_jt, p_nn])
        nt_jt = create_node_type('JT', [p_jt])
        nt_nn = create_node_type('NN', [p_nn])
        nt_tt_dn = create_node_type('TT+DN', [p_tt, p_dn])

        for nt in [nt_jt_nn, nt_jt, nt_nn, nt_tt_dn]:
            LOG.info('New NodeType: \'%s\' %s',
                     nt.name, [p.name.__str__() for p in nt.processes])

    if gen_templates:
        _generate_templates(nt_jt_nn, nt_jt, nt_nn, nt_tt_dn)

    LOG.info('All defaults has been inserted')


def _generate_templates(nt_jt_nn, nt_jt, nt_nn, nt_tt_dn):
    jt_nn_small = create_node_template('jt_nn.small', nt_jt_nn.id, 'm1.small',
                                       {
                                           'job_tracker': {
                                               'heap_size': '896'
                                           },
                                           'name_node': {
                                               'heap_size': '896'
                                           }
                                       })
    jt_nn_medium = create_node_template('jt_nn.medium', nt_jt_nn.id,
                                        'm1.medium',
                                        {
                                            'job_tracker': {
                                                'heap_size': '1792'
                                            },
                                            'name_node': {
                                                'heap_size': '1792'
                                            }
                                        })
    tt_dn_small = create_node_template('tt_dn.small', nt_tt_dn.id, 'm1.small',
                                       {
                                           'task_tracker': {
                                               'heap_size': '896'
                                           },
                                           'data_node': {
                                               'heap_size': '896'
                                           }
                                       })
    tt_dn_medium = create_node_template('tt_dn.medium', nt_tt_dn.id,
                                        'm1.medium',
                                        {
                                            'task_tracker': {
                                                'heap_size': '1792'
                                            },
                                            'data_node': {
                                                'heap_size': '1792'
                                            }
                                        })

    for tmpl in [jt_nn_small, jt_nn_medium, tt_dn_small, tt_dn_medium]:
        LOG.info('New NodeTemplate: \'%s\' %s', tmpl.name, tmpl.flavor_id)
