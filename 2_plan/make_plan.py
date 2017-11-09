#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import yaml


def make_step_id():
    make_step_id.counter += 1
    return '{:06d}'.format(make_step_id.counter)
make_step_id.counter = 0


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
    plan = make_simple_plan(data, args.environment)
    write_plan(plan, args.output)
    print('Created import plan with {} steps.'.format(len(plan)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', '-s', help='Source CSV file')
    parser.add_argument('--environment', '-e', help='Environment this import plan is for')
    parser.add_argument('--output', '-o', help='File to write the plan to (MUST NOT exist)')
    main(parser.parse_args())
