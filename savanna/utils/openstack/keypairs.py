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

from novaclient.v1_1 import keypairs


# TODO(slukjanov): remove this tweak when fix for 1223934 will be released
class SavannaKeypair(keypairs.Keypair):
    def _add_details(self, info):
        dico = 'keypair' in info and \
            info['keypair'] or info
        for (k, v) in dico.items():
            if k == 'id':
                continue
            setattr(self, k, v)


class SavannaKeypairManager(keypairs.KeypairManager):
    resource_class = SavannaKeypair
