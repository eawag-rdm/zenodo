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
import logging
from pprint import pprint

DEFAULT_AFFILIATION = 'Eawag'
DEFAULT_TYPE = 'dataset'
ZENODO_HOST = 'https://zenodo.org'
ZENODO_HOST_TEST = 'https://sandbox.zenodo.org'

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
        self.resources = self.get_ckanresources(self.resourceurls)
        if args.get('--sandbox'):
            self.apitoken_zenodo = self.getapitokens().get('zenodo_test')
            self.host_zenodo = ZENODO_HOST_TEST
        else:
            self.apitoken_zenodo = self.getapitokens().get('zenodo')
            self.host_zenodo = ZENODO_HOST

    def putfiles(self, resourcefiles=None, zid=None):
        resourcefiles = resourcefiles or self.resourcefiles
        zid = zid or self.zid
        params = {'access_token': self.apitoken_zenodo}
        for fn, _, fpath in resourcefiles:
            url = '{}/{}'.format(self.bucket_url, fn)
            print("Uploading {}, Path: {} to {}".format(fn, fpath, url))
            with  open(fpath, 'rb') as f:
                r = requests.put(url,
                                 data=f,
                                 params=params)            
            print('\n{}'.format(r.text))
        
    def putmeta(self):
        url = '{}/api/deposit/depositions'.format(self.host_zenodo)
        print(url)
        headers = {'Content-Type': 'application/json'}
        print(headers)
        params = {'access_token': self.apitoken_zenodo}
        print(params)
        print(self.zmeta)
        r = requests.post(url,
                          headers=headers,
                          params=params,
                          json={'metadata': self.zmeta})
        if r.status_code != 201:
            print(r.text)
            raise(RuntimeError('Failed to create metadata record'))
        else:
            self.zid = r.json()['id']
            self.bucket_url = r.json()['links']['bucket']
            return r

    def list_depositions(self):
        url = '{}/api/deposit/depositions'.format(self.host_zenodo)
        r = requests.get(url, params={'access_token': self.apitoken_zenodo})
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
        self.resourcefiles = resources
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
        return meta

        
if __name__ == '__main__':
    args = docopt(__doc__, argv=sys.argv[1:])
    z = Zen(args)
    r = z.putmeta()
    z.putfiles()
