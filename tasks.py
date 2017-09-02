import os
import sys
import pprint
import json

from invoke import task
import contentful_management
from contentful_management.resource_builder import ResourceBuilder
import yaml

ENV_FILE = 'env.yaml'
ENV_DIST_FILE = 'env.dist.yaml'
_contentful_client = None
_config = {}


def _merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.

    :param dict_args:
    :return:
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def _load_env():
    """
    Load environment variables as defined in `env.yaml`

    :return: Environment configuration.
    :rtype: dict
    """
    if getattr(sys.modules[__name__], '_config') == {}:
        with open(ENV_FILE) as config_file:
            config_yaml = yaml.load(config_file.read())
        setattr(sys.modules[__name__], '_config', config_yaml)
    config = getattr(sys.modules[__name__], '_config')
    return config


def _get_config():
    return getattr(sys.modules[__name__], '_config')


def _get_contentful_client():
    api_token = _get_config()['management_api_token']
    client = getattr(sys.modules[__name__], '_contentful_client')
    if client is None:
        client = contentful_management.Client(api_token)
        setattr(sys.modules[__name__], '_contentful_client', client)
    return client


def _get_schema():
    with open('schema.yaml') as schema_file:
        schema = yaml.load(schema_file.read())
    return schema


def _extract_interface_controls_from_schema(schema):
    interface_controls = {}
    for content_type, value in schema['contentTypes'].items():
        interface_controls[content_type] = []
        for field in value['fields']:
            control = {
                'fieldId': field['id']
            }
            if 'interface' in field:
                for interface_property, property_value in field['interface'].items():
                    control[interface_property] = property_value
            interface_controls[content_type].append(control)
    return interface_controls


def _get_content_type_interface_controls(content_type):
    schema = _get_schema()
    interface_controls = _extract_interface_controls_from_schema(schema)
    return interface_controls[content_type]



@task()
def sync_env(ctx):
    """
    Add new keys from `env.dist.yaml`.

    :param ctx:
    :return:
    """
    if os.path.isfile(ENV_FILE):
        config_yaml = _load_env()
    else:
        config_yaml = {}

    with open(ENV_DIST_FILE) as config_dist_file:
        config_dist_yaml = yaml.load(config_dist_file.read())

    merged_config = _merge_dicts(config_dist_yaml, config_yaml)

    with open(ENV_FILE, 'w') as config_file:
        config_file.write(yaml.dump(merged_config, default_flow_style=False))


@task()
def describe_space(ctx):
    _load_env()
    client = _get_contentful_client()
    content_types = client.content_types(_config['space_id']).all()
    if content_types.total > 0:
        content_types_dict = {content_type_instance.name: content_type_instance for content_type_instance in content_types.items}
    return content_types_dict


@task()
def create_content_type(ctx, content_type):
    _load_env()
    with open('schema.yaml') as schema_file:
        schema = yaml.load(schema_file.read())
    client = _get_contentful_client()
    content_type_schema = schema['contentTypes'][content_type]
    """ First update the content type resource """
    try:
        content_type_instance = client.content_types(_config['space_id']).create(content_type, content_type_schema)
    except contentful_management.errors.VersionMismatchError as e:
        content_type = client.content_types(_config['space_id']).find(content_type)
        content_json = content_type.to_json()
        merged_schema = _merge_dicts(content_json, content_type_schema)
        content_type_instance = ResourceBuilder(client, client.default_locale, merged_schema).build()
        content_type_instance.save()
    """ Publish the changes """
    content_type_instance.publish()

    """ Now update the editor interface """
    editor_interface = client.editor_interfaces(_config['space_id'], content_type.id).find()
    interface_controls = _get_content_type_interface_controls(content_type.id)
    editor_interface.controls = interface_controls
    editor_interface.save()


@task()
def describe_content_type(ctx, content_type):
    _load_env()
    client = _get_contentful_client()
    content_type = client.content_types(_config['space_id']).find(content_type)
    print(f"Content type {content_type}.\n")
    pretty_yaml = yaml.dump(content_type.raw, default_flow_style=False)
    print(pretty_yaml)


@task()
def describe_content_type_fields(ctx, content_type):
    _load_env()
    client = _get_contentful_client()
    content_type_instance = client.content_types(_config['space_id']).find(content_type)
    interface = client.editor_interfaces(_config['space_id'], content_type).find()
    fields = {field.id: field.raw for field in content_type_instance.fields}
    for control in interface.controls:
        fields[control['fieldId']]['interface'] = control
    pretty_yaml = yaml.dump(fields, default_flow_style=False)
    print(pretty_yaml)



@task()
def describe_editor_interface(ctx, content_type):
    _load_env()
    client = _get_contentful_client()
    interface = client.editor_interfaces(_config['space_id'], content_type).find()
    pp = pprint.PrettyPrinter(indent=4)
    print(f"Editor interface for {content_type}.\n")
    for control in interface.controls:
        pp.pprint(control)
        print('\n')


# @task()
# def sync(ctx):
#     client = Client('<content_management_api_key>')
#
#     # Create a Content Type:
#     content_type_id = '<content_type_id>'  # Use `None` if you want the API to autogenerate the ID.
#     content_type = client.content_types('<space_id>').create(content_type_id, {
#         'name': 'New Content Type',
#         'description': 'Content Type Description',
#         'displayField': 'name',
#         'fields': [
#             {
#                 'name': 'Name',
#                 'id': 'name',
#                 'type': 'Symbol',
#                 'localized': False
#             }
#         ]
#     })
    #
    # # Update a Content Type:
    # content_type.name = 'Other Content Type Name'
    # content_type.save()
