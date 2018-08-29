# _*_ coding: utf-8 _*_
'''zenodo.

Usage:
  zenodo [-s] <doi> <sourceurl>
  zenodo (-h | --help)

Options:
   -h --help      Show this screen
   -s --sandbox   Use Zenodo's sandbox version for testing

Arguments:
  <doi>         The Eawag DOI as "<prefix>/<suffix>"
  <sourceurl>   The URL of the CKAN package.

'''
import os
import sys
import requests
import urllib3
from docopt import docopt
import ckanapi
import tempfile
import json
import re

from pprint import pprint


# apitoken = os.environ['ZENODO_APITOKEN']
# r = requests.get("https://zenodo.org/api/deposit/depositions",
#                  params={'access_token': apitoken})
# print(r.status_code)

    
DEFAULT_AFFILIATION = 'Eawag'
DEFAULT_TYPE = 'dataset'
ZENODO_HOST = 'https://zenodo.org'
ZENODO_HOST_TEST = 'http://sandbox.zenodo.org'

class Zen:
    def __init__(self, args):
        sourceurl = urllib3.util.url.parse_url(args['<sourceurl>'])
        self.doi = args['<doi>']
        self.apitoken_ckan = self.getapitokens().get('ckan')
        self.ckanhost = '{}://{}'.format(sourceurl.scheme, sourceurl.host)
        self.ckancon = ckanapi.RemoteCKAN(
            self.ckanhost, apikey=self.apitoken_ckan)
        self.ckanpkg = self.get_ckanpkg(sourceurl.path.split('/')[-1])
        self.resourceurls = self.get_resourceurls(self.ckanpkg)
        self.zmeta = self.zenodo_meta()
        if args.get('--sandbox'):
            self.apitoken_zenodo = self.getapitokens().get('zenodo_test')
            self.host_zenodo = ZENODO_HOST_TEST
        else:
            self.apitoken_zenodo = self.getapitokens().get('zenodo')
            self.host_zenodo = ZENODO_HOST

            
    def putfile(self):
        pass
    def putmeta(self):
        url = '{}/api/deposit/depositions'.format(self.host_zenodo)
        print(url)
        headers = {'Content-Type': 'application/json'}
        print(headers)
        params = {'access_token': self.apitoken_zenodo}
        print(params)
        print(self.zmeta)
        r = requests.post(url, headers=headers, params=params, data=self.zmeta)
        return r
        
    def getapitokens(self):
        return {'zenodo': os.environ['ZENODO_APITOKEN'],
                'zenodo_test': os.environ['ZENODO_APITOKEN_SANDBOX'],
                'ckan': os.environ['CKAN_APIKEY']}

    def get_ckanpkg(self, pkg_name):
        pkg = self.ckancon.call_action(
            'package_show', data_dict={'id': pkg_name})
        return pkg
    
    def get_resourceurls(self, pkg):
        urls = [r.get('url') for r in pkg['resources'] if r.get('url')]
        return urls

    def get_ckanresources(self, urls):
        resources = []
        for u in urls:
            filename = u.split('/')[-1]
            tmpfile, tmppath =  tempfile.mkstemp()
            resources.append((filename, tmpfile, tmppath))
            with open(tmppath, 'wb') as f:
                with requests.get(u, stream=True) as r:
                    for chunk in r.iter_content(4096):
                        f.write(chunk)
        return resources
            
    
    def listself(self):
        print("SELF\n")
        pprint(self.__dict__)
        print("RESOURCEURLS\n")
        pprint(self.get_resourceurls(self.ckanpkg))
        print("ZENODO_META_TEMPLATE")
        pprint(json.dumps(self.zenodoskel()))
        
        # pprint(self.get_ckanresources(self.get_resourceurls(self.get_ckanpkg())))

    def zenodoskel(self):
        zenodo_meta = {
            "upload_type": DEFAULT_TYPE,
            "title": None,
            "creators": [], # {"name": <family, given>, "affiliation": <affil>, "orcid": orcid}
            "description": None,
            "access_right": "open",
            "license": "cc-zero",
            "doi": self.doi,
            "prereserve_doi": False,
            "keywords": [], # array of strings
            "related_identifiers": [], #array of objects {"identifier": "10.1234/foo", "relation": "isSupplementedBy"|"isSupplementTo"}
            "communities": [{"identifier": "eawag"}],
            "version": "1.0",
            "language": "eng"
        }
        return zenodo_meta

    def authors2zenodo(self):
        authors = self.ckanpkg.get('author')
        if not isinstance(authors, list):
            raise RuntimeError('package field "author" from CKAN is not a list')
        authors = [re.sub('(<.*>)', '', a).strip() for a in authors]
        creators =  [{
            'name': n,
            'affiliation': DEFAULT_AFFILIATION} for n in authors]
        return creators
    
    def zenodo_meta(self):
        meta = self.zenodoskel()
        meta.update({
            'title': self.ckanpkg.get('title'),
            'creators': self.authors2zenodo(),
            'description': self.ckanpkg.get('notes'),
            'keywords': [t.get('display_name') for t in self.ckanpkg.get('tags')]
            })
        return json.dumps(meta)
        
if __name__ == '__main__':
    args = docopt(__doc__, argv=sys.argv[1:])
    z = Zen(args)
    z.listself()
   
    #resources = z.get_ckanresources(z.resourceurls)
    #print(resources)
    print("AUTHORS\n")

    print(z.authors2zenodo())
    print("META\n")
    print(z.zenodo_meta())
    r = z.putmeta()
    print("RETURN META\n")
    print(r.__dict__)
          

args = {'<doi>': '10.25678/000055',
        '--sandbox': False,
        '<sourceurl>': 'https://eaw-ckan-dev1.eawag.wroot.emp-eaw.ch/dataset/bottom-up-identification-of-subsystems-in-swiss-water-governance'
        }

z = Zen(args)

r = z.putmeta()
