#!/usr/bin/env python3

import argparse
import boto3
import json

from scalr_session import ScalrSession
from util import json_serial


def load_scalr_password():
    creds_file = '/etc/scalr-server/scalr-server-secrets.json'
    with open(creds_file) as f:
        secrets = json.load(f)
        return secrets['app']['admin_password']


def main(args):
    # Step 1 : get list of servers available for import from Scalr
    scalr_user = 'admin'
    scalr_password = args.password or load_scalr_password()
    scalr_url = args.url
    scalr_client = ScalrSession(scalr_url)
    scalr_client.login('admin', scalr_password)
    scalr_client.admin_login_as(args.account)
    servers = {s['cloudServerId']: s for s in scalr_client.get_servers_for_import(args.location)}
    # Step 2 : get more info on these servers from EC2
    client = boto3.client('ec2', region_name=args.location)
    instances = client.describe_instances(InstanceIds=list(servers.keys()))
    for r in instances['Reservations']:
        for i in r['Instances']:
            instance_id = i['InstanceId']
            servers[instance_id]['ec2-data'] = i
    print(json.dumps(servers, indent=2, default=json_serial))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--account', '-a', required=True, type=int)
    parser.add_argument('--environment', '-e', required=True, type=int)
    parser.add_argument('--location', '-l', required=True, help='Cloud Location (region for EC2, e.g. us-east-1)')
    parser.add_argument('--url', '-u', help='Scalr URL', default='http://localhost')
    parser.add_argument('--password', '-p', help='Scalr admin password. Taken from /etc/scalr-server-secrets.json if not provided.')
    main(parser.parse_args())

