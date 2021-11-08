#!/usr/bin/python3
import re
import json


def read_node(string, node_name='activity'):
    nodes = []
    manifest_nodes = re.findall('<%s .*>' % node_name, string)
    for node in manifest_nodes:
        m = re.match('.*?name="(.*?)".*', node)
        if m:
            nodes.append(m.group(1))
    return nodes

def launcher_activity(manifest):
    pass


def parse_manifest(file):
    with open(file, 'r') as f:
        manifest = f.read()
    manifest_entity = {}
    manifest_entity['permissions'] = read_node(manifest, 'uses-permission')
    manifest_entity['activities'] = read_node(manifest, 'activity')
    manifest_entity['providers'] = read_node(manifest, 'provider')
    manifest_entity['services'] = read_node(manifest, 'service')
    manifest_entity['receivers'] = read_node(manifest, 'receiver')
    applications = read_node(manifest, 'application')
    launcher_activity(manifest)
    if len(applications) > 0:
        manifest_entity['application'] = applications[0]
    else:
        manifest_entity['application'] = 'android.app.Application'
    return manifest_entity


if __name__ == '__main__':
    print(json.dumps(parse_manifest('AndroidManifest.xml')))
