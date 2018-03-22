#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import re
import yaml


def make_step_id():
    make_step_id.counter += 1
    return '{:06d}'.format(make_step_id.counter)
make_step_id.counter = 0


def project_find_step(project_name, env_id):
    return {
        'id': make_step_id(),
        'action': 'find-project',
        'params': {
            'envId': str(env_id),
        },
        'query': {
            'name': project_name,
        },
        'outputs': [
            {
                'name': 'projectid',
                'location': 'id'
            }
        ]
    }


def farm_find_step(farm_name, env_id):
    return {
        'id': make_step_id(),
        'action': 'find-farm',
        'params': {
            'envId': str(env_id),
        },
        'query': {
            'name': farm_name,
        },
        'outputs': [
            {
                'name': 'farmid',
                'location': 'id'
            }
        ]
    }


def farm_role_find_step(farm_role_name, parent_farm_step_id, env_id):
    return {
        'id': make_step_id(),
        'action': 'find-farm-role',
        'params': {
            'envId': str(env_id),
            'farmId': '$ref/{}/farmid'.format(parent_farm_step_id)
        },
        'query': {
            'alias': farm_role_name,
        },
        'outputs': [
            {
                'name': 'farmroleid',
                'location': 'id'
            }
        ]
    }


def server_import_step(server_id, parent_farm_role_step_id, env_id):
    return {
        'id': make_step_id(),
        'action': 'import-server',
        'params': {
            'envId': str(env_id),
            'farmRoleId': '$ref/{}/farmroleid'.format(parent_farm_role_step_id)
        },
        'body': {
            'cloudServerId': server_id,
        }
    }


def farm_launch_step(parent_farm_step_id, env_id):
    return {
        'id': make_step_id(),
        'action': 'launch-farm',
        'params': {
            'envId': str(env_id),
            'farmId': '$ref/{}/farmid'.format(parent_farm_step_id)
        }
    }


def farm_create_step(farm_name, env_id, project_id=None, project_step_id=None):
    step = {
        'id': make_step_id(),
        'action': 'create-farm',
        'params': {
            'envId': str(env_id)
        },
        'body': {
            'name': farm_name,
            'project': {
                'id': ''
            }
        },
        'outputs': [
            {
                'name': 'farmid',
                'location': 'id'
            }
        ]
    }
    if project_id:
        step['body']['project']['id'] = project_id
    elif project_step_id:
        step['body']['project']['id'] = '$ref/{}/projectid'.format(project_step_id)
    return step


def farm_role_create_step(parent_farm_step_id, env_id, alias, cloud_platform,
                          cloud_location, instance_type, network_id,
                          subnets, role_id, security_groups):
    return {
        'id': make_step_id(),
        'action': 'create-farm-role',
        'params': {
            'envId': env_id,
            'farmId': '$ref/{}/farmid'.format(parent_farm_step_id)
        },
        'body': {
            'alias': alias,
            'cloudPlatform': cloud_platform,
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


def make_farms(data):
    # farm name is a position 1, project ID is at position 9
    # We want to check that the same project is specified for all servers in one farm...
    farms = {} # name -> project mapping
    for i, line in enumerate(data):
        farm_name = line[1]
        project = line[9]
        if farm_name not in farms:
            farms[farm_name] = project
        else:
            if farms[farm_name] != project:
                print('ERROR at line {}: project for farm {} defined as {}, previously defined as {}. Aborting.'.format(
                    i, farm_name, project, farms[farm_name]))
                raise ValueError
    return farms


def check_farm_role(structure):
    # Check alias
    if not re.match('^[a-zA-Z\d][a-zA-Z\d\-]*[a-zA-Z\d]$', structure['alias']):
        print('ERROR: invalid farm role alias: {}. Must contain only letters, numbers and dashes'.format(structure['alias']))
        raise ValueError
    # Check SG list is not empty
    if len(structure['security_groups']) == 0:
        print('ERROR: In farm role {} empty security groups list is not allowed.'.format(structure['alias']))
        raise ValueError


def make_farms_and_roles_plan(data, envId, use_project_names=False):
    """ Required data format:
    server id, farm name, farm role alias, region, instance type, VPC id, subnet, role id, security groups (space separated), project id
    """
    farms = make_farms(data)
    projects = {p: None for p in set(farms.values())}
    farm_names = set([l[1] for l in data])
    farm_roles = {f:{} for f in farm_names}
    # Gather required data for each farm role, and make sure that the provided data is consistent...
    for i, line in enumerate(data):
        farm_name = line[1]
        farm_role_name = line[2]
        if farm_role_name not in farm_roles[farm_name]:
            farm_role_structure = farm_role_from_line(line)
            farm_roles[farm_name][farm_role_name] = farm_role_structure
            check_farm_role(farm_role_structure)

    steps = []
    # 0: fetch projects
    if use_project_names:
        for project_name in projects:
            # Record the step id in projects
            step = project_find_step(project_name, envId)
            projects[project_name] = step['id']
            steps.append(step)

    # 1: create farms
    farms_step_ids = {} # key = farm, value = id of the step that retrieves this farm
    for farm_name, project in farms.items():
        if use_project_names:
            step = farm_create_step(farm_name, envId, project_step_id=projects[project])
        else:
            step = farm_create_step(farm_name, envId, project_id=project)
        farms_step_ids[farm_name] = step['id']
        steps.append(step)

    # 2 : farm roles
    farm_roles_step_ids = {} # key = (farm, farm role) pair, value = id of the step the retrieves the farm role
    for farm_name in farm_roles:
        for farm_role_alias, farm_role_structure in farm_roles[farm_name].items():
            step = farm_role_create_step(farms_step_ids[farm_name], envId, cloud_platform='ec2', **farm_role_structure)
            farm_roles_step_ids[(farm_name, farm_role_alias)] = step['id']
            steps.append(step)

    # 3 : launch farms
    for farm_name in farms:
        step = farm_launch_step(farms_step_ids[farm_name], envId)
        steps.append(step)

    return steps


def make_simple_plan(data, envId):
    # Assumption: col 1 is server ID, col 2 is farm name, col 3 is farm role alias
    farms = set([l[1] for l in data])
    farm_roles = {} # farm name -> list of farm role aliases
    for line in data:
        if not line[1] in farm_roles:
            farm_roles[line[1]] = [line[2]]
        else:
            if line[2] not in farm_roles[line[1]]:
                farm_roles[line[1]].append(line[2])

    steps = []
    # 1 : find farms
    farms_step_ids = {} # key = farm, value = id of the step that retrieves this farm
    for farm_name in farms:
        step = farm_find_step(farm_name, envId)
        farms_step_ids[farm_name] = step['id']
        steps.append(step)
    # 2 : find farm roles
    farm_roles_step_ids = {} # key = (farm, farm role) pair, value = id of the step the retrieves the farm role
    for farm_name in farm_roles:
        for farm_role_alias in farm_roles[farm_name]:
            step = farm_role_find_step(farm_role_alias, farms_step_ids[farm_name], envId)
            farm_roles_step_ids[(farm_name, farm_role_alias)] = step['id']
            steps.append(step)
    # 3 : import all servers
    for line in data:
        server_id = line[0]
        farm_name = line[1]
        farm_role_alias = line[2]
        steps.append(server_import_step(server_id, farm_roles_step_ids[(farm_name, farm_role_alias)], envId))

    return steps


def write_plan(plan, fname):
    # Refuse to overwrite existing file
    with open(fname, 'x') as outfile:
        yaml.dump(plan, outfile, default_flow_style=False)


def main(args):
    with open(args.source, newline='') as source_file:
        reader = csv.reader(source_file)
        data = [l for l in reader]
    setup_plan = make_farms_and_roles_plan(data, args.environment, args.project_names)
    print('Created setup plan with {} steps.'.format(len(setup_plan)))
    write_plan(setup_plan, args.output + '.setup.yml')
    import_plan = make_simple_plan(data, args.environment)
    print('Created import plan with {} steps.'.format(len(import_plan)))
    write_plan(import_plan, args.output + '.import.yml')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', '-s', help='Source CSV file')
    parser.add_argument('--environment', '-e', help='Environment this import plan is for')
    parser.add_argument('--output', '-o', help='File to write the plan to (MUST NOT exist)')
    parser.add_argument('--project-names', '-p', help='Treat column 10 of source CSV as project names and not IDs', action='store_true')
    main(parser.parse_args())
