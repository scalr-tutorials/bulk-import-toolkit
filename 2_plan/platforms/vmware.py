#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

"""
Platform specific functions for VMware

CSV format for VMware imports:
vm-1372,Farm Name,Farm role alias,datacenter-21,0f52797dd8ba,network-30,96554,domain-s26,host-28,Project name or ID,group-v22,resgroup-27,datastore-29
VMID                              Location      Inst. typeID network ID Role  Cpt res                               Folder
"""

def farm_role_from_line(line):
    return {
        'alias': line[2],
        'datacenter': line[3],
        'instance_type': line[4],
        'network': line[5],
        'role_id': line[6],
        'compute_resource': line[7],
        'host': line[8],
        'folder': line[10],
        'resource_group': line[11],
        'datastore': line[12],
    }


def check_farm_role(structure):
    # Check alias
    if not re.match('^[a-zA-Z\d][a-zA-Z\d\-]*[a-zA-Z\d]$', structure['alias']):
        print('ERROR: invalid farm role alias: {}. Must contain only letters, numbers and dashes'.format(structure['alias']))
        raise ValueError


def farm_role_create_step(parent_farm_step_id, env_id, step_id, alias,
                          datacenter, instance_type, network,
                          role_id, compute_resource, host, folder,
                          resource_group, datastore):
    return {
        'id': step_id,
        'action': 'create-farm-role',
        'params': {
            'envId': env_id,
            'farmId': '$ref/{}/farmid'.format(parent_farm_step_id)
        },
        'body': {
            'alias': alias,
            'cloudFeatures': {
                'type': 'VmwareCloudFeatures',
                'hosts': [ host ],
                'dataStore': datastore,
                'computeResource': compute_resource,
                'folder': folder,
                'resourcePool': resource_group,
            }, 
            'cloudLocation': datacenter,
            'cloudPlatform': 'vmware',
            'instanceType': {
                'id': instance_type
            },
            'networking': {
                'networks': [{
                    'id': network
                }],
            },
            'role': {
                'id': role_id
            },
            'scaling': {
                'enabled': False
            }
        },
        'outputs': [
            {
                'name': 'farmroleid',
                'location': 'id'
            }
        ]
    }


