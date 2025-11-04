import importlib.resources as resources
import json

from jsonschema import validators
from referencing import Registry, Resource

import gltf_conv.schemas as schemas

def _create_registry():
    schema_store: dict[str, dict] = {}
    for r in resources.files( schemas ).iterdir():
        with r.open() as f:
            s = json.load( f )
            schema_store[s['$id']] = s
    return Registry( { k: Resource.from_contents( v ) for k, v in schema_store.items() } )

_SCHEMA_REGISTRY = _create_registry()

def get_validator( schema: str ):
    ValidatorClass = validators.validator_for( _SCHEMA_REGISTRY[schema].contents )
    return ValidatorClass( _SCHEMA_REGISTRY[schema].contents, registry=_SCHEMA_REGISTRY )