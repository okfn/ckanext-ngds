''' ___NGDS_HEADER_BEGIN___

National Geothermal Data System - NGDS
https://github.com/ngds

File: <filename>

Copyright (c) 2013, Siemens Corporate Technology and Arizona Geological Survey

Please Refer to the README.txt file in the base directory of the NGDS
project:
https://github.com/ngds/ckanext-ngds/README.txt

___NGDS_HEADER_END___ '''

import json

class PostGISDatastoreDef:
    def __init__(self, workspace):
        
        self.workspace = {
            "name": workspace.name,
            "href": workspace.href
        }
        
        # default values
        port = '5432'
        host = "localhost"
        password = 'geoserver'
        user = 'admin'
        database = 'datastore'
        
        
        self.connectionParameters = [
            ("Connection timeout", "20"),
            ("port", port),
            ("passwd", password),
            ("dbtype", "postgis"),
            ("host", host),
            ("validate connections", "false"),
            ("max connections", "10"),
            ("database", database),
            ("namespace", self.workspace["href"]),
            ("schema", "public"),
            ("Loose bbox", "true"),
            ("Expose primary keys", "false"),
            ("Max open prepared statements", "50"),
            ("preparedStatements", "false"),
            ("Estimated extends", "true"),
            ("user", user),
            ("min connections", "1"),
            ("fetch size", "1000"),                                         
        ]
        
    def serialize(self):
        return json.dumps({
            "dataStore": {
                "name": "django",
                "type": "PostGIS",
                "enabled": True,
                "workspace": self.workspace,
                "connectionParameters": {
                    "entry": [{"@key": key[0], "$": key[1]} for key in self.connectionParameters]                        
                },
                "__default": False
            }           
        })
