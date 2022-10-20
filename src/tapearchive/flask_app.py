import json
from flask import Flask, make_response
from flask_restful import Api

from tapearchive.api import (
    catalog, 
    status,
)

from tapearchive.app import create_db_connection
from tapearchive.config import AppConfig

from tq.database import CustomJSONEncoder

# TODO: Separate flask from the rest of the application

API_V1_PREFIX = "/api/v1"


def create_flask_app(config: AppConfig):
    connection_pool = create_db_connection(config)
    app = Flask(__name__)
    api = Api(app)

    catalog_controller = catalog.CatalogController(connection_pool)

    @api.representation('application/json')
    def output_json(data, code, headers=None):
        resp = make_response(json.dumps(data, cls=CustomJSONEncoder), code)
        resp.headers.extend(headers or {})
        return resp

    # TODO: Add error handlers

    api.add_resource(status.ContianerHeartbeat, f"{API_V1_PREFIX}/heartbeat")
    api.add_resource(catalog.CatalogEntryView, f"{API_V1_PREFIX}/catalog/<string:catalog_name>", resource_class_args=[catalog_controller])
    api.add_resource(catalog.CatalogListView, f"{API_V1_PREFIX}/catalog_names/", resource_class_args=[catalog_controller])
    
    return app
