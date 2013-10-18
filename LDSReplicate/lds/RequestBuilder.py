'''
v.0.0.9

LDSReplicate -  RequestBuilder

Copyright 2011 Crown copyright (c)
Land Information New Zealand and the New Zealand Government.
All rights reserved

This program is released under the terms of the new BSD license. See the 
LICENSE file for more information.

URI builder subclasses for differing WFS implementations 

Created on 03/09/2013

@author: jramsay
'''
import re

import logging

from contextlib import closing
from lxml import etree
from lxml.etree import XMLSyntaxError

from lds.WFSDataStore import WFSDataStore
from urllib2 import urlopen, build_opener, install_opener, ProxyHandler
from lds.LDSUtilities import LDSUtilities
from lds.DataStore import MalformedConnectionString, UnknownDSVersionException
from lds.VersionUtilities import AppVersion

ldslog = LDSUtilities.setupLogging()

class RequestBuilder(object):
    '''
    LDS DataStore provides standard options and URI methods along with convenience methods for common functions/documents expressed as 
    URI builders. For incremental specifically the change-column is defined here
    '''
    
    SUPPORTED_OUTPUT_FORMATS = ('GML2','GML3','JSON')


    def __init__(self,params,conn_str=None):
        '''
        LDS init/constructor subclassing WFSDataStore
        '''
        self.setParameters(params)
        self.conn_str = conn_str
        #if conn_str provided get key from the string
        if self.conn_str:
            self.key = self.extractAPIKey(self.conn_str,raise_err=False)
            
        if not self.validateAPIKey(self.key):
            raise MalformedConnectionString('Invalid KEY, '+self.key)
        
    def setParameters(self,params):
        (self.url,self.key,self.svc,self.ver,self.fmt,self.cql) = params

            
    @staticmethod
    def getInstance(params,cs=None):
        version = params[3]
        if version=='1.0.0' or version=='1.0':
            return RequestBuilderWFS110(params,cs)
        elif version=='1.1.0':
            return RequestBuilderWFS110(params,cs)
        elif version=='2.0.0' or version=='2.0':
            return RequestBuilderWFS200(params,cs)
        else:
            raise UnknownDSVersionException('Cannot decode WFS version '+str(version))
        
    def validateAPIKey(self,kstr):
        '''Make sure the provided key conforms to the required format'''
        srch = re.search('[a-f0-9]{32}',kstr,flags=re.IGNORECASE)
        if srch is None:
            raise MalformedConnectionString('Cannot parse API key, '+str(kstr))
        return True
        
    def extractAPIKey(self,cs,raise_err=False):
        '''if the user has supplied a connection string then they dont need to specify an API key in their config file, therefore we must extract it from the cs'''
        srch = re.search('/([a-f0-9]{32})/(v/x|wfs\?)',cs,flags=re.IGNORECASE)
        if srch is None and raise_err:
            raise MalformedConnectionString('Cannot parse API key')
        return srch.group(1) if srch is not None else None
    
    def _buildCQLStr(self):
        '''Builds a cql_filter string as set by the user appending an 'id>...' partitioning string if needed. NB. Manual partitioning is accomplished using the parameters, 'maxFeatures' to set feature quantity, a page-by-page recorded 'id' value and a 'sortBy=id' argument'''
        cql = ()
        maxfeat = ""
        
#         #if implementing pagination in cql      
#         if self.pstart is not None and self.psize is not None:
#             cql += (self.pkey+">"+str(self.pstart),)
#             #sortBy used so last feature will have the new maximum key, saves a comparison
#             maxfeat = "&sortBy="+self.pkey+"&maxFeatures="+str(self.psize)            

        if self.cql:
            cql += (LDSUtilities.checkCQL(self.cql),)

        return maxfeat+"&cql_filter="+';'.join(cql) if len(cql)>0 else ""    
    
    
class RequestBuilderWFS200(RequestBuilder):
    #example
    #http://data-test.linz.govt.nz/services;key=a3624a518c67440daf97789975cc7d23/wfs?service=WFS&request=GetCapabilities
    #http://data-test.linz.govt.nz/services;key=a3624a518c67440daf97789975cc7d23/wfs?service=WFS&request=GetFeature&typeName=linz:layer-452&count=3
    def __str__(self):
        return 'RequestBuilder_WFS-2.0.0'
    
    def getCapabilities(self):
        uri = '{}services;key={}/wfs?service={}&request=GetCapabilities'.format(self.url,self.key,self.svc)
        ldslog.debug(uri)
        return uri
    
    def validateConnStr(self,cs):
        '''WFS basic checks. 1 url format,2 api key,3 ask for wfs'''
        if not re.search('^http://',cs,flags=re.IGNORECASE):
            raise MalformedConnectionString('\'http\' declaration required in LDS request')
        if not re.search('data-test\.linz\.govt\.nz',cs,flags=re.IGNORECASE):
            raise MalformedConnectionString('Require \'data-test.linz.govt.nz\' in LDS (WFS2.0) address string')
        if not re.search('/key=[a-f0-9]{32}/',cs,flags=re.IGNORECASE):
            raise MalformedConnectionString('Require API key (32char hex) in LDS address string')
        if not re.search('wfs\?',cs,flags=re.IGNORECASE):
            raise MalformedConnectionString('Need to specify \'wfs?\' service in LDS request')
        #look for conflicts
        ulayer = LDSUtilities.getLayerNameFromURL(cs)

        return cs,ulayer
    
    def buildIndex(self,lce,dst_layer_name):
        pass
    
    def sourceURI(self,layername):
        '''Basic 2.0 Endpoint constructor'''
        if self.conn_str:
            valid,urilayer = self.validateConnStr(self.conn_str)
            if layername and urilayer!=layername:
                raise MalformedConnectionString('Layer specifications in URI differs from selected layer (-l); '+str(layername)+'!='+str(urilayer))
            return valid

        cql = self._buildCQLStr()
        #pql = self._buildPageStr()     
            
        typ = "##typeName="+layername
        ver = "##version="+self.ver if self.ver else ""
        svc = "##service="+self.svc if self.svc else "##service=WFS"
        req = "##request=GetFeature"
        #if omitted the outputformat parameter is null and default used, GML2
        fmt = "##outputFormat="+self.fmt if (self.fmt in self.SUPPORTED_OUTPUT_FORMATS) else ""
        uri = re.sub('##','&',re.sub('##','?',self.url+self.key+"/wfs"+svc+ver+req+typ+fmt+cql,1))
        ldslog.debug(uri)
        return uri
    
    def sourceURIIncremental(self,layername,fromdate,todate):
        '''Endpoint constructor fetching specific layers with incremental date fields'''
        if self.conn_str:
            valid,urilayer = self.validateConnStr(self.conn_str)
            #I don't know why you would attempt to specify dates in the CL and in the URL as well but we might as well attempt to catch diffs
            if layername is not None and urilayer!=layername:
                raise MalformedConnectionString('Layer specifications in URI differs from selected layer (-l); '+str(layername)+'!='+str(urilayer))
            if (fromdate is not None and re.search('from:'+fromdate[:10],valid) is None) or (todate is not None and re.search('to:'+todate[:10],valid) is None):
                raise MalformedConnectionString("Date specifications in URI don't match those referred to with -t|-f "+str(todate)+'/'+str(fromdate)+" not in "+valid)
            return valid

        cql = self._buildCQLStr()
        #pql = self._buildPageStr()     
        
        vep = LDSUtilities.splitLayerName(layername)+"-changeset"
        typ = "##typeName="+layername+"-changeset"
        inc = "##viewparams=from:"+fromdate+";to:"+todate
        ver = "##version="+self.ver if self.ver else ""
        svc = "##service="+self.svc if self.svc else "##service=WFS"
        req = "##request=GetFeature"
        #if omitted the outputformat parameter is null and default used, GML2
        fmt = "##outputFormat="+self.fmt if (self.fmt in self.SUPPORTED_OUTPUT_FORMATS) else ""
        uri = re.sub('##','&',re.sub('##','?',self.url+self.key+vep+"/wfs"+svc+ver+req+typ+inc+fmt+cql,1))
        ldslog.debug(uri)
        return uri
    
    def sourceURIFeatureCount(self,layername):
        '''Endpoint constructor to fetch number of features for a specific layer. for: Trigger manual paging for broken JSON'''
        #version must be 1.1.0 or > for this to work. NB outputFormat doesn't seem to have any effect here either so its omitted
        typ = "&typeName="+layername
        uri = self.url+self.key+"/wfs?service="+self.svc+"&version="+self.ver+"&request=GetFeature&resultType=hits"+typ
        ldslog.debug(uri)
        return uri        

class RequestBuilderWFS100(RequestBuilder):
    
    @classmethod
    def new(cls,*args,**kwargs):
        return RequestBuilderWFS110(*args,**kwargs)
    
    def __str__(self):
        return 'RequestBuilder_WFS-1.0.0'

class RequestBuilderWFS110(RequestBuilder):
    
    def __str__(self):
        return 'RequestBuilder_WFS-1.1.0'
    
    def getCapabilities(self):
        '''GetCapabilities endpoint constructor'''
        #capabilities doc is fetched using urlopen, not wfs, so escaping isnt needed
        #uri = LDSUtilities.xmlEscape(self.url+self.key+"/wfs?service=WFS&version=1.1.0&request=GetCapabilities")
        uri = '{}{}/wfs?service=WFS&version=1.1.0&request=GetCapabilities'.format(self.url,self.key)
        ldslog.debug(uri)
        return uri
        
        
    def validateConnStr(self,cs):
        '''WFS basic checks. 1 url format,2 api key,3 ask for wfs'''
        if not re.search('^http://',cs,flags=re.IGNORECASE):
            raise MalformedConnectionString('\'http\' declaration required in LDS request')
        if not re.search('wfs\.data\.linz\.govt\.nz',cs,flags=re.IGNORECASE):
            raise MalformedConnectionString('Require \'wfs.data.linz.govt.nz\' in LDS address string')
        if not re.search('/[a-f0-9]{32}/(v/x|wfs\?)',cs,flags=re.IGNORECASE):
            raise MalformedConnectionString('Require API key (32char hex) in LDS address string')
        if not re.search('wfs\?',cs,flags=re.IGNORECASE):
            raise MalformedConnectionString('Need to specify \'wfs?\' service in LDS request')
        #look for conflicts
        ulayer = LDSUtilities.getLayerNameFromURL(cs)

        return cs,ulayer
        
    def buildIndex(self,lce,dst_layer_name):
        pass
        
    def sourceURI(self,layername):
        '''Basic Endpoint constructor'''
        if not layername:
            ldslog.warn('No layer name provided to URI generator')
            return None
        
        if self.conn_str:
            valid,urilayer = self.validateConnStr(self.conn_str)
            if layername and urilayer!=layername:
                raise MalformedConnectionString('Layer specifications in URI differs from selected layer (-l); '+str(layername)+'!='+str(urilayer))
            return valid

        cql = self._buildCQLStr()
        #pql = self._buildPageStr()     
        typ = "##typeName="+layername
        ver = "##version="+self.ver if self.ver else ""
        svc = "##service="+self.svc if self.svc else "##service=WFS"
        req = "##request=GetFeature"
        #if omitted the outputformat parameter is null and default used, GML2
        fmt = "##outputFormat="+self.fmt if (self.fmt in self.SUPPORTED_OUTPUT_FORMATS) else ""
        uri = re.sub('##','&',re.sub('##','?',self.url+self.key+"/wfs"+svc+ver+req+typ+fmt+cql,1))
        ldslog.debug(uri)
        return uri

        
    def sourceURIIncremental(self,layername,fromdate,todate):
        '''Endpoint constructor fetching specific layers with incremental date fields'''
        if self.conn_str:
            valid,urilayer = self.validateConnStr(self.conn_str)
            #I don't know why you would attempt to specify dates in the CL and in the URL as well but we might as well attempt to catch diffs
            if layername is not None and urilayer!=layername:
                raise MalformedConnectionString('Layer specifications in URI differs from selected layer (-l); '+str(layername)+'!='+str(urilayer))
            if (fromdate is not None and re.search('from:'+fromdate[:10],valid) is None) or (todate is not None and re.search('to:'+todate[:10],valid) is None):
                raise MalformedConnectionString("Date specifications in URI don't match those referred to with -t|-f "+str(todate)+'/'+str(fromdate)+" not in "+valid)
            return valid

        cql = self._buildCQLStr()
        #pql = self._buildPageStr()     
        
        vep = LDSUtilities.splitLayerName(layername)+"-changeset"
        typ = "##typeName="+layername+"-changeset"
        inc = "##viewparams=from:"+fromdate+";to:"+todate
        ver = "##version="+self.ver if self.ver else ""
        svc = "##service="+self.svc if self.svc else "##service=WFS"
        req = "##request=GetFeature"
        #if omitted the outputformat parameter is null and default used, GML2
        fmt = "##outputFormat="+self.fmt if (self.fmt in self.SUPPORTED_OUTPUT_FORMATS) else ""
        uri = re.sub('##','&',re.sub('##','?',self.url+self.key+vep+"/wfs"+svc+ver+req+typ+inc+fmt+cql,1))
        ldslog.debug(uri)
        return uri
    
    def sourceURIFeatureCount(self,layername):
        '''Endpoint constructor to fetch number of features for a specific layer. for: Trigger manual paging for broken JSON'''
        #version must be 1.1.0 or > for this to work. NB outputFormat doesn't seem to have any effect here either so its omitted
        typ = "&typeName="+layername
        uri = self.url+self.key+"/wfs?service="+self.svc+"&version="+self.ver+"&request=GetFeature&resultType=hits"+typ
        ldslog.debug(uri)
        return uri        


    


        

        
        