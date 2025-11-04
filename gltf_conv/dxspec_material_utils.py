from dataclasses import dataclass, field
from pathlib import Path
from types import NoneType
from typing import ClassVar, DefaultDict, Optional, TypeAlias

from gltf_conv.gltf_material_utils import GLTF_Material, GLTF_NormalTexture, GLTF_OcclusionTexture, GLTF_PBRMetallicRoughness
from gltf_conv.gltf_src import GLTFSrc
from gltf_conv.utils import BlendModes, DDSFormat, modulate


DXSpec_TextureKey: TypeAlias = tuple[tuple[tuple[Optional[Path], str], ...], DDSFormat, tuple[int, int]]

@dataclass
class DXSpec_TextureInfo:
    uri: Path | None
    swizzle: str

@dataclass
class DXSpec_NormalTexture( DXSpec_TextureInfo ):
    scale: float

    #pylint: disable=W0231
    def __init__( self, obj: GLTF_NormalTexture | None, src: GLTFSrc, override: dict | None ):
        if obj is None:
            self.uri = None
            self.swizzle = 'hh'
            self.scale = 1.0
        else:
            self.uri = src.texture_idx2uri( obj.index )
            self.swizzle = 'rg'
            self.scale = obj.scale

        if override:
            if 'uri' in override:
                self.uri = override.pop( 'uri' )
                self.swizzle = 'rg'
            if 'scale' in override:
                self.scale = modulate( self.scale, override.pop( 'scale' ) )

            if len( override ) > 0:
                raise ValueError( f'Unknown overrides: {override}' )


    def get_texture_key( self, resolution: tuple[int, int] ) -> DXSpec_TextureKey:
        return ( ( ( self.uri, self.swizzle ), ), 'BC5_UNORM', resolution )

@dataclass
class DXSpec_OcclusionTexture( DXSpec_TextureInfo ):
    strength: float

    #pylint: disable=W0231
    def __init__( self, obj: GLTF_OcclusionTexture | None, src: GLTFSrc, override: dict | None ):
        if obj is None:
            self.uri = None
            self.swizzle = '1'
            self.strength = 1.0
        else:
            self.uri = src.texture_idx2uri( obj.index )
            self.swizzle = 'r'
            self.strength = obj.strength

        if override:
            if 'uri' in override:
                self.uri = override.pop( 'uri' )
                self.swizzle = 'r'
            if 'strength' in override:
                self.strength = modulate( self.strength, override.pop( 'strength' ) )

            if len( override ) > 0:
                raise ValueError( f'Unknown overrides: {override}' )

@dataclass
class DXSpec_RoughnessTexture( DXSpec_TextureInfo ):
    strength: float

    default_strength: ClassVar[float] = 1.0

    #pylint: disable=W0231
    def __init__( self, obj: GLTF_PBRMetallicRoughness | None, src: GLTFSrc, override: dict | None ):
        if obj is None:
            self.uri = None
            self.swizzle = '1'
            self.strength = self.default_strength
        else:
            texture = obj.metallic_roughness_texture
            if texture:
                self.uri = src.texture_idx2uri( texture.index )
                self.swizzle = 'g'
                self.strength = obj.roughness_factor or 1.0
            else:
                self.uri = None
                self.swizzle = '1'
                self.strength = obj.roughness_factor or self.default_strength

        if override:
            if 'uri' in override:
                self.uri = override.pop( 'uri' )
                self.swizzle = 'g'
            if 'strength' in override:
                self.strength = modulate( self.strength, override.pop( 'strength' ) )

            if len( override ) > 0:
                raise ValueError( f'Unknown overrides: {override}' )

@dataclass
class DXSpec_MetalnessTexture( DXSpec_TextureInfo ):
    strength: float

    default_strength: ClassVar[float] = 0.0

    #pylint: disable=W0231
    def __init__( self, obj: GLTF_PBRMetallicRoughness | None, src: GLTFSrc, override: dict | None ):
        if obj is None:
            self.uri = None
            self.swizzle = '1'
            self.strength = self.default_strength
        else:
            texture = obj.metallic_roughness_texture
            if texture:
                self.uri = src.texture_idx2uri( texture.index )
                self.swizzle = 'b'
                self.strength = obj.metallic_factor or 1.0
            else:
                self.uri = None
                self.swizzle = '1'
                self.strength = obj.metallic_factor or self.default_strength

        if override:
            if 'uri' in override:
                self.uri = override.pop( 'uri' )
                self.swizzle = 'b'
            if 'strength' in override:
                self.strength = modulate( self.strength, override.pop( 'strength' ) )

            if len( override ) > 0:
                raise ValueError( f'Unknown overrides: {override}' )

@dataclass
class DXSpec_DiffuseTexture( DXSpec_TextureInfo ):
    strength: tuple[float, float, float, float]

    #pylint: disable=W0231
    def __init__( self, obj: GLTF_PBRMetallicRoughness | None, alpha_mode: str, src: GLTFSrc, override: dict | None ):
        if obj is None:
            self.uri = None
            self.swizzle = '1111'
            self.strength = ( 1.0, 1.0, 1.0, 1.0 )
        else:
            texture = obj.base_color_texture
            if texture:
                self.uri = src.texture_idx2uri( texture.index )
                self.swizzle = 'rgb1' if alpha_mode == 'OPAQUE' else 'rgba'
                self.strength = obj.base_color_factor
            else:
                self.uri = None
                self.swizzle = '1111'
                self.strength = obj.base_color_factor

        if override:
            if 'uri' in override:
                self.uri = override.pop( 'uri' )
                self.swizzle = 'rgb1' if alpha_mode == 'OPAQUE' else 'rgba'
            if 'strength' in override:
                self.strength = modulate( self.strength, override.pop( 'strength' ) )

            if len( override ) > 0:
                raise ValueError( f'Unknown overrides: {override}' )

    def get_texture_key( self, resolution: tuple[int, int] ) -> DXSpec_TextureKey:
        return (
            ( ( self.uri, self.swizzle ), ),
            'BC1_UNORM_SRGB' if self.swizzle[-1] == '1' else 'BC3_UNORM_SRGB',
            resolution
        )

@dataclass
class DXSpec_OcclusionRoughnessMetalness:
    occlusion: DXSpec_OcclusionTexture
    roughness: DXSpec_RoughnessTexture
    metalness: DXSpec_MetalnessTexture

    def __init__( self, obj: GLTF_Material, src: GLTFSrc, override: dict | None ):
        override = override or {}
        self.occlusion = DXSpec_OcclusionTexture( obj.occlusion_texture, src, override.pop( 'occlusion', None ) )
        self.roughness = DXSpec_RoughnessTexture( obj.pbr_metallic_roughness, src, override.pop( 'roughness', None ) )
        self.metalness = DXSpec_MetalnessTexture( obj.pbr_metallic_roughness, src, override.pop( 'metalness', None ) )

    def get_texture_key( self, resolution: tuple[int, int] ) -> DXSpec_TextureKey:
        texs: list[DXSpec_TextureInfo] = [ self.occlusion, self.roughness, self.metalness ]
        return ( tuple( ( tex.uri, tex.swizzle ) for tex in texs ), 'BC7_UNORM', resolution )

@dataclass
class DXSpec_EmissiveTexture( DXSpec_TextureInfo ):
    factor: tuple[float, float, float]

    #pylint: disable=W0231
    def __init__( self, obj: GLTF_Material, src: GLTFSrc, override: dict | None ):
        texture = obj.emissive_texture
        factor = obj.emissive_factor

        if texture or factor:
            self.uri = src.texture_idx2uri( texture.index ) if texture else None
            self.swizzle = 'rgb' if texture else '111'
            self.factor = factor or ( 1.0, 1.0, 1.0 )
        elif override is None:
            raise ValueError( 'Cannot construct emissive texture if neither texture nor factor specified!' )

        if override:
            if 'uri' in override:
                self.uri = override.pop( 'uri' )
                self.swizzle = 'rgb'
            if 'factor' in override:
                self.factor = modulate( self.factor, override.pop( 'factor' ) )

            if len( override ) > 0:
                raise ValueError( f'Unknown overrides: {override}' )

    def get_texture_key( self, resolution: tuple[int, int] ) -> DXSpec_TextureKey:
        return ( ( ( self.uri, self.swizzle ), ), 'BC6H_UF16', resolution ) # TODO: yay or nay?

@dataclass
class DXSpec_Material:
    name: str

    diffuse: DXSpec_DiffuseTexture
    normal: DXSpec_NormalTexture
    orm: DXSpec_OcclusionRoughnessMetalness
    emissive: Optional[DXSpec_EmissiveTexture]

    blend_mode: BlendModes
    alpha_cutoff: Optional[float]
    double_sided: bool

    resolution: tuple[int, int]

    def __init__( self, obj: GLTF_Material, src: GLTFSrc, override: dict | None ):
        override = override or {}

        self.blend_mode = override.pop( 'blend_mode', obj.alpha_mode )
        assert self.blend_mode in [ 'OPAQUE', 'MASK', 'BLEND' ]

        self.alpha_cutoff = override.pop( 'alpha_cutoff', obj.alpha_cutoff )
        assert isinstance( self.alpha_cutoff, int | float | NoneType )

        self.double_sided = override.pop( 'double_sided', obj.double_sided )
        assert isinstance( self.double_sided, bool )

        self.name = obj.name
        self.src_file = src.file

        self.diffuse = DXSpec_DiffuseTexture( obj.pbr_metallic_roughness, self.blend_mode, src, override.pop( 'diffuse', None ) )
        self.normal = DXSpec_NormalTexture( obj.normal_texture, src, override.pop( 'normal', None ) )
        self.orm = DXSpec_OcclusionRoughnessMetalness( obj, src, override )

        if obj.emissive_texture or obj.emissive_factor or 'emissive' in override:
            self.emissive = DXSpec_EmissiveTexture( obj, src, override.pop( 'emissive', None ) )
        else:
            self.emissive = None

        self.resolution = tuple( override.pop( 'resolution', [ -1, -1 ] ) )
        # TODO: more exception handling

        if len( override ) > 0:
            raise ValueError( f'Unknown overrides: {override}' )


    def get_diffuse_texture_key( self ) -> DXSpec_TextureKey | None:
        return self.diffuse.get_texture_key( self.resolution )

    def get_normal_texture_key( self ) -> DXSpec_TextureKey | None:
        return self.normal.get_texture_key( self.resolution )

    def get_orm_texture_key( self ) -> DXSpec_TextureKey | None:
        return self.orm.get_texture_key( self.resolution )

    def get_emissive_texture_key( self ) -> DXSpec_TextureKey | None:
        return self.emissive.get_texture_key( self.resolution ) if self.emissive else None

class DXSpec_TextureKeysContainer:
    @dataclass
    class _Key2List:
        diffuse: DefaultDict[DXSpec_TextureKey, list[str]] = field( default_factory=lambda: DefaultDict( list[str] ) )
        normal: DefaultDict[DXSpec_TextureKey, list[str]] = field( default_factory=lambda: DefaultDict( list[str] ) )
        orm: DefaultDict[DXSpec_TextureKey, list[str]] = field( default_factory=lambda: DefaultDict( list[str] ) )
        emissive: DefaultDict[DXSpec_TextureKey, list[str]] = field( default_factory=lambda: DefaultDict( list[str] ) )

    @dataclass
    class _Str2Key:
        diffuse: dict[str, DXSpec_TextureKey] = field( default_factory=dict )
        normal: dict[str, DXSpec_TextureKey] = field( default_factory=dict )
        orm: dict[str, DXSpec_TextureKey] = field( default_factory=dict )
        emissive: dict[str, DXSpec_TextureKey] = field( default_factory=dict )

    def __init__( self, dxspec_material_db: dict[str, DXSpec_Material] ):

        # Image texture key to list of material names
        self.key2list = self._Key2List()

        # Material name to image texture key
        self.str2key = self._Str2Key()

        # Map image texture key to list of material names
        for mat_name, spec_mat in dxspec_material_db.items():
            if( diff_key := spec_mat.get_diffuse_texture_key() ):
                self.key2list.diffuse[diff_key].append( mat_name )
            if( norm_key := spec_mat.get_normal_texture_key() ):
                self.key2list.normal[norm_key].append( mat_name )
            if( orm_key := spec_mat.get_orm_texture_key() ):
                self.key2list.orm[orm_key].append( mat_name )
            if( em_key := spec_mat.get_emissive_texture_key() ):
                self.key2list.emissive[em_key].append( mat_name )

        # Map material name to image texture key
        self.str2key.diffuse = { v: k for k, vs in self.key2list.diffuse.items() for v in vs }
        self.str2key.normal = { v: k for k, vs in self.key2list.normal.items() for v in vs }
        self.str2key.orm = { v: k for k, vs in self.key2list.orm.items() for v in vs }
        self.str2key.emissive = { v: k for k, vs in self.key2list.emissive.items() for v in vs }

class DXSpec_TextureSpecContainer:
    @dataclass
    class _Key2Str:
        diffuse: dict[DXSpec_TextureKey, str] = field( default_factory=dict )
        normal: dict[DXSpec_TextureKey, str] = field( default_factory=dict )
        orm: dict[DXSpec_TextureKey, str] = field( default_factory=dict )
        emissive: dict[DXSpec_TextureKey, str] = field( default_factory=dict )

    @dataclass
    class _Str2Key:
        diffuse: dict[str, DXSpec_TextureKey] = field( default_factory=dict )
        normal: dict[str, DXSpec_TextureKey] = field( default_factory=dict )
        orm: dict[str, DXSpec_TextureKey] = field( default_factory=dict )
        emissive: dict[str, DXSpec_TextureKey] = field( default_factory=dict )

    def __init__( self, dxspec_texture_keys_db: DXSpec_TextureKeysContainer ):

        # Image texture key to DDS texture name
        self.key2str = self._Key2Str()

        # DDS texture name to image texture key
        self.str2key = self._Str2Key()

        key2list = dxspec_texture_keys_db.key2list
        for texture_keys, default, texture_outs, texture_outs_inv in [
            ( key2list.diffuse, '$DEFAULT_DIFFUSE', self.str2key.diffuse, self.key2str.diffuse ),
            ( key2list.normal, '$DEFAULT_NORMAL', self.str2key.normal, self.key2str.normal ),
            ( key2list.orm, '$DEFAULT_ORM', self.str2key.orm, self.key2str.orm ),
            ( key2list.emissive, '$DEFAULT_EMISSIVE', self.str2key.emissive, self.key2str.emissive ),
        ]:
            for key in texture_keys.keys():
                key_name_fold = self.name_fold( key, default )

                if key_name_fold not in texture_outs:
                    texture_outs[ key_name_fold ] = key
                else:
                    raise ValueError( 'Outname already exists!!' )

                if key not in texture_outs_inv:
                    texture_outs_inv[ key ] = key_name_fold
                else:
                    raise ValueError( 'Outname inverse already exists!!' )

    def name_fold( self, key: DXSpec_TextureKey, default: str ):
        paths = [ sub_key[0] for sub_key in key[0] if sub_key[0] is not None ]

        if not paths:
            return default # TODO: check 1111/hh/111/111

        # Check if all paths are the same
        if len( set( paths ) ) == 1:
            return ( paths[0].stem + '.dds' ).replace( "\\", "/" )

        raise ValueError( f'Cannot fold {key}' )

class DXSpec_Mat2TextureContainer:
    def __init__( self, dxspec_texture_keys_db: DXSpec_TextureKeysContainer, dxspec_texture_outs_db: DXSpec_TextureSpecContainer ):
        tex_outs = dxspec_texture_outs_db.key2str
        tex_keys = dxspec_texture_keys_db.str2key

        self.diffuse: dict[str, str] = { k: tex_outs.diffuse[v] for k, v in tex_keys.diffuse.items() }
        self.normal: dict[str, str] = { k: tex_outs.normal[v] for k, v in tex_keys.normal.items() }
        self.orm: dict[str, str] = { k: tex_outs.orm[v] for k, v in tex_keys.orm.items() }
        self.emissive: dict[str, str] = { k: tex_outs.emissive[v] for k, v in tex_keys.emissive.items() }