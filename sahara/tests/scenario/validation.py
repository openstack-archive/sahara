# Copyright (c) 2015 Mirantis Inc.
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

import re

import jsonschema
import rfc3986


SCHEMA = {
    "type": "object",
    "properties": {
        "concurrency": {
            "type": "integer",
            "minimum": 1
        },
        "credentials": {
            "type": "object",
            "properties": {
                "os_username": {
                    "type": "string",
                    "minLength": 1
                },
                "os_password": {
                    "type": "string",
                    "minLength": 1
                },
                "os_tenant": {
                    "type": "string",
                    "minLength": 1
                },
                "os_auth_url": {
                    "type": "string",
                    "format": "uri"
                },
                "sahara_service_type": {
                    "type": "string",
                    "minLength": 1
                },
                "sahara_url": {
                    "type": "string",
                    "format": "uri"
                },
                "ssl_verify": {
                    "type": "boolean"
                },
                "ssl_cert": {
                    "type": "string",
                    "minLength": 1
                }
            },
            "additionalProperties": False
        },
        "network": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["neutron", "nova-network"]
                },
                "auto_assignment_floating_ip": {
                    "type": "boolean"
                },
                "public_network": {
                    "type": "string",
                    "minLength": 1
                },
                "private_network": {
                    "type": "string",
                    "minLength": 1
                }
            },
            "additionalProperties": False
        },
        "clusters": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "existing_cluster": {
                        "type": "string",
                        "minLength": 1
                    },
                    "key_name": {
                        "type": "string",
                        "minLength": 1
                    },
                    "plugin_name": {
                        "type": "string",
                        "minLength": 1
                    },
                    "plugin_version": {
                        "type": "string",
                        "minLength": 1
                    },
                    "image": {
                        "type": "string",
                        "minLength": 1
                    },
                    "node_group_templates": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "minLength": 1,
                                    "format": "valid_name"
                                },
                                "node_processes": {
                                    "type": "array",
                                    "minItems": 1,
                                    "items": {
                                        "type": "string",
                                        "minLength": 1
                                    }
                                },
                                "flavor": {
                                    "type": ["object", "string"],
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "minLength": 1
                                        },
                                        "id": {
                                            "type": "string",
                                            "minLength": 1
                                        },
                                        "vcpus": {
                                            "type": "integer",
                                            "minimum": 1
                                        },
                                        "ram": {
                                            "type": "integer",
                                            "minimum": 1
                                        },
                                        "root_disk": {
                                            "type": "integer",
                                            "minimum": 0
                                        },
                                        "ephemeral_disk": {
                                            "type": "integer",
                                            "minimum": 0
                                        },
                                        "swap_disk": {
                                            "type": "integer",
                                            "minimum": 0
                                        },
                                    },
                                    "additionalProperties": True
                                },
                                "description": {
                                    "type": "string"
                                },
                                "volumes_per_node": {
                                    "type": "integer",
                                    "minimum": 0
                                },
                                "volumes_size": {
                                    "type": "integer",
                                    "minimum": 0
                                },
                                "node_configs": {
                                    "type": "object"
                                },
                                "security_groups": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "minLength": 1
                                    }
                                },
                                "auto_security_group": {
                                    "type": "boolean"
                                },
                                "availability_zone": {
                                    "type": "string",
                                    "minLength": 1
                                },
                                "volumes_availability_zone": {
                                    "type": "string",
                                    "minLength": 1
                                },
                                "volume_type": {
                                    "type": "string",
                                    "minLength": 1
                                },
                                "is_proxy_gateway": {
                                    "type": "boolean"
                                }
                            },
                            "required": ["name", "flavor", "node_processes"],
                            "additionalProperties": False
                        }
                    },
                    "cluster_template": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "minLength": 1,
                                "format": "valid_name"
                            },
                            "description": {
                                "type": "string"
                            },
                            "cluster_configs": {
                                "type": "object"
                            },
                            "node_group_templates": {
                                "type": "object",
                                "patternProperties": {
                                    ".*": {
                                        "type": "integer",
                                        "minimum": 1
                                    }
                                }
                            },
                            "anti_affinity": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "minLength": 1
                                }
                            }
                        },
                        "required": ["name", "node_group_templates"],
                        "additionalProperties": False
                    },
                    "cluster": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "minLength": 1,
                                "format": "valid_name"
                            },
                            "description": {
                                "type": "string"
                            },
                            "is_transient": {
                                "type": "boolean"
                            }
                        },
                        "required": ["name"],
                        "additionalProperties": False,
                    },
                    "timeout_check_transient": {
                        "type": "integer",
                        "minimum": 1
                    },
                    "timeout_delete_resource": {
                        "type": "integer",
                        "minimum": 1
                    },
                    "timeout_poll_cluster_status": {
                        "type": "integer",
                        "minimum": 1
                    },
                    "timeout_poll_jobs_status": {
                        "type": "integer",
                        "minimum": 1
                    },
                    "custom_checks": {
                        "type": "object",
                        "properties": {
                            ".*": {
                                "type": "object",
                            }
                        }
                    },
                    "scaling": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "operation": {
                                    "type": "string",
                                    "enum": ["add", "resize"]
                                },
                                "node_group": {
                                    "type": "string",
                                    "minLength": 1
                                },
                                "size": {
                                    "type": "integer",
                                    "minimum": 0
                                }
                            },
                            "required": ["operation", "node_group", "size"],
                            "additionalProperties": False
                        }
                    },
                    "scenario": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "minLength": 1
                        }
                    },
                    "edp_jobs_flow": {
                        "type": ["string", "array"]
                    },
                    "retain_resources": {
                        "type": "boolean"
                    },
                    "edp_batching": {
                        "type": "integer",
                        "minimum": 1
                    }
                },
                "required": ["plugin_name", "plugin_version", "image"],
                "additionalProperties": False
            }
        },
        "edp_jobs_flow": {
            "type": "object",
            "patternProperties": {
                ".*": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["Pig", "Java", "MapReduce",
                                         "MapReduce.Streaming", "Hive",
                                         "Spark"]
                            },
                            "input_datasource": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["swift", "hdfs", "maprfs"]
                                    },
                                    "source": {
                                        "type": "string"
                                    },
                                    "hdfs_username": {
                                        "type": "string"
                                    }
                                },
                                "required": ["type", "source"],
                                "additionalProperties": False
                            },
                            "output_datasource": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["swift", "hdfs", "maprfs"]
                                    },
                                    "destination": {
                                        "type": "string"
                                    }
                                },
                                "required": ["type", "destination"],
                                "additionalProperties": False
                            },
                            "main_lib": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["swift", "database"]
                                    },
                                    "source": {
                                        "type": "string"
                                    }
                                },
                                "required": ["type", "source"],
                                "additionalProperties": False
                            },
                            "additional_libs": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {
                                            "type": "string",
                                            "enum": ["swift", "database"]
                                        },
                                        "source": {
                                            "type": "string"
                                        }
                                    },
                                    "required": ["type", "source"],
                                    "additionalProperties": False
                                }
                            },
                            "configs": {
                                "type": "object"
                            },
                            "args": {
                                "type": "array"
                            }
                        },
                        "required": ["type"],
                        "additionalProperties": False
                    }
                }
            }
        }
    },
    "required": ["clusters"],
    "additionalProperties": False
}


@jsonschema.FormatChecker.cls_checks("uri")
def validate_uri_format(entry):
    return rfc3986.is_valid_uri(entry)


@jsonschema.FormatChecker.cls_checks('valid_name')
def validate_name_hostname_format(entry):
    res = re.match(r"^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]"
                   r"*[a-zA-Z0-9])\.)*([A-Za-z]|[A-Za-z]"
                   r"[A-Za-z0-9\-]*[A-Za-z0-9])$", entry)
    return res is not None


class Validator(jsonschema.Draft4Validator):
    def __init__(self, schema):
        format_checker = jsonschema.FormatChecker()
        super(Validator, self).__init__(
            schema, format_checker=format_checker)


def validate(config):
    return Validator(SCHEMA).validate(config)
