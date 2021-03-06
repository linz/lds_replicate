'''
v.0.0.9

LDSReplicate -  ldsreplicate

| Copyright 2011 Crown copyright (c)
| Land Information New Zealand and the New Zealand Government.
| All rights reserved

This program is released under the terms of the new BSD license. See the LICENSE file for more information.

Created on 23/07/2012

@author: jramsay

Python script to translate fetch an LDS update between two dates. Intended to be used in a batch process rather than interactively. 

Usage:

python LDSReader/ldsreplicate.py -l <layer_id>
    [-f <from date>|-t <to date>|-c <cql filter>|-s <src conn str>|-d <dst conn str>|-v|-h] 
    <output> [full]
    
    -f (--fromdate) Date in yyyy-mm-dd format start of incremental range (omission assumes auto incremental bounds)
    -t (--todate) Date in yyyy-mm-dd format for end of incremental range (omission assumes auto incremental bounds)
    -l (--layer) Layer name/id in format v:x### (IMPORTANT. Omission assumes all layers)
    -g (--group) Layer sub group list for layer selection, comma separated
    -e (--epsg) Destination EPSG. Layers will be converted to this SRS
    -s (--source) Connection string for source DS
    -d (--destination) Connection string for destination DS
    -c (--cql) Filter definition in CQL format
    -h (--help) Display this message
    -v (--version) Display the version number"

'''


import sys
import getopt

from datetime import datetime
from urllib2 import HTTPError

from lds.TransferProcessor import TransferProcessor
from lds.TransferProcessor import InputMisconfigurationException
from lds.VersionUtilities import AppVersion, VersionChecker, UnsupportedVersionException
from lds.DataStore import DSReaderException
from lds.LDSUtilities import LDSUtilities
from lds.ConfigConnector import DatasourceRegister

ldslog = LDSUtilities.setupLogging()

#ldslog = logging.getLogger('LDS')
#ldslog.setLevel(logging.DEBUG)
#
#path = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../log/"))
#if not os.path.exists(path):
#    os.mkdir(path)
#df = os.path.join(path,"debug.log")
#
#fh = logging.FileHandler(df,'a')
#fh.setLevel(logging.DEBUG)
#
#formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s %(lineno)d - %(message)s')
#fh.setFormatter(formatter)
#ldslog.addHandler(fh)

__version__ = AppVersion.getVersion()

def usage():
    print "Usage: python LDSReader/ldsreplicate.py -l <layer_id> [-f <from date>|-t <to date>|-c <cql filter>|-s <src conn str>|-d <dst conn str>|-v|-h] <output> [full]"
    print "For help use --help"

def main():
    '''Main entrypoint if the LDS incremental replication script
    
    usage: python LDSReader/ldsreplicate.py -l <layer_id>
        [-f <from date>|-t <to date>|-c <cql filter>|-s <src conn str>|-d <dst conn str>|-u <user_config>|-g <group keyword>|-e <conversion-epsg>|-h (help)] 
        <output>
    '''

    td = None
    fd = None
    ly = None
    gp = None
    ep = None
    sc = None
    dc = None
    cq = None
    uc = None
    
    gdal_ver = VersionChecker.getGDALVersion()   
    #pgis_ver = VersionChecker.getPostGISVersion()   
    #pg_ver = VersionChecker.getPostgreSQLVersion()
    
    
    if VersionChecker.compareVersions(VersionChecker.GDAL_MIN,gdal_ver.get('GDAL') if gdal_ver.get('GDAL') is not None else VersionChecker.GDAL_MIN):
        raise UnsupportedVersionException('PostgreSQL version '+str(gdal_ver.get('GDAL'))+' does not meet required minumum '+str(VersionChecker.GDAL_MIN))
     
#do the datasource checks in object and once initialised
#        message += 'GDAL '+pgis_ver.get('GDAL')+'<'+VersionChecker.GDAL_MIN+'(reqd) \n'
#    if VersionChecker.compareVersions(VersionChecker.GDAL_MIN,pgis_ver.get('GDAL') if pgis_ver.get('GDAL') is not None else VersionChecker.GDAL_MIN): 
#        message += 'GDAL(pgis) '+pgis_ver.get('GDAL')+'<'+VersionChecker.GDAL_MIN+'(reqd) \n'
#    if VersionChecker.compareVersions(VersionChecker.PostgreSQL_MIN,pg_ver.get('PostgreSQL') if pgis_ver.get('PostgreSQL') is not None else VersionChecker.PostgreSQL_MIN): 
#        message += 'PostgreSQL '+pg_ver.get('PostgreSQL')+'<'+VersionChecker.PostgreSQL_MIN+' (reqd)\n'

    
    # parse command line options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvixf:t:l:g:e:s:d:c:u:", ["help","version","internal","external","fromdate=","todate=","layer=","group=","epsg=","source=","destination=","cql=","userconf="])
        ldslog.info("OPTS:"+str(opts))
        ldslog.info("ARGS:"+str(args))
    except getopt.error, msg:
        print msg
        usage()
        sys.exit(2)
        
    # process options
    for opt, val in opts:
        if opt in ("-h", "--help"):
            print __doc__
            sys.exit(0)
        elif opt in ("-v", "--version"):
            print __version__
            sys.exit(0)
        elif opt in ("-f","--fromdate"):
            fd = val 
        elif opt in ("-t","--todate"):
            td = val
        elif opt in ("-l","--layer"):
            ly = val
        elif opt in ("-g","--group"):
            gp = val
        elif opt in ("-e","--epsg"):
            ep = val
        elif opt in ("-s","--source"):
            sc = val
        elif opt in ("-d","--destination"):
            dc = val
        elif opt in ("-c","--cql"):
            cq = val
        elif opt in ("-u","--userconf"):
            uc = val
        else:
            print "unrecognised option:\n" \
            "-f (--fromdate) Date in yyyy-mm-dd format start of incremental range (omission assumes auto incremental bounds)," \
            "-t (--todate) Date in yyyy-mm-dd format for end of incremental range (omission assumes auto incremental bounds)," \
            "-l (--layer) Layer name/id in format v:x### (IMPORTANT. Omission assumes all layers)," \
            "-g (--group) Layer sub group list for layer selection, comma separated" \
            "-e (--epsg) Destination EPSG. Layers will be converted to this SRS" \
            "-s (--source) Connection string for source DS," \
            "-d (--destination) Connection string for destination DS," \
            "-c (--cql) Filter definition in CQL format," \
            "-u (--user) User defined config file used as partial override for template.conf," \
            "-h (--help) Display this message"
            sys.exit(2)

#    #TODO consider ly argument to specify a file name containing a list of layers? 

    st = datetime.now()
    m1 = '*** Begin    *** '+str(st.isoformat())
    print m1
    ldslog.info(m1)
    #layer overrides group, whether layer is IN group is not considered
    ly if ly else gp
    tp = TransferProcessor(None,ly if ly else gp,ep,fd,td,sc,dc,cq,uc)

    #output format
    if len(args)==0:
        print __doc__
        sys.exit(0)
    else: 
        #since we're not breaking the switch the last arg read will be the DST used
        pn = None
        for arg in args:
            if arg.lower() in ("init", "initialise", "initalize"):
                ldslog.info("Initialisation of configuration files/tables requested. Implies FULL rebuild")
                tp.setInitConfig()
            elif arg in ("clean"):
                ldslog.info("Cleaning named layer")
                tp.setCleanConfig()
            else:
                #if we dont have init/clean the only other arg must be output type
                pn = LDSUtilities.standardiseDriverNames(arg)
                
        if pn is None:
            print __doc__
            raise InputMisconfigurationException("Unrecognised command; output type (pg,ms,slite,fgdb) declaration required")
            

    #aggregation point for common LDS errors
    mm = '*** Complete *** '
    try:
        reg = DatasourceRegister()
        sep = reg.openEndPoint('WFS',uc)
        dep = reg.openEndPoint(pn,uc)
        reg.setupLayerConfig(tp,sep,dep, tp.getInitConfig())
        tp.setSRC(sep)
        tp.setDST(dep)
        tp.processLDS()
    except HTTPError as he:
        ldslog.error('Error connecting to LDS. '+str(he))
        mm = '*** Failed 1 *** '
    except DSReaderException as dse:
        ldslog.error('Error creating DataSource. '+str(dse))
        mm = '*** Failed 2 *** '
    #except Exception as e:
        #if errors are getting through we catch/report them
    #    ldslog.error("Error! "+str(e))
    #    mm = '*** Failed 3 *** '
    finally:
        reg.closeEndPoint(pn)
        reg.closeEndPoint('WFS')
        sep,dep = None,None
        
    
    et = datetime.now()
    
    m2 = mm + str(et.isoformat())
    print m2
    ldslog.info(m2)
    
    dur = et-st
    m3 = '*** Duration *** '+str(dur)
    print m3
    ldslog.info(m3)
    
    return 1000*dur.total_seconds()


if __name__ == "__main__":
    #main()
    
    try:
        main()
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        ldslog.error('LDSReplicate Error.',exc_info=(exc_type,exc_value,exc_traceback))
        print str(e)+'\n(see debug.log for full stack trace)'
