from typing import Literal, Sequence, Type, TypeGuard, TypeVar, Mapping
import copy
import rich

BlendModes = Literal['OPAQUE', 'MASK', 'BLEND']
DDSFormat = Literal[
    'BC1_UNORM', 'BC1_UNORM_SRGB',
    'BC3_UNORM', 'BC3_UNORM_SRGB',
    'BC4_UNORM',
    'BC5_UNORM',
    'BC6H_UF16',
    'BC7_UNORM', 'BC7_UNORM_SRGB'
]

def format_get_channels( f: DDSFormat ):
    match f[:3]:
        case 'BC1': return 4
        case 'BC3': return 4
        case 'BC4': return 1
        case 'BC5': return 2
        case 'BC6': return 3
        case 'BC7': return 4

    raise ValueError( f'Unknow BC format {f}' )

def format_get_srgb( f: DDSFormat ):
    return f[-4:] == 'SRGB'

def format_requires_alpha_cuttoff( f: DDSFormat, blend_mode: BlendModes ):
    return f[:3] == 'BC1' and blend_mode == 'MASK'


def is_numeric(obj: object) -> TypeGuard[int | float]:
    return isinstance(obj, (int, float))

def is_numeric_sequence(obj: object) -> TypeGuard[Sequence[int | float]]:
    return isinstance(obj, (tuple, list)) and all(isinstance(o, (int, float)) for o in obj)

def _modulate( original, modulator ) :
    # If modulator is a literal, overwite original with modulator
    if not isinstance( modulator, dict ):
        return modulator

    op = modulator.pop( 'op' )
    value = modulator.pop( 'value' )

    if op not in [ 'mult', 'add' ]:
        raise ValueError( f'Unknown operator {op}!' )

    if original is None:
        raise ValueError( f'Cannot modulate a None value with op "{op}" and value "{value}"!' )

    if not ( is_numeric( original ) or is_numeric_sequence( original ) ):
        raise ValueError( f'Original value "{original}" must be numeric to be modulated by op "{op}" and value "{value}"!' )

    if not ( is_numeric( value ) or is_numeric_sequence( value ) ):
        raise ValueError( f'Value "{value}" must be numeric to be modulate original "{original}" with op "{op}"!' )

    if is_numeric( original ) and is_numeric( value ):
        match op:
            case 'mult': return original * value
            case 'add': return original + value
            case _: assert False

    if is_numeric( original ) and is_numeric_sequence( value ):
        raise ValueError( f'Cannot modulate float "{original}" by tuple "{value}"' )

    if is_numeric_sequence( original ) and is_numeric( value ):
        match op:
            case 'mult': return tuple( o * value for o in original )
            case 'add': return tuple( o + value for o in original )
            case _: assert False

    if is_numeric_sequence( original ) and is_numeric_sequence( value ):
        if len( original ) != len( value ):
            raise ValueError( f'Original tuple "{original}" and value tuple "{value}" must be equal length!' )

        match op:
            case 'mult': return tuple( o * v for o, v in zip( original, value ) )
            case 'add': return tuple( o + v for o, v in zip( original, value ) )
            case _: assert False

    assert False


O = TypeVar( 'O' )
def modulate( original: O, modulator ) -> O:
    out: O = _modulate( original, modulator ) # type: ignore

    assert is_numeric( original ) == is_numeric( out )
    assert is_numeric_sequence( original ) == is_numeric_sequence( out )

    return out


T = TypeVar( 'T' )
def init( cls: Type[T], obj: dict, key: str, default: T | None = None ) -> T | None:
    if key in obj:
        return cls( obj[ key ] ) # type: ignore
    return default

class ezlog:
    @staticmethod
    def debug( *args ):
        rich.print( '[bold cyan]DEBUG:[/bold cyan]', *args, flush=True )

    @staticmethod
    def info( *args ):
        rich.print( '[bold green]INFO:[/bold green]', *args, flush=True )

    @staticmethod
    def warning( *args ):
        rich.print( '[bold yellow]WARNING:[/bold yellow]', *args, flush=True )

    @staticmethod
    def error( *args ):
        rich.print( '[bold red]ERROR:[/bold red]', *args, flush=True )

def recursive_overwrite(A: dict, B: Mapping) -> dict:
    """
    Overwrites A with keys/values from B recursively.
    - If both A[k] and B[k] are dicts -> recurse
    - Otherwise -> overwrite A[k] with a deep copy of B[k]
    """
    for k, v in B.items():
        if (
            k in A
            and isinstance(A[k], Mapping)
            and isinstance(v, Mapping)
        ):
            recursive_overwrite(A[k], v)
        else:
            A[k] = copy.deepcopy(v)
    return A
