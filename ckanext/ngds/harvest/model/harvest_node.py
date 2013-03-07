from ckanext.ngds.base.model.ngds_db_object import NgdsDataObject
from ckanext.ngds.metadata.model.additional_metadata import ResponsibleParty

from ckan import model
from ckan.model import meta, Package

from sqlalchemy import types, Column, Table, ForeignKey
from sqlalchemy.orm import relationship, validates

import logging
log = logging.getLogger(__name__)

from datetime import datetime

from urlparse import urlparse, urlunparse
from urllib import urlencode
from urllib2 import urlopen

from lxml import etree
from owslib.iso import MD_Metadata
from owslib.csw import CatalogueServiceWeb

class HarvestNode(NgdsDataObject):
    """Stores information about harvest endpoints"""
    def __init__(self, url, **kwargs):
        # A URL must be given
        p = urlparse(url)
        self.url = urlunparse((p.scheme, p.netloc, p.path, "", "", "")) # Strip URL to just domain + path
        self.frequency = kwargs.get('frequency', 'manual') # frequency should be one of manual|daily|weekly|monthly
        self.title = kwargs.get('title', 'No Title Was Given') # A title for bookkeeping
        self.node_admin_id = kwargs.get('node_admin_id', None) # Foreign Key to a responsible_party who maintains the remote node
        self.csw = CatalogueServiceWeb(self.url) # owslib CSW class provides mechanisms for making CSW requests
        
    def do_harvest(self):
        """Perform a harvest from another CSW server"""                        
        self.get_records() # Do the first GetRecords request
        ids = self.csw.records.keys() # Start an array to house all of the ids
        print "next: %s, total: %s" % (self.csw.results["nextrecord"], self.csw.results["matches"])
        
        while self.csw.results["nextrecord"] < self.csw.results["matches"] and self.csw.results["nextrecord"] != 0: # Once next_record > number_matched, we've gotten everything
            self.get_records(self.csw.results["nextrecord"], self.csw.results["returned"]) # Get another set, starting from next_record from previous response
            ids += self.csw.records.keys() # Add new ids to the array
            print "next: %s, total: %s" % (self.csw.results["nextrecord"], self.csw.results["matches"])
        
        self.parse_records(ids) # Gather the records themselves
                   
    def parse_records(self, ids):
        """Perform as many GetRecordById requests as needed"""
        print "Gathered %s IDs" % str(len(ids))
        for record_id in ids:
            self.get_record_by_id(record_id)
            print "got one"
    
    def get_record_by_id(self, record_id):
        """Get a single record, by ID"""
        params = {
            "id": [ record_id ],
            "outputschema": "http://www.isotc211.org/2005/gmd"    
        }
        self.csw.getrecordbyid(**params) # Puts response in self.csw.records        
    
    def get_records(self, start_position=1, max_records=1000):
        """Perform a GetRecords request"""
        params = {
            "typenames": "gmd:MD_Metadata",
            "outputschema": "http://www.isotc211.org/2005/gmd",
            "startposition": start_position,
            "maxrecords": max_records,
            "esn": "brief"          
        }
        self.csw.getrecords(**params) # Puts results in self.csw.records        
        
class HarvestedRecord(NgdsDataObject):
    """Store relationship between a harvest node and a CKAN package"""
    def __init__(self, package_id, harvest_node_id, harvested_xml):
        self.package_id = package_id
        self.harvest_node_id = harvest_node_id
        self.harvested_xml = harvested_xml
    
    @validates('package_id')
    def validate_package_id(self, key, package_id):
        """Check that the package_id given is valid"""
        pkg = self.Session.query(Package).filter(getattr(Package, "id", None)==package_id).first() # Check if a package with that ID already exists
        if pkg:
            return package_id
        else:
            assert False
            
    @classmethod
    def from_md_metadata(cls, md, harvest_node):
        """Given a MD_Metadata record parsed by owslib, create a Package and HarvestedRecord"""
        package_parameters = {
            "id": md.identifier, # will CKAN let us state the ID for a package?
            "metadata_modified": md.datestamp, # this is a string in owslib
            "dataset_uri": md.dataseturi, # this can probably be an array?
            "dataset_category": md.hierarchy,
            "publication_date": md.identification.date[0].date, # this is a string in owslib, should find the obj in the date array where type="publication"
            "creators": [], # complex procedure involves adding ResponsibleParties
            "abstract": md.identification.abstract,
            "quality": md.dataquality,
            "status": md.identification.status,
            "keywords": "", # tough logic that will need to amalgamate keywords. Will I loose thesaurus info?
            "dataset_lang": md.identification.resourcelanguage, # this is an array in owslib
            "spatial_word": "", # tough logic to find any location keywords
            "spatial": md.identification.extent.boundingBox, # generate GeoJSON from this owslib ele
            "usage": md.identification.useconstraints # array in owslib
        }
        
        '''The rest here is conceptual'''
        pkg = create_package(**package_parameters) # Find out how to do this in CKAN
        pkg.save() # Save a CKAN package
        iso = ckanext.ngds.metadata.model.IsoPackage(pkg) # Create the ckan to ISO wrapper object
        cswRecord = ckanext.ngds.csw.model.CswRecord(iso) # Create the pycsw record for this guy
        cswRecord.save() # Save the pycsw record
        return cls(pkg.id, harvest_node.id, etree.tostring(md)) # Return the HarvestRecord object that binds package to harvest node with the trailing xml 
        
        
'''
This stuff is started, but not sure if I actually want to do it this way

class HarvestLog(NgdsDataObject):
    """Persist harvesting history"""
    def __init__(self, harvest_node_id, **kwargs):
        self.harvest_node_id = harvest_node_id
        self.harvest_date = kwargs.get('harvest_date', datetime.now().date())
        self.records_harvested = kwargs.get('records_harvested', 0)
        self.success = kwargs.get('success', False)
        
class HarvestLogEntry(NgdsDataObject):
    def __init__(self, harvest_log_id, message):
        self.harvest_log_id = harvest_log_id
        self.message = message
'''
        
def define_tables():
    """Create in-memory representation of the harvest tables"""
    # Define the tables
    node_table = Table(
        "harvest_node",
        meta.metadata,
        Column("id", types.Integer, primary_key=True),
        Column("url", types.UnicodeText),
        Column("frequency", types.UnicodeText),
        Column("title", types.UnicodeText),
        Column("node_admin_id", types.Integer, ForeignKey("responsible_party.id"))                
    )
    
    harvest_record_table = Table(
        "harvested_record",
        meta.metadata,
        Column("id", types.Integer, primary_key=True),
        Column("package_id", types.UnicodeText, ForeignKey("package.id")),
        Column("harvest_node_id", types.Integer, ForeignKey("harvest_node.id")),
        Column("harvested_xml", types.UnicodeText)                             
    )
    
    # Map classes to tables
    meta.mapper(HarvestNode, node_table,
        properties={
            "node_admin": relationship(ResponsibleParty)            
        }
    )
    
    meta.mapper(
        HarvestedRecord,
        harvest_record_table, 
        properties={
            "package": relationship(Package),
            "harvest_node": relationship(HarvestNode)
        }
    )
    
    # Add classes to memory
    model.HarvestNode = HarvestNode
    model.HarvestedRecord = HarvestedRecord
    
def db_setup():
    """Create database tables"""
    node_table = meta.metadata.tables.get("harvest_node", None)
    harvest_record_table = meta.metadata.tables.get("harvested_record", None)
    
    if node_table == None or harvest_record_table == None:
        log.debug("Could not create additional tables. Please make sure that you've added the ngdsharvest plugin to your CKAN config .ini file.")
    else:
        log.debug("NGDS Harvesting tables defined in memory")
        from ckanext.ngds.base.commands.ngds_tables import create_tables
        create_tables([node_table, harvest_record_table], log)

        
        

        
        