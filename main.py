import argparse
import urllib.request
import re
from git_boost import boostorg
import prefab

version = '1.81.0'
depends = {}
root = boostorg(version)

def depends_callback(module):
    if not module.name in depends:
        print("check module dependencies" , module.name)
        depends[module.name] = True
        module = root.updateModule(module.name)
        mod_depends = root.scan_module_dependencies(module, depends_callback)

        prefab.create_prefab_package(module, version, mod_depends)


if( __name__ == "__main__" ):
    parser = argparse.ArgumentParser( description='Package Boost library into android prefab' )
    parser.add_argument( 'library', nargs="+", help="name of library to build" )
    args = parser.parse_args()

    for library in args.library:
        depends_callback(root.updateModule(library))
