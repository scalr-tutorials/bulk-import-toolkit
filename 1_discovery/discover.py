#!/usr/bin/env python3

import argparse
import json

from scalr_session import ScalrSession


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
    servers = scalr_client.get_servers_for_import(args.location)
    # Step 2 : get more info on these servers from EC2
    print(servers)
    client = boto3.client('ec2')
    for s in servers:
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--account', '-a', required=True, type=int)
    parser.add_argument('--environment', '-e', required=True, type=int)
    parser.add_argument('--location', '-l', required=True, help='Cloud Location (region for EC2, e.g. us-east-1)')
    parser.add_argument('--url', '-u', help='Scalr URL', default='http://localhost')
    parser.add_argument('--password', '-p', help='Scalr admin password. Taken from /etc/scalr-server-secrets.json if not provided.')

