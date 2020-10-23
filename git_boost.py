from __future__ import print_function

import git
import os
import sys
import re

verbose = 0

def vprint(level, *args):
    if verbose >= level:
        print(*args)

class boostorg:
    def __init__(self, version):
        self.root_repo = None

        root_path = 'boost_'+ version

        if os.path.exists(root_path):
            self.root_repo = git.Repo(root_path)

        if not self.root_repo:
            self.root_repo = git.Repo.clone_from(
                url='https://github.com/boostorg/boost.git',
                to_path=root_path,
                branch='boost-' + version)

        self.module_list = [mod.name for mod in self.root_repo.submodules]

    def updateModule(self, name):
        module = self.root_repo.submodule(name)
        self.root_repo.git.submodule('update', '--init', module.path)
        return module

    def scan_module_dependencies(self, module, callback):
        vprint(1, 'Scanning module', module.path)

        depends = []
        for file in ['src','include']:
            self.scan_directory(os.path.join(module.abspath, 'include'), module, depends, callback)

        return depends


    def scan_directory(self, path, module, depends, callback):
        vprint(1, 'Scanning directory', path)

        if os.name == 'nt' and sys.version_info[0] < 3:
            d = unicode(d)

        for root, dirs, files in os.walk(path):
            for file in files:
                fn = os.path.join(root, file)
                vprint(2, 'Scanning file', fn)

                if sys.version_info[0] < 3:
                    with open(fn, 'r') as f:
                        self.scan_header_dependencies(f, module, depends, callback)
                else:
                    with open(fn, 'r', encoding='latin-1') as f:
                        self.scan_header_dependencies(f, module, depends, callback)

    def scan_header_dependencies(self, f, module, depends, callback):
        for line in f:
            m = re.match('[ \t]*#[ \t]*include[ \t]*["<](boost/[^">]*)[">]', line)
            if m:
                h = m.group(1)
                mod = self.module_for_header(h)
                if mod and mod != module.name:
                    if not mod in depends:
                        depends.append(mod)
                        callback(self.root_repo.submodule(mod))

    def module_for_header(self, h):

        # boost/function.hpp
        m = re.match('boost/([^\\./]*)\\.h[a-z]*$', h)
        if m and m.group(1) in self.module_list: 
            return m.group(1)

        # boost/numeric/conversion.hpp
        m = re.match('boost/([^/]*/[^\\./]*)\\.h[a-z]*$', h)
        if m and m.group(1) in self.module_list: 
            return m.group(1)


        # boost/numeric/conversion/header.hpp
        m = re.match('boost/([^/]*/[^/]*)/', h)
        if m and m.group(1) in self.module_list: 
            return m.group(1)

        # boost/function/header.hpp
        m = re.match('boost/([^/]*)/', h)
        if m and m.group(1) in self.module_list: 
            return m.group(1)

        vprint(0, 'Cannot determine module for header', h)
        return None
