import os
import json
import distutils
from distutils.dir_util import copy_tree
from xml.etree import ElementTree as xmlNode
import shutil
from url_normalize import url_normalize
import subprocess

def get_module_name(name):
    return 'boost_' + name


def create_package_directory(module, version):
    path = os.path.join('prefab', get_module_name(module.name) + '-' + version)
    os.makedirs(path, exist_ok=True)
    return path


def create_prefab_json(path, module, version, depends):
    # we can't declare dependencies because it don't work
    content = {
        'schema_version': 1,
        'name': get_module_name(module.name),
        'version': version,
        'dependencies': [] # [ get_module_name(mod) for mod in depends]
    }
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, 'prefab.json'), 'w') as f:
        json.dump(content, f, sort_keys=False, indent=2)

def create_module_json(path, module):
    module_path = os.path.join(path, 'modules', get_module_name(module.name))
    os.makedirs(module_path, exist_ok=True)

    content = {
        'export_libraries': [],
        'library_name': None,
        'android': {
            'export_libraries': [],
            'library_name': None
        }
    }

    with open(os.path.join(module_path, 'module.json'), 'w') as f:
        json.dump(content, f, sort_keys=False, indent=2)

def copy_include_files(path, module):
    include_path = os.path.join(module.abspath, 'include')
    distutils.dir_util.copy_tree(include_path, os.path.join(path, 'modules', get_module_name(module.name), 'include'))

def create_manifest(path):
    xml = xmlNode.parse('AndroidManifest.xml')
    xml.write(os.path.join(path, 'AndroidManifest.xml'))

def create_maven_pom(path, module, version, depends):
    ns = {'pom': 'http://maven.apache.org/POM/4.0.0'}
    xml = xmlNode.parse('pom-template.xml')

    for node in xml.findall('./pom:artifactId', ns):
        node.text = get_module_name(module.name)
    for node in xml.findall('./pom:version', ns):
        node.text = version
    for node in xml.findall('./pom:name', ns):
        node.text = get_module_name(module.name)


    remoteUrl = module.url
    if remoteUrl.startswith('..'):
        remoteUrl = url_normalize(os.path.join(module.repo.remotes.origin.url, module.url))

    for node in xml.findall('./pom:scm/pom:url', ns):
        node.text = remoteUrl

    for node in xml.findall('./pom:scm/pom:connection', ns):
        node.text = 'scm:git:' + remoteUrl

    with open(os.path.join(module.abspath, 'meta', 'libraries.json'), 'r') as f:
        content = json.load(f)
        if 'key' in content:
            pass
        else:
            content = content[0]

        if 'description' in content:
            for node in xml.findall('./pom:description', ns):
                node.text = content['description']

        if 'name' in content:
            for node in xml.findall('./pom:name', ns):
                node.text = content['name']


        if 'maintainers' in content:
            for node in xml.findall('./pom:developers', ns):
                for author in content['maintainers']:
                    developer = xmlNode.SubElement(node, '{http://maven.apache.org/POM/4.0.0}developer')
                    name = xmlNode.SubElement(developer, '{http://maven.apache.org/POM/4.0.0}name')
                    name.text = author
        else :
            if 'authors' in content:
                for node in xml.findall('./pom:developers', ns):
                    for author in content['authors']:
                        developer = xmlNode.SubElement(node, '{http://maven.apache.org/POM/4.0.0}developer')
                        name = xmlNode.SubElement(developer, '{http://maven.apache.org/POM/4.0.0}name')
                        name.text = author


        #Add dependecies : 
        for node in xml.findall('./pom:dependencies', ns):
            for mod in depends:
                dependency = xmlNode.SubElement(node, '{http://maven.apache.org/POM/4.0.0}dependency')

                xmlNode.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}groupId').text = 'com.github.brunotl'
                xmlNode.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}artifactId').text = get_module_name(mod)
                xmlNode.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}version').text = version
                xmlNode.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}type').text = 'aar'
                xmlNode.SubElement(dependency, '{http://maven.apache.org/POM/4.0.0}optional').text = False



    xml.write(path + '.pom', 
                encoding='utf-8', xml_declaration=True, 
                default_namespace='http://maven.apache.org/POM/4.0.0')


def create_prefab_package(module, version, depends):
    # TODO : check if package already exist (aar & pom file)

    path = create_package_directory(module, version)

    # manifest.xml
    create_manifest(path)
    # <prefab>/
    prefab_path = os.path.join(path, 'prefab')
    #     prefab.json
    create_prefab_json(prefab_path, module, version, depends)
    #     modules/
    #         <module name>/
    #             module.json
    create_module_json(prefab_path, module)
    #             include/
    copy_include_files(prefab_path, module)
    #             libs/
    #                 <platform>.<id>/
    #                     include/
    #                     <lib>

    shutil.make_archive(path, 'zip', path)
    os.rename(path + '.zip', path + '.aar')
    shutil.rmtree(path)

    # TODO : create xml pom file
    create_maven_pom(path, module, version, depends)

    # TODO : check prefab

    with open('prefab/include.cmake', 'a') as f: 
        module_name = get_module_name(module.name)
        f.writelines([
            'find_package ({} REQUIRED CONFIG)\n'.format(module_name),
            'target_link_libraries(LK8000 {}::{})\n'.format(module_name,module_name),
            '\n'
        ])


    # # Publish on local maven
    subprocess.call(['mvn', 
                        'install:install-file', 
                        '-Dfile=' + path + '.aar', 
                        '-DpomFile=' + path + '.pom'])

    # # Deploy to sonatype OSSRH maven remote repository
    local_mvn_setting = os.path.join(os.getenv("HOME"),'.m2', 'settings.xml')
    subprocess.call(['mvn',
                        'gpg:sign-and-deploy-file',
                        '-Durl=https://oss.sonatype.org/service/local/staging/deploy/maven2/',
                        '-Dfile=' + path + '.aar', 
                        '-DpomFile=' + path + '.pom',
                        '-DrepositoryId=ossrh',
                        '--settings', local_mvn_setting])
