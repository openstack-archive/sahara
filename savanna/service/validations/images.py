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

image_register_schema = {
    "type": "object",
    "properties": {
        "username": {
            "type": "string",
        },
        "description": {
            "type": "string",
        },
    },
    "additionalProperties": False,
    "required": ["username"]
}

image_tags_schema = {
    "type": "object",
    "properties": {
        "tags": {
            "type": "array",
            "items": {
                "type": "string",
                "format": "valid_tag"
            },
        },
    },
    "additionalProperties": False,
    "required": ["tags"]
}


def check_image_register(data, **kwargs):
    pass


def check_tags(data, **kwargs):
    pass
