"""Custom YAML file loader with !secrets support."""

import logging
import os
import sys

from config.configuration import Configuration
from pathlib import Path
import yaml
from config import config_from_yaml

from collections import OrderedDict
from typing import Dict, List, TextIO, TypeVar, Union

from exceptions import FailedInitialization


CONFIG_YAML = 'mme.yaml'
SECRET_YAML = 'mme_secrets.yaml'

JSON_TYPE = Union[List, Dict, str]      # pylint: disable=invalid-name
DICT_T = TypeVar("DICT_T", bound=Dict)  # pylint: disable=invalid-name

_LOGGER = logging.getLogger('mme')
_SECRET_CACHE: Dict[str, JSON_TYPE] = {}


def buildYAMLExceptionString(exception, file='cs_esphome'):
    e = exception
    try:
        type = ''
        file = file
        line = 0
        column = 0
        info = ''

        if e.args[0]:
            type = e.args[0]
            type += ' '

        if e.args[1]:
            file = os.path.basename(e.args[1].name)
            line = e.args[1].line
            column = e.args[1].column

        if e.args[2]:
            info = os.path.basename(e.args[2])

        if e.args[3]:
            file = os.path.basename(e.args[3].name)
            line = e.args[3].line
            column = e.args[3].column

        errmsg = f"YAML file error {type}in {file}:{line}, column {column}: {info}"

    except Exception as e:
        errmsg = f"YAML file error: {e}"

    return errmsg


class ConfigError(Exception):
    """General YAML configuration file exception."""


class FullLineLoader(yaml.FullLoader):
    """Loader class that keeps track of line numbers."""

    def compose_node(self, parent: yaml.nodes.Node, index: int) -> yaml.nodes.Node:
        """Annotate a node with the first line it was seen."""
        last_line: int = self.line
        node: yaml.nodes.Node = super().compose_node(parent, index)
        node.__line__ = last_line + 1  # type: ignore
        return node


def load_yaml(fname: str) -> JSON_TYPE:
    """Load a YAML file."""
    try:
        with open(fname, encoding="utf-8") as conf_file:
            return parse_yaml(conf_file)
    except UnicodeDecodeError as exc:
        _LOGGER.error(f"Unable to read '{fname}': {exc}")
        raise ConfigError(exc) from exc


def parse_yaml(content: Union[str, TextIO]) -> JSON_TYPE:
    """Load a YAML file."""
    try:
        # If configuration file is empty YAML returns None
        # We convert that to an empty dict
        return yaml.load(content, Loader=FullLineLoader) or OrderedDict()
    except yaml.YAMLError as exc:
        _LOGGER.error(str(exc))
        raise ConfigError(exc) from exc


def _load_secret_yaml(secret_path: str) -> JSON_TYPE:
    """Load the secrets yaml from path."""
    secret_path = os.path.join(secret_path, SECRET_YAML)
    if secret_path in _SECRET_CACHE:
        return _SECRET_CACHE[secret_path]

    _LOGGER.debug("Loading %s", secret_path)
    try:
        secrets = load_yaml(secret_path)
        if not isinstance(secrets, dict):
            raise ConfigError("Secrets is not a dictionary")

    except FileNotFoundError:
        secrets = {}

    _SECRET_CACHE[secret_path] = secrets
    return secrets


def secret_yaml(loader: FullLineLoader, node: yaml.nodes.Node) -> JSON_TYPE:
    """Load secrets and embed it into the configuration YAML."""
    if os.path.basename(loader.name) == SECRET_YAML:
        raise ConfigError(f"{SECRET_YAML}: attempt to load secret from within secrets file")

    secret_path = os.path.dirname(loader.name)
    home_path = str(Path.home())
    do_walk = os.path.commonpath([secret_path, home_path]) == home_path

    while True:
        secrets = _load_secret_yaml(secret_path)
        if node.value in secrets:
            _LOGGER.debug(f"Secret '{node.value}' retrieved from {secret_path}/{SECRET_YAML}")
            return secrets[node.value]

        if not do_walk or (secret_path == home_path):
            break
        secret_path = os.path.dirname(secret_path)

    raise ConfigError(f"Secret '{node.value}' not defined")


def check_required_keys(yaml, required, path='') -> bool:
    passed = True

    for keywords in required:
        for rk, rv in keywords.items():
            currentpath = path + rk if path == '' else path + '.' + rk

            requiredKey = rv.get('required')
            requiredSubkeys = rv.get('keys')
            keyType = rv.get('type', None)
            typeStr = '' if not keyType else f" (type is '{keyType.__name__}')"

            if not yaml:
                raise FailedInitialization(f"YAML file is corrupt or truncated, expecting to find '{rk}' and found nothing")

            if isinstance(yaml, list):
                for index, element in enumerate(yaml):
                    path = f"{currentpath}[{index}]"

                    yamlKeys = element.keys()
                    if requiredKey:
                        if rk not in yamlKeys:
                            _LOGGER.error(f"'{currentpath}' is required for operation {typeStr}")
                            passed = False
                            continue

                    yamlValue = dict(element).get(rk, None)
                    if yamlValue is None:
                        return passed

                    if rk in yamlKeys and keyType and not isinstance(yamlValue, keyType):
                        _LOGGER.error(f"'{currentpath}' should be type '{keyType.__name__}'")
                        passed = False

                    if isinstance(requiredSubkeys, list):
                        if len(requiredSubkeys):
                            passed = check_required_keys(yamlValue, requiredSubkeys, path) and passed
                    else:
                        raise FailedInitialization(Exception('Unexpected YAML checking error'))
            elif isinstance(yaml, dict) or isinstance(yaml, Configuration):
                yamlKeys = yaml.keys()
                if requiredKey:
                    if rk not in yamlKeys:
                        _LOGGER.error(f"'{currentpath}' is required for operation {typeStr}")
                        passed = False
                        continue

                yamlValue = dict(yaml).get(rk, None)
                if yamlValue is None:
                    continue

                if rk in yamlKeys and keyType and not isinstance(yamlValue, keyType):
                    _LOGGER.error(f"'{currentpath}' should be type '{keyType.__name__}'")
                    passed = False

                if isinstance(requiredSubkeys, list):
                    if len(requiredSubkeys):
                        passed = check_required_keys(yamlValue, requiredSubkeys, currentpath) and passed
                else:
                    raise FailedInitialization('Unexpected YAML checking error')
            else:
                raise FailedInitialization('Unexpected YAML checking error')
    return passed


def check_unsupported(yaml, required, path=''):
    try:
        passed = True
        if not yaml:
            raise FailedInitialization("YAML file is corrupt or truncated, nothing left to parse")
        if isinstance(yaml, list):
            for index, element in enumerate(yaml):
                for yk in element.keys():
                    listpath = f"{path}.{yk}[{index}]"

                    yamlValue = dict(element).get(yk, None)
                    for rk in required:
                        supportedSubkeys = rk.get(yk, None)
                        if supportedSubkeys:
                            break
                    if not supportedSubkeys:
                        _LOGGER.warning(f"'{listpath}' option is unsupported")
                        return

                    subkeyList = supportedSubkeys.get('keys', None)
                    if subkeyList:
                        passed = check_unsupported(yamlValue, subkeyList, listpath) and passed
        elif isinstance(yaml, dict) or isinstance(yaml, Configuration):
            for yk in yaml.keys():
                currentpath = path + yk if path == '' else path + '.' + yk

                yamlValue = dict(yaml).get(yk, None)
                for rk in required:
                    supportedSubkeys = rk.get(yk, None)
                    if supportedSubkeys:
                        break
                if not supportedSubkeys:
                    _LOGGER.warning(f"'{currentpath}' option is unsupported")
                    return

                subkeyList = supportedSubkeys.get('keys', None)
                if subkeyList:
                    passed = check_unsupported(yamlValue, subkeyList, currentpath) and passed
        else:
            raise FailedInitialization('Unexpected YAML checking error')
    except FailedInitialization:
        raise
    except Exception as e:
        raise FailedInitialization(f"Unexpected exception: {e}")
    return passed


def check_config(config):
    """Check that the important options are present and unknown options aren't."""

    required_keys = [
        {
            'mme': {'required': True, 'keys': [
                {'vin': {'required': False, 'keys': []}},
                {'modules': {'required': True, 'keys': [
                    {'module': {'required': True, 'keys': [
                        {'name': {'required': True, 'keys': [], 'type': str}},
                        {'channel': {'required': True, 'keys': [], 'type': str}},
                        {'arbitration_id': {'required': True, 'keys': [], 'type': int}},
                    ]}},
                ]}},
                {'pids': {'required': True, 'keys': [
                    {'pid': {'required': True, 'keys': [
                        {'id': {'required': True, 'keys': [], 'type': int}},
                        {'name': {'required': True, 'keys': [], 'type': str}},
                        {'packing': {'required': True, 'keys': [], 'type': str}},
                        {'modules': {'required': True, 'keys': [
                            {'module': {'required': True, 'keys': [
                            ]}},
                        ]}},
                        {'states': {'required': True, 'keys': [
                            {'state': {'required': True, 'keys': [
                                {'name': {'required': True, 'keys': [], 'type': str}},
                                {'value': {'required': True, 'keys': [], 'type': None}},
                            ]}},
                        ]}},
                    ]}},
                ]}},
            ]},
        },
    ]

    try:
        result = check_required_keys(dict(config), required_keys)
        check_unsupported(dict(config), required_keys)
    except FailedInitialization:
        raise
    except Exception as e:
        raise FailedInitialization(f"Unexpected exception: {e}")
    return config if result else None


def read_config():
    """Open the YAML configuration file and check the contents"""
    try:
        yaml.FullLoader.add_constructor('!secret', secret_yaml)
        yaml_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_YAML)
        config = config_from_yaml(data=yaml_file, read_from_file=True)
        if config:
            config = check_config(config)
        return config
    except ConfigError as e:
        raise FailedInitialization(f"ConfigError exception: {e}")
    except FailedInitialization:
        raise
    except Exception as e:
        error_message = buildYAMLExceptionString(exception=e, file=yaml_file)
        raise FailedInitialization(f"Unexpected exception: {error_message}")


def retrieve_options(config, key, option_list) -> dict:
    """Retrieve requested options."""
    if key not in config.keys():
        return {}

    errors = False
    options = dict(config[key])
    for option, value in option_list.items():
        required = value.get('required', None)
        type = value.get('type', None)
        if required:
            if option not in options.keys():
                _LOGGER.error(f"Missing required option in YAML file: '{option}'")
                errors = True
            else:
                v = options.get(option, None)
                if not isinstance(v, type):
                    _LOGGER.error(f"Expected type '{type}' for option '{option}'")
                    errors = True
    if errors:
        raise FailedInitialization(f"One or more errors detected in '{key}' YAML options")
    return options


if __name__ == '__main__':
    if sys.version_info[0] >= 3 and sys.version_info[1] >= 8:
        config = read_config()
    else:
        print("python 3.8 or better required")
