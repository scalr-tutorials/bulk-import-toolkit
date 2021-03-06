#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import base64
import collections
import datetime
import hashlib
import hmac
import json
import logging
import os
import pytz
import requests
import urllib
import yaml


logging.basicConfig(level=logging.INFO)

dry_run = False


actions = {
    'find-farm': {
        'skip-on-dry-run': False,
        'method': 'list',
        'url': '/api/v1beta0/user/{envId}/farms/'
    },
    'find-farm-role': {
        'skip-on-dry-run': False,
        'method': 'list',
        'url': '/api/v1beta0/user/{envId}/farms/{farmId}/farm-roles/'
    },
    'find-project': {
        'skip-on-dry-run': False,
        'method': 'list',
        'url': '/api/v1beta0/user/{envId}/projects/'
    },
    'import-server': {
        'skip-on-dry-run': True,
        'method': 'post',
        'url': '/api/v1beta0/user/{envId}/farm-roles/{farmRoleId}/actions/import-server/'
    },
    'create-farm': {
        'skip-on-dry-run': True,
        'method': 'post',
        'url': '/api/v1beta0/user/{envId}/farms/'
    },
    'create-farm-role': {
        'skip-on-dry-run': True,
        'method': 'post',
        'url': '/api/v1beta0/user/{envId}/farms/{farmId}/farm-roles/'
    },
    'launch-farm': {
        'skip-on-dry-run': True,
        'method': 'post',
        'url': '/api/v1beta0/user/{envId}/farms/{farmId}/actions/launch/'
    }
}


def query_yes_no(question, default='yes'):
    """Ask a yes/no question via raw_input() and return their answer.

    'question' is a string that is presented to the user.
    'default' is the presumed answer if the user just hits <Enter>.
        It must be 'yes' (the default), 'no' or None (meaning
        an answer is required of the user).

    The 'answer' return value is True for 'yes' or False for 'no'.
    """
    valid = {'yes': True, 'y': True, 'ye': True,
             'no': False, 'n': False}
    if default is None:
        prompt = ' [y/n] '
    elif default == 'yes':
        prompt = ' [Y/n] '
    elif default == 'no':
        prompt = ' [y/N] '
    else:
        raise ValueError('invalid default answer: "%s"' % default)

    while True:
        print(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            print('Please respond with "yes" or "no" (or "y" or "n").')


class ScalrApiClient(object):
    def __init__(self, api_url, key_id, key_secret):
        self.api_url = api_url
        self.key_id = key_id
        self.key_secret = key_secret
        self.logger = logging.getLogger("api[{0}]".format(self.api_url))
        self.session = ScalrApiSession(self)

    def list(self, path, **kwargs):
        data = []
        while path is not None:
            body = self.session.get(path, **kwargs).json()
            data.extend(body["data"])
            path = body["pagination"]["next"]
        return data

    def create(self, *args, **kwargs):
        return self.session.post(*args, **kwargs).json().get("data")

    def fetch(self, *args, **kwargs):
        return self.session.get(*args, **kwargs).json()["data"]

    def delete(self, *args, **kwargs):
        self.session.delete(*args, **kwargs)

    def post(self, *args, **kwargs):
        return self.session.post(*args, **kwargs).json()["data"]


class ScalrApiSession(requests.Session):
    def __init__(self, client):
        self.client = client
        super(ScalrApiSession, self).__init__()

    def prepare_request(self, request):
        if not request.url.startswith(self.client.api_url):
            request.url = "".join([self.client.api_url, request.url])
        request = super(ScalrApiSession, self).prepare_request(request)

        now = datetime.datetime.now(tz=pytz.timezone(os.environ.get("TZ", "UTC")))
        date_header = now.isoformat()

        url = urllib.parse.urlparse(request.url)

        # TODO - Spec isn't clear on whether the sorting should happen prior or after encoding
        if url.query:
            pairs = urllib.parse.parse_qsl(url.query, keep_blank_values=True, strict_parsing=True)
            pairs = [list(map(urllib.parse.quote, pair)) for pair in pairs]
            pairs.sort(key=lambda pair: pair[0])
            canon_qs = "&".join("=".join(pair) for pair in pairs)
        else:
            canon_qs = ""

        # Authorize
        sts = b"\n".join([
            request.method.encode('utf-8'),
            date_header.encode('utf-8'),
            url.path.encode('utf-8'),
            canon_qs.encode('utf-8'),
            request.body if request.body is not None else b""
        ])

        sig = " ".join([
            "V1-HMAC-SHA256",
            base64.b64encode(hmac.new(self.client.key_secret.encode('utf-8'), sts, hashlib.sha256).digest()).decode('utf-8')
        ])

        request.headers.update({
            "X-Scalr-Key-Id": self.client.key_id,
            "X-Scalr-Signature": sig,
            "X-Scalr-Date": date_header
        })

        self.client.logger.debug("URL: %s", request.url)
        self.client.logger.debug("StringToSign: %s", repr(sts))
        self.client.logger.debug("Signature: %s", repr(sig))

        return request

    def request(self, *args, **kwargs):
        res = super(ScalrApiSession, self).request(*args, **kwargs)
        self.client.logger.info("%s - %s", " ".join(args), res.status_code)
        # try:
        #     errors = res.json().get("errors", None)
        #     if errors is not None:
        #         for error in errors:
        #             self.client.logger.warning("API Error (%s): %s", error["code"], error["message"])
        # except ValueError:
        #     self.client.logger.error("Received non-JSON response from API!")
        # res.raise_for_status()
        self.client.logger.debug("Received response: %s", res.text)
        return res


# Resolves references to the outputs of previous steps
# Works on dicts of (dicts of () or strings) or strings only
def resolve_references(d, outputs):
    if isinstance(d, collections.MutableMapping):
        # Dict
        for k, v in d.items():
            d[k] = resolve_references(v, outputs)
        return d
    elif isinstance(d, collections.MutableSequence):
        # List
        for i, v in enumerate(d):
            d[i] = resolve_references(v, outputs)
        return d
    elif isinstance(d, int):
        # Integer, for role IDs mostly
        return d
    else:
        if d.startswith('$ref/'):
            path = d[5:].split('/')
            o = outputs
            for key in path:
                o = o[key]
            return o
        else:
            return d


def save_outputs(step, data, outputs):
    if not 'outputs' in step:
        return
    for o in step['outputs']:
        # TODO Allow to get values not only from the top level...
        value = data[o['location']]
        logging.info('Saving output %s for step %s: %s', o['name'], step['id'], value)
        if not step['id'] in outputs:
            outputs[step['id']] = {
                o['name']: value
            }
        else:
            outputs[step['id']][o['name']] = value


def process_step(step, client, outputs, outputs_file_name):
    action = actions[step['action']]
    params = resolve_references(step.get('params', {}), outputs)
    url = action['url'].format(**params)
    query = resolve_references(step.get('query', {}), outputs)
    full_url = url + '?' + urllib.parse.urlencode(query)
    body = resolve_references(step.get('body', {}), outputs)
    if dry_run and action['skip-on-dry-run']:
        logging.info('Dry run: skipping action %s (%s)', step['id'], step['action'])
        logging.info('Would have queried: %s body: %s', full_url, body)
        return True     # Success

    # try:
    if action['method'] == 'list':
        data = client.list(full_url)
        if len(data) != 1:
            logging.error('List operation in step %s returned %d results (expected 1)', step['id'], len(data))
            return False
        data = data[0]
    elif action['method'] == 'post':
        try:
            data = client.post(full_url, json=body)
        except:
            if step['action'] == 'create-farm':
                name = urllib.parse.quote(body['name'])
                data1 = client.list(full_url + 'name=' + name)
            elif step['action'] == 'create-farm-role':
                alias = urllib.parse.quote(body['alias'])
                data1 = client.list(full_url + 'alias=' + alias)
            elif step['action'] == 'import-server':
                server_id = body['cloudServerId']
                data1 = client.list(full_url.replace('actions/import-server', 'servers') + 'cloudServerId=' + server_id)

            data = data1[0]

    save_outputs(step, data, outputs)
    outputs[step['id']]['complete'] = True
    # Save the outputs after each successful step so that we don't lose any info (but don't do it on dry runs)
    save_outputs_to_file(outputs, outputs_file_name)
    return True

    # except:
    #     # Special case for server imports, allow to continue even if it fails
    #     if step['action'] == 'import-server':
    #         if not query_yes_no('Error importing server. Continue anyway?', 'no'):
    #             raise
    #         else:
    #             return True
    #     else:
    #         raise


def process_plan(plan, client, outputs_file_name):
    total_steps = len(plan)
    logging.info('Starting import plan. %d steps to process.', total_steps)
    outputs = load_outputs(outputs_file_name) or {}
    for step_number, step in enumerate(plan):
        logging.info('Processing step %s (%d/%d)', step['id'], step_number+1, total_steps)
        if step['id'] not in outputs:
            outputs[step['id']] = {}
        if outputs[step['id']].get('complete'):
            # This step already completed on a previous run, we already have its output
            logging.info('Skipping step {}, already done'.format(step['id']))
            continue
        r = process_step(step, client, outputs, outputs_file_name)
        if not r:
            logging.error('Error processing step %s, aborting', step['id'])
            break



def save_outputs_to_file(outputs, outputs_file_name):
    if not outputs:
        return
    with open(outputs_file_name, 'w') as outputs_file:
        yaml.dump(outputs, outputs_file, default_flow_style=False)


def load_outputs(outputs_file_name):
    """ Load outputs generated by a previous run to resume execution at the same point """
    try:
        with open(outputs_file_name) as outputs_file:
            outputs = yaml.load(outputs_file)
        return outputs
    except:
        return {}


def main(args):
    global dry_run
    plan_filename = args.plan
    with open(plan_filename) as plan_file:
        plan = yaml.load(plan_file)
    client = ScalrApiClient(args.url, args.key, args.secret)
    if args.dry_run:
        dry_run = True
    process_plan(plan, client, plan_filename + '.status')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', '-u', help='Scalr URL')
    parser.add_argument('--key', '-k', help='API key ID')
    parser.add_argument('--secret', '-s', help='API key secret')
    parser.add_argument('--plan', '-p', help='Import plan')
    parser.add_argument('--dry-run', '-z', action='store_true', default=False,
        help='Dry run, go through the import plan without actually importing any servers')
    main(parser.parse_args())
