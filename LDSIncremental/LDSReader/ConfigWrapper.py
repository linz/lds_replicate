'''
v.0.0.1

LDSIncremental -  (Meta) Layer Reader

Copyright 2011 Crown copyright (c)
Land Information New Zealand and the New Zealand Government.
All rights reserved

This program is released under the terms of the new BSD license. See the 
LICENSE file for more information.

Created on 23/07/2012

@author: jramsay
'''
import logging

from ReadConfig import MainFileReader, LayerFileReader

ldslog = logging.getLogger('LDS')

class ConfigWrapper(object):
    '''
    Convenience wrapper class to config-file reader instances. Facade for file reader/table reader 
    '''

    def __init__(self,config_file=None):
        #                    user cf         ,layer props file name
        '''this is not a ogr function so we dont need a driver and therefore wont call super'''
        #some layer config properties may not be needed and wont be read eg WFS so None arg wont set layerconfig
        
        
        self.CONFIG_FILE = "ldsincr.conf"

        self.setupMainConfig(config_file)
        #dont set up layerconfig by default. Wait till we know whether we want a new build (initconfig) 
        #self.setupLayerConfig()


    def setupMainConfig(self,userconfig):
        '''Sets up a reader to the main configuration file or alternatively, a user specified config file.
        Userconfig is not mean't to replace mainconfig, just overwrite the parts the user has decided to customise'''
        self.userconfig = None
        if userconfig is not None:
            self.userconfig = MainFileReader("../"+userconfig,False)
        self.mainconfig = MainFileReader("../"+self.CONFIG_FILE,True)
        
        
    def setupLayerConfig(self,filename):
        '''Adds a layerconfig file object which will be requested if external sepcified in main config'''
        self.layerconfig = LayerFileReader(filename)
        
        
    def getLayerNames(self):
        '''Returns configured layers for respective layer properties file'''
        return self.layerconfig.getSections()
    
#    def readLayerCategories(self,layer_id):
#        '''Reads configured name for a provided layer id'''
#        #(pkey,name,group,gcol,index,epsg,lmod,disc,cql) = self.layerconfig.readLayerSchemaConfig(layer_id)
#        category = self.layerconfig.readLayerProperty(layer_id,'category')
#        return category
#    
#    def readLayerEPSG(self,layer_id):
#        '''Reads configured SRS for a provided layer id'''
#        #(pkey,name,group,gcol,index,epsg,lmod,disc,cql) = self.layerconfig.readLayerSchemaConfig(layer_id)
#        epsg = self.layerconfig.readLayerProperty(layer_id,'epsg')
#        return epsg
#    
#    def readConvertedLayerName(self,layer_id):
#        '''Reads configured name for a provided layer id'''
#        #(pkey,name,group,gcol,index,epsg,lmod,disc,cql) = self.layerconfig.readLayerSchemaConfig(layer_id)
#        name = self.layerconfig.readLayerProperty(layer_id,'name')
#        return name
#    
#    def lookupConvertedLayerName(self,layer_name):
#        '''Reverse lookup of layer id given a layer name, again using the layer properties file'''
#        return self.layerconfig.findLayerIdByName(layer_name)
#
#
#
#
#    def readLastModified(self,layer_id):
#        '''Reads last modified date for a provided layer id per destination'''
#        #(pkey,name,group,gcol,index,epsg,lmod,disc,cql) = self.layerconfig.readLayerSchemaConfig(layer_id)
#        lmod = self.layerconfig.readLayerProperty(layer_id,'lastmodified')
#        return lmod
#        
#    def writeLastModified(self,layer_id,lmod):
#        '''Writes a new last modified date for a provided layer id per destination'''
#        ldslog.info("Writing "+lmod+" for layer="+layer_id+" to config file")
#        self.layerconfig.writeLayerSchemaConfig(layer_id, lmod)
#
#        
#
#
#    def readOptionalColmuns(self,layer_id):
#        '''Returns a list of columns being discarded for the named layer (with removal of brackets)'''
#        #(pkey,name,group,gcol,index,epsg,lmod,disc,cql) = self.layerconfig.readLayerSchemaConfig(layer_id)
#        disc = self.layerconfig.readLayerProperty(layer_id,'discard')
#        return disc.strip('[]{}()').split(',') if disc is not None else []
#    
#    def readPrimaryKey(self,layer_id):
#        '''Returns a list of columns being discarded for the named layer'''
#        #(pkey,name,group,gcol,index,epsg,lmod,disc,cql) = self.layerconfig.readLayerSchemaConfig(layer_id)
#        pkey = self.layerconfig.readLayerProperty(layer_id,'pkey')
#        return pkey
#    
#    def readIndexRef(self,layer_id):
#        '''Returns a list of columns being discarded for the named layer'''
#        #(pkey,name,group,gcol,index,epsg,lmod,disc,cql) = self.layerconfig.readLayerSchemaConfig(layer_id)
#        index = self.layerconfig.readLayerProperty(layer_id,'index')
#        return index
#    
#    def readCQLFilter(self,layer_id):
#        '''Reads the CQL filter for the layer if provided'''
#        #(pkey,name,group,gcol,index,epsg,lmod,disc,cql) = self.layerconfig.readLayerSchemaConfig(layer_id)
#        cql = self.layerconfig.readLayerProperty(layer_id,'cql')
#        return cql
#    
#    
#    
#    def readGeometryColumnName(self,layer_id):
#        '''Returns preferred geometry column name. If not provided uses the existing layer name'''
#        #(pkey,name,group,gcol,index,epsg,lmod,disc,cql) = self.layerconfig.readLayerSchemaConfig(layer_id)
#        gcol = self.layerconfig.readLayerProperty(layer_id,'geocolumn')
#        return gcol
#    
#    
#    def readLayerParameters(self,layer_id):
#        '''Returns a list of all layer parameters'''
#        return self.layerconfig.readLayerSchemaConfig(layer_id)
#        
#    #==============MAINCONFIG===========================================================

    def readDSParameters(self,drv):
        '''Returns the datasource parameters. By request updated to let users override parts of the basic config file'''
        ul = ()

        if drv=='PostgreSQL':
            ml = self.mainconfig.readPostgreSQLConfig()
            if self.userconfig is not None:
                ul = self.userconfig.readPostgreSQLConfig()
        elif drv=='MSSQLSpatial':
            ml = self.mainconfig.readMSSQLConfig()
            if self.userconfig is not None:
                ul = self.userconfig.readMSSQLConfig()
        elif drv=='FileGDB':
            ml = self.mainconfig.readFileGDBConfig()
            if self.userconfig is not None:
                ul = self.userconfig.readFileGDBConfig()
        elif drv=='SQLite':
            ml = self.mainconfig.readSpatiaLiteConfig()
            if self.userconfig is not None:
                ul = self.userconfig.readSpatiaLiteConfig()
        elif drv=='WFS':
            ml = self.mainconfig.readWFSConfig()
            if self.userconfig is not None:
                ul = self.userconfig.readWFSConfig()
        else:
            return None
        
        params = map(lambda x,y: y if x is None else x,ul,ml)
        
        
        return params

        
        