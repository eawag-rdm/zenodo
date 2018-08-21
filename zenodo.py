# _*_ coding: utf-8 _*_
'''zenodo.

Usage:
  zenodo <doi> <sourceurl>
  zenodo (-h | --help)

Options:
   -h --help    Show this screen

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

from pprint import pprint




# apitoken = os.environ['ZENODO_APITOKEN']
# r = requests.get("https://zenodo.org/api/deposit/depositions",
#                  params={'access_token': apitoken})
# print(r.status_code)


class Zen:
    def __init__(self, args):
        sourceurl = urllib3.util.url.parse_url(args['<sourceurl>'])
        self.doi = args['<doi>']
        self.apitoken = self.getapitokens()
        self.ckanhost = '{}://{}'.format(sourceurl.scheme, sourceurl.host)
        self.ckancon = ckanapi.RemoteCKAN(
            self.ckanhost, apikey=self.apitoken['ckan'])
        self.ckanpkg = self.get_ckanpkg(sourceurl.path.split('/')[-1])
        
    def putfile(self):
        pass
    def putmeta(self):
        pass
    def getapitokens(self):
        return {'zenodo': os.environ['ZENODO_APITOKEN'],
                'ckan': os.environ['CKAN_APIKEY']}
    # def getfiles(self, packageurl):
    #     conn = self.getckanconn(ckanhost, apikey=self.apitoke['ckan'])
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
        print(self.__dict__)
        pprint(self.get_ckanpkg())
        pprint(self.get_resourceurls(self.get_ckanpkg()))
        pprint(self.get_ckanresources(self.get_resourceurls(self.get_ckanpkg())))
        
if __name__ == '__main__':
    args = docopt(__doc__, argv=sys.argv[1:])
    z = Zen(args)
    z.listself()
    
