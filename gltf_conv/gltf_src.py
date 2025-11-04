import copy
import json
import os
from pathlib import Path
import subprocess

from gltf_conv.utils import ezlog


# .\gltfpack.exe -i .\NewSponza_Main_glTF_003.gltf -o .\NewSponza_Main_glTF_003_comp.gltf -km -ke -tr -v -vtf -se 0.001 -si 0.5 -slb
# .\gltfpack.exe -i .\NewSponza_Curtains_glTF.gltf -o .\NewSponza_Curtains_glTF_comp.gltf -km -ke -tr -v -vtf -se 0.001 -si 0.5 -slb

class GLTFSrc:
    def __init__( self, src_dir: str, src: dict, verbose: bool ):
        self.file = src[ 'file' ]
        self.name = src.get( 'name', self.file )
        self.src_dir = src_dir

        inp = os.path.join( src_dir, self.file + '.gltf' ).replace( '\\', '/' )
        out = os.path.join( src_dir, self.file + '.comp.gltf' ).replace( '\\', '/' )

        args = [
            'gltfpack.exe',
            '-i', inp,
            '-o', out,
            '-km',
            # '-ke',
            '-kn',
            # '-mm',
            '-tr', '-vtf', '-vnf', '-slb',
            '-kv',
            '-se', str( src.get( 'se', 0.01 ) ),
            '-si', str( src.get( 'si', 1.0 ) ),
            '-noq'
        ]

        if verbose:
            args.append( '-v' )

        ezlog.info( f'Compressing "{inp}"' )

        try:
            ret = subprocess.run( args, check=False )
        except FileNotFoundError as e:
            raise ValueError( 'gltfpack.exe not found! Please make sure it is added to PATH!' ) from e

        if ret.returncode == 0:
            ezlog.info( f'Writing to "{out}"!' )
        else:
            raise ValueError( f'gltfpack.exe returned with error code {ret.returncode}')

        with open( out, encoding='utf-8' ) as f:
            self.data = json.load( f )

    @property
    def src_materials( self ) -> list[dict]:
        return self.data[ 'materials' ]

    @property
    def src_textures( self ) -> list[dict]:
        return self.data[ 'textures' ]

    @property
    def src_images( self ) -> list[dict]:
        return self.data[ 'images' ]

    def texture_idx2uri( self, index: int | None ) -> Path | None:
        if index is None:
            return None
        texture_src = self.src_textures[ index ][ 'source' ]
        image_uri = self.src_images[ texture_src ][ 'uri' ]
        return Path( os.path.join( self.src_dir, image_uri ) )

    def as_dxtf( self ):
        dxtf = copy.deepcopy( self.data )

        dxtf.pop( 'textures', None )
        dxtf.pop( 'images', None )
        dxtf.pop( 'samples', None )

        for b in dxtf[ 'buffers' ]:
            b[ 'uri' ] = b[ 'uri' ].replace( '.comp.bin', '.dxtf_mdl' )

        for mat in dxtf[ 'materials' ]:
            for k in list( mat.keys() ):
                if k != 'name':
                    mat.pop( k )

        return dxtf
