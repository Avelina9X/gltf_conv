
from dataclasses import dataclass, field
import json
import os

from gltf_conv.schema_registry import get_validator

@dataclass
class ConvSpec:
    name: str
    src_dir: str
    srcs: list[dict]

    out_dir: str

    tex2dds_settings: dict

    dx_textures_subdir: str = field( default='textures' )
    dx_materials_subdir: str = field( default='materials' )

    material_spec_overrides: dict = field( default_factory=dict )


    @property
    def dx_textures_path( self ) -> str:
        return os.path.join( self.out_dir, self.dx_textures_subdir ).replace( '\\', '/' )

    @property
    def dx_materials_path( self ) -> str:
        return os.path.join( self.out_dir, self.dx_materials_subdir ).replace( '\\', '/' )

    @classmethod
    def from_dict( cls, obj: dict ) -> 'ConvSpec':
        validator = get_validator( 'conv_spec.schema.json' )
        validator.validate( obj )
        return cls( **obj )

    @classmethod
    def from_file( cls, file: str ) -> 'ConvSpec':
        with open( file, encoding='utf-8' ) as f:
            return cls.from_dict( json.load( f ) )