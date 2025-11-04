from setuptools import setup, find_packages
import ast
from pathlib import Path

def get_version():
    source = Path( 'gltf_conv/__init__.py' ).read_text( encoding='utf-8' )
    module = ast.parse( source )

    for node in module.body:
        if isinstance( node, ast.Assign ):
            for target in node.targets:
                if isinstance( target, ast.Name ) and target.id == '__version__':
                    if isinstance( node.value, ast.Constant ):
                        if isinstance( node.value.value, str ):
                            return node.value.value
    raise RuntimeError( 'Cout not find __version__!' )

setup(
    name="gltf_conv",
    version=get_version(),
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "gltf_conv": [
            "schemas/*.json"
        ]
    },
    install_requires=[
        "rich",
        "jsonschema"
    ],
    entry_points={
        "console_scripts": [
            "gltf_conv=gltf_conv.__main__:main",
        ]
    },
)