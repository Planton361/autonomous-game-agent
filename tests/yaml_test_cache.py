"""Per-fixture reuse of pure YAML work; no filesystem or Vault state cached."""

import pickle
from copy import deepcopy

import yaml

from fh_agent.research_atlas.validator import UniqueKeyLoader

# Independent real-parser oracles, captured before any fixture installs reuse.
parse_yaml = yaml.load
serialize_yaml = yaml.safe_dump


class YamlReuse:
    def __init__(self, load, safe_dump):
        self._load = load
        self._safe_dump = safe_dump
        self._parsed = {}
        self._serialized = {}

    def load(self, stream, Loader):  # noqa: N803 -- PyYAML keyword contract
        if (Loader is not UniqueKeyLoader and Loader is not yaml.SafeLoader) or type(
            stream
        ) not in {str, bytes}:
            return self._load(stream, Loader=Loader)
        # Include mutable constructor/resolver configuration, not only class identity.
        try:
            configuration = pickle.dumps(
                (
                    Loader.yaml_constructors,
                    Loader.yaml_multi_constructors,
                    Loader.yaml_implicit_resolvers,
                    Loader.yaml_path_resolvers,
                ),
                protocol=5,
            )
        except (TypeError, AttributeError, pickle.PicklingError):
            return self._load(stream, Loader=Loader)
        key = (type(stream), stream, Loader, configuration)
        if key not in self._parsed:
            self._parsed[key] = self._load(stream, Loader=Loader)
        # Deep copies preserve alias structure inside one result, never across calls.
        return deepcopy(self._parsed[key])

    def safe_dump(self, data, stream=None, **kwargs):
        if stream is not None:
            return self._safe_dump(data, stream=stream, **kwargs)
        try:
            # Preserve types, order, aliases and all serializer options.
            key = pickle.dumps(
                (
                    data,
                    kwargs,
                    yaml.SafeDumper,
                    yaml.SafeDumper.yaml_representers,
                    yaml.SafeDumper.yaml_multi_representers,
                    yaml.SafeDumper.yaml_implicit_resolvers,
                    yaml.SafeDumper.yaml_path_resolvers,
                ),
                protocol=5,
            )
        except (TypeError, AttributeError, pickle.PicklingError):
            return self._safe_dump(data, **kwargs)
        if key not in self._serialized:
            self._serialized[key] = self._safe_dump(data, **kwargs)
        return self._serialized[key]  # immutable text
