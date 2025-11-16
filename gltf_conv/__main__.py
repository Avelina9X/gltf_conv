from importlib import resources
import json
import os
import argparse
import copy
import shutil
from typing import Literal

from gltf_conv import __version__
from gltf_conv.conv_spec import ConvSpec
from gltf_conv.dxspec_material_utils import (
    DXSpec_Mat2TextureContainer,
    DXSpec_Material,
    DXSpec_TextureKeysContainer,
    DXSpec_TextureSpecContainer,
)
from gltf_conv.dxtf_material_utils import DXTF_Material, DXTF_Tex2DDS
from gltf_conv.gltf_material_utils import GLTF_Material
from gltf_conv.gltf_src import GLTFSrc
from gltf_conv.schema_registry import get_validator
from gltf_conv.utils import ezlog, recursive_overwrite

def parse_materials( gltf_srcs: list[GLTFSrc], conv_spec: ConvSpec ):

    # Create mutable copy of material_spec_overrides
    material_spec_overrides: dict[str, dict] = copy.deepcopy( conv_spec.material_spec_overrides )

    # Pop the global override (if exists)
    material_spec_override_global: dict = material_spec_overrides.pop( '*', {} )

    # Create empty container for dxspec materials
    dxspec_material_db: dict[str, DXSpec_Material] = {}

    # Iterate over sources
    for gltf_src in gltf_srcs:
        ezlog.info( f'Parsing {len(gltf_src.src_materials)} materials from {gltf_src.file}' )
        # Iterate over all materials in source
        for i, mat_src in enumerate( gltf_src.src_materials ):

            # Create a GLTF Material instance
            gltf_mat = GLTF_Material( mat_src, i )
            mat_name = gltf_mat.name

            # If material not already in db create a DXSpec Material and add to material db
            if mat_name not in dxspec_material_db:
                # Pop override
                curr_override = material_spec_overrides.pop( mat_name, {} )

                # Combine globals
                recursive_overwrite( curr_override, material_spec_override_global )

                # Add to material db
                try:
                    dxspec_material_db[mat_name] = DXSpec_Material( gltf_mat, gltf_src, curr_override )
                except ValueError as e:
                    raise ValueError( f'Error while creating DXSpec_Material for material {mat_name}!' ) from e

            # Otherwise warn user that material exists
            else:
                ezlog.warning(
                    f'{mat_name} already specified in {dxspec_material_db[mat_name].src_file}, '
                    f'[bold]skipping[/bold] version from {gltf_src.file}!'
                )

    # Ensure no material spec overrides remain
    if len( material_spec_overrides ) != 0:
        remainder = ', '.join( material_spec_overrides.keys() )
        raise ValueError( f'Not all material spec overrides consumed! Unknown materials: {remainder}')

    ezlog.info( f'Parsed {len(dxspec_material_db)} unique GLTF materials!' )

    return dxspec_material_db

def write_manifest( conv_spec: ConvSpec, gltf_srcs: list[GLTFSrc] ):
    ezlog.info( f'Writing DXTF manifest to "{conv_spec.out_dir}"')
    manifest_path = os.path.join( conv_spec.out_dir, conv_spec.name + '.dxtf_mdm' )
    manifest_dict = {
        'name': conv_spec.name,
        'textures_path': conv_spec.dx_textures_subdir,
        'materials_path': conv_spec.dx_materials_subdir,
        'models' : []
    }
    for gltf_src in gltf_srcs:
        manifest_dict['models'].append( { 'name': gltf_src.name, 'file': gltf_src.file + '.dxtf_mds' } )
    with open( manifest_path, 'w', encoding='utf-8' ) as f:
        validator = get_validator( 'dxtf_mdm.schema.json' )
        validator.validate( manifest_dict )
        json.dump( manifest_dict, f, indent=2 )
    ezlog.info( f'Wrote manifest to "{conv_spec.name}.dxtf_mdm"!' )

def main( file_path: str, verbose: list[str], model_move: Literal['copy', 'move'] ):

    # Load conversion spec
    conv_spec = ConvSpec.from_file( file_path )

    # Set CWD to file_path's parent
    os.chdir( cwd := os.path.dirname( os.path.abspath( file_path ) ).replace( '\\', '/' ) )
    ezlog.warning( f'Setting CWD to "{cwd}"!\n' )

    # Iterate over all .gltf files and construct a src object
    gltf_srcs = [ GLTFSrc( conv_spec.src_dir, src, 'gltfpack' in verbose ) for src in conv_spec.srcs ]
    print()

    # Parse all GLTF materials and return a dict of dxspec materials
    dxspec_material_db = parse_materials( gltf_srcs, conv_spec )
    print()

    # Create bi-map of image texture assembly keys to material names
    dxspec_texture_keys_db = DXSpec_TextureKeysContainer( dxspec_material_db )

    # Create bi-map of image texture assembly keys to DDS texture filenames
    dxspec_texture_outs_db = DXSpec_TextureSpecContainer( dxspec_texture_keys_db )

    # Create map of material names to DDS texture filenames
    dxspec_mat2textures_db = DXSpec_Mat2TextureContainer( dxspec_texture_keys_db, dxspec_texture_outs_db )

    # Create list of DXTF materials from dxspec materials and material name map
    dxtf_materials_db = DXTF_Material.list_from_texture_specs( dxspec_material_db, dxspec_mat2textures_db, 'dxtf_mats' in verbose )

    # Write DXTF materials to disk
    DXTF_Material.write_materials( dxtf_materials_db, conv_spec.dx_materials_path )
    print()

    # Create list of Tex2DDS objects from texture specs and the destination path
    dxtf_tex2dds_db = DXTF_Tex2DDS.list_from_texture_specs( dxspec_texture_outs_db, conv_spec.dx_textures_path, conv_spec.tex2dds_settings, 'tex2dds_spec' in verbose )
    print()

    # Write DDS textures to disk
    DXTF_Tex2DDS.write_textures( dxtf_tex2dds_db, conv_spec.dx_textures_path, 'tex2dds' in verbose )
    print()

    ezlog.info( f'Writing DXTF meshes to "{conv_spec.out_dir}"' )
    for gltf_src in gltf_srcs:
        dxtf_path = os.path.join( conv_spec.out_dir, gltf_src.file + '.dxtf_mds' )
        with open( dxtf_path, 'w', encoding='utf-8' ) as f:
            json.dump( gltf_src.as_dxtf(), f )
            ezlog.info( f'Wrote "{gltf_src.name}" struct to "{gltf_src.file}.dxtf_mds"!' )
        shutil.copy(
            os.path.join( gltf_src.src_dir, gltf_src.file + '.comp.bin' ),
            os.path.join( conv_spec.out_dir, gltf_src.file + '.dxtf_mdl' ),
        )
        ezlog.info( f'Wrote "{gltf_src.name}" binary to "{gltf_src.file}.dxtf_mdl"!' )
    print()

    write_manifest( conv_spec, gltf_srcs )
    print()



if __name__ == '__main__':

    class VerboseAction( argparse.Action ):
        """ Returns a list of all choices if argument specified with no values """

        def __call__( self, parser, namespace, values, option_string=None ):
            assert self.choices
            if ( values is None ) or ( isinstance( values, list ) and len( values ) == 0 ):
                setattr( namespace, self.dest, list( self.choices ) )
            elif isinstance( values, list ):
                for v in values:
                    if v not in self.choices:
                        raise ValueError( f'Unknown verbose argument {v}! Must be one of {self.choices}' )
                setattr( namespace, self.dest, values )
            else:
                raise ValueError( f'Unknown verbose argument {values}!' )

    class SchemaAction( argparse.Action ):
        def __call__( self, parser, namespace, values, option_string=None ):
            if values is None:
                print( 'available schemas are:' )
                for schema in resources.files( 'gltf_conv.schemas' ).iterdir():
                    print( f' - {schema.name}' )
            else:
                if not isinstance( values, str ):
                    raise ValueError( 'Argument of --schema must be a string!' )

                resource = resources.files( 'gltf_conv.schemas' ).joinpath( values )

                if resource.is_file():
                    with resource.open( 'r', encoding='utf-8' ) as f:
                        print( f.read() )
                else:
                    raise ValueError( f'Schema {values} not found!' )

            parser.exit()

    arg_parser = argparse.ArgumentParser(
        prog='gltf_conv',
        description=f'Tool for converting glTF2.0 files to the DXTF format. Version {__version__}'
    )

    arg_parser.add_argument( 'file', type=str, help='path to json file specifying conversion configuration.' )
    arg_parser.add_argument( '-m', '--model', type=str, choices=[ 'copy', 'move' ], default='copy', help='if the compressed GLTF .bin should be copied or moved' )

    arg_parser.add_argument(
        '-v', '--verbose',
        nargs="*",
        action=VerboseAction,
        metavar='component',
        default=[],
        choices=( 'gltfpack', 'dxtf_mats', 'tex2dds_spec', 'tex2dds' ),
        help='enables verbose printing, optionally only for the components specified or everything when unspecified.'
    )

    arg_parser.add_argument( '--version', action='version', version=__version__ )

    arg_parser.add_argument(
        '--schema',
        nargs='?',
        metavar='name',
        action=SchemaAction,
        help='prints the names of all schemas, or prints the specified schema to console' )

    arguments = arg_parser.parse_args()
    main( arguments.file, arguments.verbose, arguments.model )
