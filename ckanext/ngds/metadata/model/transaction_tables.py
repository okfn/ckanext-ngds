''' ___NGDS_HEADER_BEGIN___

National Geothermal Data System - NGDS
https://github.com/ngds

File: <filename>

Copyright (c) 2013, Siemens Corporate Technology and Arizona Geological Survey

Please Refer to the README.txt file in the base directory of the NGDS
project:
https://github.com/ngds/ckanext-ngds/README.txt

___NGDS_HEADER_END___ '''

"""
Contains models for the transaction tables used part of ngds.

"""

from ckan import model


from ckan.model import meta

from sqlalchemy import types, Column, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

import datetime

import logging
log = logging.getLogger(__name__)

from ckanext.ngds.base.model.ngds_db_object import NgdsDataObject
        
class BulkUpload(NgdsDataObject):
    """
    A BulkUpload represents the details of a bulk uploaded dataset and status of the processing.
    *data_file - xls file path which contains the details about dataset, resource.
    *resources - zip file path which contains the documents/resources to be uploaded as part of dataset creation which
                is linked in the xls file.
    *path - Full path of the location where data_file and resources are stored.
    *status - Status of a particular record (VALID,INVALID, COMPLETED, FAILURE)
    *comments - Contains the reason for failure or validaiton error messages.
    *uploaded_by - User who uploaded this record.
    """
    
    def __init__(self, **kwargs):
        self.data_file = kwargs.get('data_file', None)
        self.resources = kwargs.get('resources', None)
        self.path = kwargs.get('path', None)
        self.status = kwargs.get('status', None)
        self.comments = kwargs.get('comments', None)
        self.uploaded_by = kwargs.get('uploaded_by', None)
        
    @classmethod
    def search(cls, querystr, sqlalchemy_query=None):
        """Search by status """
        if sqlalchemy_query is None:
            query = meta.Session.query(cls)
        else:
            query = sqlalchemy_query

        query = query.filter(cls.status == querystr)
        return query

    @classmethod
    def get_all(cls):
         return cls.Session.query(cls).order_by(cls.uploaded_date.desc()).all()
    
    @classmethod
    def by_data_file(cls, querystr):
        """Returns a bulk upload record referenced by its id or name."""
        query = meta.Session.query(cls).filter(cls.data_file == querystr)
        member = query.first()        
        return member


    @classmethod
    def get(cls, reference):
        """Returns a bulk upload record referenced by its id or name."""
        query = meta.Session.query(cls).filter(cls.id == reference)
        member = query.first()
        if member is None:
            member = cls.by_data_file(reference)
        return member

class BulkUpload_Package(NgdsDataObject):
    """
    A BulkUpload_Package represents the packages created as part of the bulk upload process.
    *package_name - unique name of package
    *package_title - Short description about the package
    """
    
    def __init__(self, **kwargs):
        self.bulk_upload_id = kwargs.get('bulk_upload_id', None)
        self.package_name = kwargs.get('package_name', None)
        self.package_title = kwargs.get('package_title', None)
        self.uploaded_date = kwargs.get('uploaded_date',None)

    @classmethod
    def by_bulk_upload(cls, querystr):
        """ This method returns data based on input bulk upload identifier."""
        query = meta.Session.query(cls).filter(cls.bulk_upload_id == querystr)
        return query.all()


class StandingData(NgdsDataObject):
    """
    A StandingData represents the all the lookup values used in the system. Any restricted list of data is represented
    in this table.
     *description - Explains about the lookup value (typically what is displayed to user)
     *code - Any other code available to represent the lookup data
     *data_type - type of lookup data. (E.g. status (Dataset status), protocol (Protocol of the resource)
    """
    def __init__(self, **kwargs):
        self.description = kwargs.get('description', None)
        self.code = kwargs.get('code', None)
        self.data_type = kwargs.get('data_type', None)    

    @classmethod
    def validate(cls, data_type, sdvalue):
        """ This method validates whether given SD value is present in the model or not. 
        If exists returns SD description otherwise None """

        print "Data type:%s SD Value: %s" % (data_type, sdvalue)

        query = meta.Session.query(cls).filter(cls.data_type == data_type)
        query = query.filter(func.lower(cls.description) == sdvalue.lower())
        member = query.first()        
        if member is None:
            return None
        else:
            if member.code is not None:
                return member.code
            else: 
                return member.description

class UserSearch(NgdsDataObject):
    """
    UserSearch represents the saved searches of registered users.
    *user_id - Saved user identifier
    *search_name - Name for the saved search.
    *url - Actual saved search URL
    """

    def __init__(self, **kwargs):
        self.user_id = kwargs.get('user_id', None)
        self.search_name = kwargs.get('search_name', None)
        self.url = kwargs.get('url', None)

    @classmethod
    def search(cls, user_id, sqlalchemy_query=None):
        """
        This method searches the saved searches by a registered user. If the query is provided as input then that is
        used for constructing the query otherwise default selection is used.
        """


        if sqlalchemy_query is None:
            query = meta.Session.query(cls)
        else:
            query = sqlalchemy_query
        query = query.filter(cls.user_id == user_id)
        return query

class DocumentIndex(NgdsDataObject):
    """
    DocumentIndex model represents the physical documents uploaded as part of resource which needs to be full-text indexed.
    *file_path - Full path of the uploaded document
    *status - explains the status of current document (NEW,CANCEL,COMPLETED)
    *comments - Any exception comments if there is an error.
    """

    def __init__(self, **kwargs):
        self.package_id = kwargs.get('package_id', None)
        self.resource_id = kwargs.get('resource_id', None)
        self.file_path = kwargs.get('file_path', None)
        self.status = kwargs.get('status', None)
        self.comments = kwargs.get('comments', None)

    @classmethod
    def search(cls, status, sqlalchemy_query=None):

        if sqlalchemy_query is None:
            query = meta.Session.query(cls)
        else:
            query = sqlalchemy_query
        query = query.filter(cls.status == status)
        return query


def define_tables():
    """Create the in-memory represenatation of tables, and map those tables to classes defined above"""
    
    # First define the tables
    bulkupload = Table(
        "bulk_upload",
        meta.metadata,
        Column("id", types.Integer, primary_key=True),
        Column("data_file", types.UnicodeText),
        Column("resources", types.UnicodeText),
        Column("path", types.UnicodeText),
        Column("status", types.UnicodeText),
        Column("comments", types.UnicodeText),
        Column("uploaded_by", types.UnicodeText, ForeignKey("user.id")),
        Column("uploaded_date", types.DateTime, default=datetime.datetime.now),
        Column('last_updated', types.DateTime, default=datetime.datetime.now),
    )

    bulkupload_package = Table(
        "bulk_upload_package",
        meta.metadata,
        Column("id", types.Integer, primary_key=True),
        Column("bulk_upload_id", types.Integer,ForeignKey("bulk_upload.id")),
        Column("package_name", types.UnicodeText),
        Column("package_title", types.UnicodeText),
        Column("uploaded_date", types.DateTime, default=datetime.datetime.now),
    )    

    standingdata = Table(
        "standing_data",
        meta.metadata,
        Column("id", types.Integer, primary_key=True),
        Column("code", types.UnicodeText),
        Column("description", types.UnicodeText),
        Column("data_type", types.UnicodeText),
    )    

    user_saved_search = Table(
        "user_saved_search",
        meta.metadata,
        Column("id", types.Integer, primary_key=True),
        Column("user_id", types.UnicodeText),
        Column("search_name", types.UnicodeText),
        Column("url", types.UnicodeText),
    )

    document_index = Table(
        "resource_document_index",
        meta.metadata,
        Column("id", types.Integer, primary_key=True),
        Column("package_id", types.UnicodeText),
        Column("resource_id", types.UnicodeText),
        Column("file_path", types.UnicodeText),
        Column("status", types.UnicodeText),
        Column("comments", types.UnicodeText),
        Column('last_updated', types.DateTime, default=datetime.datetime.now),
    )

    # Map those tables to classes, define the additional properties for related models
    meta.mapper(BulkUpload, bulkupload,
        properties={
            "uploaded_user": relationship(model.User)            
        }
    )
    meta.mapper(StandingData, standingdata)
    meta.mapper(BulkUpload_Package, bulkupload_package)
    meta.mapper(UserSearch, user_saved_search)
    meta.mapper(DocumentIndex, document_index)
    
    # Stick these classes into the CKAN.model, for ease of access later
    model.BulkUpload = BulkUpload
    model.StandingData = StandingData
    model.BulkUpload_Package = BulkUpload_Package
    model.UserSearch = UserSearch
    model.DocumentIndex = DocumentIndex
    
    return bulkupload, bulkupload_package, standingdata, user_saved_search, document_index

def db_setup():
    """Create tables in the database"""
    # These tables will already be defined in memory IConfigurer will make a call to define_tables()
    
    bulkupload = meta.metadata.tables.get("bulk_upload", None)
    bulkupload_package = meta.metadata.tables.get("bulk_upload_package", None)
    standingdata = meta.metadata.tables.get("standing_data", None)
    user_saved_search = meta.metadata.tables.get("user_saved_search", None)
    document_index = meta.metadata.tables.get("resource_document_index", None)

    if bulkupload == None:
        # The tables have not been defined. Its likely that the plugin is not enabled in the CKAN .ini file
        log.debug("Could not create additional tables. Please make sure that you've added the metadata plugin to your CKAN config .ini file.")
    else:    
        log.debug('Additional Metadata tables defined in memory')
        
        # Alright. Create the tables.
        from ckanext.ngds.base.commands.ngds_tables import create_tables
        create_tables([bulkupload,bulkupload_package,standingdata,user_saved_search,document_index], log)
