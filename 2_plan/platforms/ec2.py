#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

"""
Platform specific functions for EC2

CSV format for EC2 imports:
server id, farm name, farm role alias, region, instance type, VPC id, subnet, role id, security groups (space separated), project id
"""


def farm_role_from_line(line):
    return {
        'alias': line[2],
        'cloud_location': line[3],
        'instance_type': line[4],
        'network_id': line[5],
        'subnets': [line[6]],
        'role_id': line[7],
        'security_groups': line[8].split()
    }


def check_farm_role(structure):
    # Check alias
    if not re.match('^[a-zA-Z\d][a-zA-Z\d\-]*[a-zA-Z\d]$', structure['alias']):
        print('ERROR: invalid farm role alias: {}. Must contain only letters, numbers and dashes'.format(structure['alias']))
        raise ValueError
    # Check SG list is not empty
    if len(structure['security_groups']) == 0:
        print('ERROR: In farm role {} empty security groups list is not allowed.'.format(structure['alias']))
        raise ValueError


def farm_role_create_step(parent_farm_step_id, env_id, step_id, alias,
                          cloud_location, instance_type, network_id,
                          subnets, role_id, security_groups):
    return {
        'id': step_id,
        'action': 'create-farm-role',
        'params': {
            'envId': env_id,
            'farmId': '$ref/{}/farmid'.format(parent_farm_step_id)
        },
        'body': {
            'alias': alias,
            'cloudPlatform': 'ec2',
            'cloudLocation': cloud_location,
            'instanceType': {
                'id': instance_type
            },
            'networking': {
                'networks': [{
                    'id': network_id
                }],
                'subnets': [{'id': subnet_id} for subnet_id in subnets],
            },
            'role': {
                'id': role_id
            },
            'scaling': {
                'enabled': False
            },
            'security': {
                'securityGroups': [{'id': sg_id} for sg_id in security_groups]
            }
        },
        'outputs': [
            {
                'name': 'farmroleid',
                'location': 'id'
            }
        ]
    }



