from dataclasses import dataclass
from typing import Optional

from gltf_conv.utils import init


@dataclass
class GLTF_TextureInfo:
    index: int

    def __init__( self, obj: dict ):
        self.index = obj[ 'index' ]

@dataclass
class GLTF_NormalTexture( GLTF_TextureInfo ):
    scale: float

    def __init__( self, obj: dict ):
        super().__init__( obj )
        self.scale = obj.get( 'scale', 1.0 )


@dataclass
class GLTF_OcclusionTexture( GLTF_TextureInfo ):
    strength: float

    def __init__( self, obj: dict ):
        super().__init__( obj )
        self.strength = obj.get( 'strength', 1.0 )

@dataclass
class GLTF_PBRMetallicRoughness:
    base_color_factor: tuple[float, float, float, float]
    base_color_texture: Optional[GLTF_TextureInfo]

    metallic_factor: Optional[float]
    roughness_factor: Optional[float]
    metallic_roughness_texture: Optional[GLTF_TextureInfo]

    def __init__( self, obj: dict ):
        self.base_color_factor = tuple( obj.get( 'baseColorFactor', [ 1.0, 1.0, 1.0, 1.0 ] ) )
        self.base_color_texture = init( GLTF_TextureInfo, obj, 'baseColorTexture' )

        self.metallic_factor = init( float, obj, 'metallicFactor' )
        self.roughness_factor = init( float, obj, 'roughnessFactor' )
        self.metallic_roughness_texture = init( GLTF_TextureInfo, obj, 'metallicRoughnessTexture' )

@dataclass
class GLTF_Material:
    name: str
    pbr_metallic_roughness: Optional[GLTF_PBRMetallicRoughness]
    normal_texture: Optional[GLTF_NormalTexture]
    occlusion_texture: Optional[GLTF_OcclusionTexture]
    emissive_texture: Optional[GLTF_TextureInfo]
    emissive_factor: Optional[tuple[float, float, float]]
    alpha_mode: str
    alpha_cutoff: Optional[float]
    double_sided: bool

    def __init__( self, obj ):
        self.name = obj[ 'name' ]
        self.pbr_metallic_roughness = init( GLTF_PBRMetallicRoughness, obj, 'pbrMetallicRoughness' )
        self.normal_texture = init( GLTF_NormalTexture, obj, 'normalTexture' )
        self.occlusion_texture = init( GLTF_OcclusionTexture, obj, 'occlusionTexture' )
        self.emissive_texture = init( GLTF_TextureInfo, obj, 'emissiveTexture' )
        self.emissive_factor = init( tuple[float, float, float], obj, 'emissiveFactor' )
        self.alpha_mode = obj.get( 'alphaMode', 'OPAQUE' )
        self.alpha_cutoff = init( float, obj, 'alphaCuttoff', 0.5 if self.alpha_mode == 'MASK' else None )
        self.double_sided = obj.get( 'doubleSided', False )