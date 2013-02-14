'''
v.0.0.1

LDSIncremental -  PostgreSQLDataStore

Copyright 2011 Crown copyright (c)
Land Information New Zealand and the New Zealand Government.
All rights reserved

This program is released under the terms of the new BSD license. See the 
LICENSE file for more information.

Created on 9/08/2012

@author: jramsay
'''
import gdal
import logging
import re
import string

from DataStore import DataStore
from DataStore import MalformedConnectionString

ldslog = logging.getLogger('LDS')

class PostgreSQLDataStore(DataStore):
    '''
    PostgreSQL DataStore
    '''
    
    DRIVER_NAME = "PostgreSQL"
    PG_USE_COPY = "NO"
    PG_USE_BASE64 = "YES"
    
    def __init__(self,conn_str=None,user_config=None):
        '''
        PostgreSQL DataStore constructor
        '''
        
        super(PostgreSQLDataStore,self).__init__(conn_str,user_config)
              
        #doesnt work with createlayer... but not needed if we want to overwrite FID with PK
        #self.PGSQL_OGR_FID = "ID"    
        #gdal.SetConfigOption("PGSQL_OGR_FID",self.PGSQL_OGR_FID)
        
        #do not use PG_USE_COPY if you want FID preserved
        #self.PG_USE_COPY = "NO"
        gdal.SetConfigOption("PG_USE_COPY",self.PG_USE_COPY)
        
        #self.PG_USE_BASE64 = "YES"
        gdal.SetConfigOption("PG_USE_BASE64",self.PG_USE_BASE64)

        (self.host,self.port,self.dbname,self.schema,self.usr,self.pwd, self.overwrite,self.config,self.srs,self.cql) = self.params

        
    def sourceURI(self,layer):
        '''URI method returns source DB instance'''
        return self._commonURI(layer)
    
    def destinationURI(self,layer):
        '''URI method returns destination DB instance'''
        return self._commonURI(layer)
        
    def validateConnStr(self,cs):
        '''The PostgreSQL connection string must be something like PG:"dbname='databasename' host='addr' port='5432' user='x' password='y'" '''
        #-d PG:"dbname='ldsincr' host='127.0.0.1' port='5432' user='pguser' password='pgpass'"
        if not re.search('^PG:',cs,flags=re.IGNORECASE):
            '''TODO. We could append a PG here instead'''
            raise MalformedConnectionString('PostgreSQL declaration must begin with \'PG\'')
        if not re.search("dbname='\S+'",cs,flags=re.IGNORECASE):
            raise MalformedConnectionString('\'dbname\' parameter required in PostgreSQL config string')
        if not re.search("host='\S+'",cs,flags=re.IGNORECASE):
            raise MalformedConnectionString('\'host\' parameter required in PostgreSQL config string')
        if not re.search("port='\d+'",cs,flags=re.IGNORECASE):
            raise MalformedConnectionString('\'port\' parameter required in PostgreSQL config string')
        #HACK. active schema, unlike the other PG parameters, cannot have single quotes! this silently removes them if they've been mistakenly added
        return re.sub(r"active_schema='(\S+)'",r"active_schema=\1",cs)

        
        
    def _commonURI(self,layer):
        '''Refers to common connection instance for reading or writing'''
        if hasattr(self,'conn_str') and self.conn_str is not None:
            return self.validateConnStr(self.conn_str)
        #can't put schema in quotes, causes error but without quotes tables get created in public anyway, still need schema.table syntax
        sch = " active_schema={}".format(self.schema) if self.schema is not None and not all(i in string.whitespace for i in self.schema) else ""
        usr = " user='{}'".format(self.usr) if self.usr is not None and not all(i in string.whitespace for i in self.usr) else ""
        pwd = " password='{}'".format(self.pwd) if self.pwd is not None and not all(i in string.whitespace for i in self.pwd) else ""
        hst = " host='{}'".format(self.host) if self.host is not None and not all(i in string.whitespace for i in self.host) else ""
        prt = " port='{}'".format(self.port) if self.port is not None and not all(i in string.whitespace for i in self.port) else ""
        uri = "PG:dbname='{}'".format(self.dbname)+hst+prt+usr+pwd+sch
        ldslog.debug(uri)
        return uri


    def getOptions(self,layer_id):
        '''Add PG options for SCHEMA and GEO_NAME'''
        #Should default to geometry but doesn't, creates bytea instead
        local_opts = ['GEOM_TYPE=GEOMETRY']
        gname = self.layerconf.readLayerProperty(layer_id,'geocolumn')
        
        if gname is not None:
            local_opts += ['GEOMETRY_NAME='+gname]
        
        return super(PostgreSQLDataStore,self).getOptions(layer_id) + local_opts
    
    def buildIndex(self,lce,dst_layer_name):
        '''Builds an index creation string for a new full replicate in PG format'''
        ref_index = DataStore.parseStringList(lce.index)
        if ref_index.intersection(set(('spatial','s'))):
            cmd = 'CREATE INDEX {}_SK ON {} USING GIST({})'.format(dst_layer_name.split('.')[-1]+"_"+lce.gcol,dst_layer_name,lce.gcol)
        elif ref_index.intersection(set(('primary','pkey','p'))):
            cmd = 'CREATE INDEX {}_PK ON {}({})'.format(dst_layer_name.split('.')[-1]+"_"+lce.pkey,dst_layer_name,lce.pkey)
        elif ref_index is not None:
            #maybe the user wants a non pk/spatial index? Try to filter the string. This wont work for spatial columns since GIST needed
            #TODO. Detect when gcol is in the col list and build a "mixed-spatial"? index...
            clst = ','.join(ref_index)
            cmd = 'CREATE INDEX {}_PK ON {}({})'.format(dst_layer_name.split('.')[-1]+"_"+DataStore.sanitise(clst),dst_layer_name,clst)
        else:
            return
        ldslog.info("Index="+','.join(ref_index)+". Execute "+cmd)
        self.executeSQL(cmd)
        
        
        
    def versionCheck(self):
        '''Postgres/Postgis version checker'''
        from VersionChecker import VersionChecker,UnsupportedVersionException

        pgv_cmd = 'SELECT version()'
        pgisv_cmd = 'SELECT postgis_full_version()'
        
        pgv_res = re.search('PostgreSQL\s+(\d+\.\d+\.\d+)',self.executeSQL(pgv_cmd).GetNextFeature().GetFieldAsString(0))
        pgisv_res = re.search('POSTGIS=\"(\d+\.\d+\.\d+)',self.executeSQL(pgisv_cmd).GetNextFeature().GetFieldAsString(0))
        
        if VersionChecker.compareVersions(VersionChecker.PostgreSQL_MIN, pgv_res.group(1) if pgv_res is not None else VersionChecker.PostgreSQL_MIN):
            raise UnsupportedVersionException('PostgreSQL version '+str(pgv_res.group(1))+' does not meet required minumum '+str(VersionChecker.PostgreSQL_MIN))
        
        if VersionChecker.compareVersions(VersionChecker.PostGIS_MIN, pgisv_res.group(1) if pgisv_res is not None else VersionChecker.PostGIS_MIN):
            raise UnsupportedVersionException('PostGIS version '+str(pgisv_res.group(1))+' does not meet required minumum '+str(VersionChecker.PostGIS_MIN))
        
        return True
        
        
        

    