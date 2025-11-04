from dataclasses import dataclass, asdict
import json
import os
from pathlib import Path
import subprocess
from typing import Optional

from gltf_conv.schema_registry import get_validator
from gltf_conv.dxspec_material_utils import (
    DXSpec_Mat2TextureContainer,
    DXSpec_Material,
    DXSpec_TextureKey,
    DXSpec_TextureSpecContainer
)
from gltf_conv.utils import BlendModes, DDSFormat, ezlog, format_get_channels


@dataclass
class DXTF_DiffuseTexture:
    texture: str
    strength: tuple[float, float, float, float]

@dataclass
class DXTF_NormalTexture:
    texture: str
    strength: float

@dataclass
class DXTF_ORMTexture:
    texture: str
    occlusion_strength: float
    roughness_strength: float
    metalness_strength: float

@dataclass
class DXTF_EmissiveTexture:
    texture: str
    strength: tuple[float, float, float]

@dataclass
class DXTF_Material:
    name: str

    diffuse: DXTF_DiffuseTexture
    normal: DXTF_NormalTexture
    orm: DXTF_ORMTexture
    emissive: Optional[DXTF_EmissiveTexture]

    blend_mode: BlendModes
    alpha_cutoff: Optional[float]
    double_sided: bool

    def __init__(
        self,
        src: DXSpec_Material,
        tex: DXSpec_Mat2TextureContainer
    ):
        self.name = src.name
        self.diffuse = DXTF_DiffuseTexture( tex.diffuse[self.name], src.diffuse.strength )
        self.normal = DXTF_NormalTexture( tex.normal[self.name], src.normal.scale )
        self.orm = DXTF_ORMTexture( tex.orm[self.name], src.orm.occlusion.strength, src.orm.roughness.strength, src.orm.metalness.strength )

        if src.emissive:
            self.emissive = DXTF_EmissiveTexture( tex.emissive[self.name], src.emissive.factor )
        else:
            self.emissive = None

        self.blend_mode = src.blend_mode
        self.alpha_cutoff = src.alpha_cutoff
        self.double_sided = src.double_sided

    def as_dict( self ):
        out = asdict( self )

        if self.emissive is None:
            out.pop( 'emissive' )

        if self.blend_mode != 'MASK':
            out.pop( 'alpha_cutoff' )

        return out

    def as_nameless_dict( self ):
        out = self.as_dict()
        out.pop( 'name' )
        return out

    @classmethod
    def list_from_texture_specs(
        cls,
        dxspec_material_db: dict[str, DXSpec_Material],
        dxspec_mat2textures_db: DXSpec_Mat2TextureContainer,
        verbose: bool
    ) -> list['DXTF_Material']:

        ezlog.info( 'Creating DXTF material database' )

        dxtf_materials_db: list[DXTF_Material] = [ cls( v, dxspec_mat2textures_db ) for v in dxspec_material_db.values() ]

        if verbose:
            ezlog.debug( 'DXTF materials:', dxtf_materials_db )

        ezlog.info( f'Created {len(dxtf_materials_db)} DXTF materials!' )

        return dxtf_materials_db

    @classmethod
    def write_materials( cls, dxtf_materials_db: list['DXTF_Material'], dx_materials_path: str ):

        ezlog.info( f'Writing DXTF materials to: "{dx_materials_path}"' )

        os.makedirs( dx_materials_path, exist_ok=True )

        validator = get_validator( 'dxtf_mat.schema.json' )

        for mat in dxtf_materials_db:
            mat_path = os.path.join( dx_materials_path, mat.name + '.dxtf_mat' )
            with open( mat_path, 'w', encoding='utf-8' ) as f:
                mat_dict = json.loads( json.dumps( mat.as_nameless_dict() ) )
                validator.validate( mat_dict )
                json.dump( mat_dict, f, indent=2 )

        ezlog.info( f'Wrote {len(dxtf_materials_db)} DXTF materials!' )

@dataclass
class DXTF_Tex2DDS:
    format: DDSFormat
    srgb: str # TODO: make literal
    output_path: Path
    channels: list[tuple[Path | None, str]]
    resolution: tuple[int, int]

    def __init__( self, texture_path: str, texture_key: DXSpec_TextureKey, out_path: str, srgb: str ):
        self.format = texture_key[1]
        self.output_path = Path( os.path.join( out_path, texture_path ) )
        self.resolution = texture_key[2]
        self.srgb = srgb
        self.channels = []

        for tex, swizzle in texture_key[0]:
            for s in swizzle:
                self.channels.append( ( tex if s in 'rgba' else None, s ) )

        expected_channels = format_get_channels( self.format )

        if actual_channels := len( self.channels ) > expected_channels:
            raise ValueError( f'Format {self.format} requires {expected_channels} channels but got {actual_channels}!' )

        while len( self.channels ) < expected_channels:
            self.channels.append( ( None, '1' ) )

    def as_dict( self ):
        return {
            'output_path': str( self.output_path ).replace( '\\', '/' ),
            'srgb': self.srgb,
            'format': self.format,
            'resolution': list( self.resolution ),
            'channels': [ { 'file': str( f ).replace( '\\', '/' ) if f else None, 'src': s } for f, s in self.channels ],

        }

    def as_nameless_dict( self ):
        out = self.as_dict()
        out.pop( 'output_path' )
        return out

    @classmethod
    def list_from_texture_specs(
        cls,
        dxspec_texture_outs_db: DXSpec_TextureSpecContainer,
        dx_textures_path: str,
        tex2dds_settings: dict,
        verbose: bool
    ) -> list['DXTF_Tex2DDS']:
        str2key = dxspec_texture_outs_db.str2key

        ezlog.info( 'Creating DDS texture database' )

        dxtf_tex2dds_db: list[DXTF_Tex2DDS] = []
        for texture_outs, key in [
            ( str2key.diffuse, 'diffuse' ),
            ( str2key.normal, 'normal' ),
            ( str2key.orm, 'orm' ),
            ( str2key.emissive, 'emissive' )
        ]:
            for k, v in texture_outs.items():
                if '$' in k:
                    ezlog.warning( f'Skipping creation of DXTF_Tex2DDS for "{k}"' )
                else:
                    dxtf_tex2dds_db.append( cls( k, v, dx_textures_path, tex2dds_settings[key]['srgb'] ) )

        if verbose:
            ezlog.debug( 'DDS textures:', dxtf_tex2dds_db )
        ezlog.info( f'Created {len(dxtf_tex2dds_db)} Tex2DDS specifications!' )

        return dxtf_tex2dds_db

    @classmethod
    def write_textures( cls, dxtf_tex2dds_db: list['DXTF_Tex2DDS'], dx_textures_path: str, verbose: bool ):
        ezlog.info( f'Writing DDS textures to: "{dx_textures_path}"' )
        os.makedirs( dx_textures_path, exist_ok=True )

        validator = get_validator( 'tex2dds.schema.json' )

        textures = []
        for tex in dxtf_tex2dds_db:
            tex_dict = tex.as_dict()
            validator.validate( tex_dict )
            textures.append( tex_dict )

        arguments = [ 'tex2dds.exe' ]

        if verbose:
            arguments.append( '-v' )

        subprocess.run(
            arguments,
            input=json.dumps( textures ),
            check=True,
            text=True,
            stdout=None if verbose else subprocess.DEVNULL
        )
        ezlog.info( f'Wrote {len(dxtf_tex2dds_db)} DDS textures!' )
