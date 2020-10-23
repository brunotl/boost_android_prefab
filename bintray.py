import requests
import subprocess
import os
import lxml
from xml.etree import ElementTree as xmlNode

def upload_to_bintray(path, name, vcs_url):

    local_mvn_setting = os.path.join(os.getenv("HOME"),'.m2', 'settings.xml')

    username = None
    password = None
    xml_setting = xmlNode.parse(local_mvn_setting)
    ns = {'s':'http://maven.apache.org/SETTINGS/1.1.0'}
    servers = xml_setting.findall("s:servers/s:server",namespaces=ns)
    for server in servers:
        if server.findtext("s:id", namespaces=ns) == 'bintray-brunotl-prefab-library':
            username = server.findtext("s:username", namespaces=ns)
            password = server.findtext("s:password", namespaces=ns)

    response = requests.get('https://api.bintray.com/packages/brunotl/prefab-library/'+name)
    package = response.json()
    if not 'name' in package:

        response = requests.post("https://api.bintray.com/packages/brunotl/prefab-library", 
                                    auth=(username, password),
                                    json={
                                        'name': name,
                                        'licenses':['BSL-1.0'],
                                        'vcs_url': vcs_url,
                                        'website_url':'https://www.boost.org'
                                    })
        package = response.json()
    if 'name' in package:
        args = ['mvn', 'deploy:deploy-file',
                            '-Dfile=' + path + '.aar', 
                            '-DpomFile=' + path + '.pom',
                            '-Durl=https://api.bintray.com/maven/brunotl/prefab-library/'+ name + '/;publish=1',
                            '-DrepositoryId=bintray-brunotl-prefab-library',
                            '--settings', local_mvn_setting]

        subprocess.call(args)

