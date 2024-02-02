import json
import logging
from flask import Flask, make_response
from flask_restful import Api
from flasgger import APISpec, Swagger

from apispec.ext.marshmallow import MarshmallowPlugin

from tapearchive.api import (
    catalog,
    status,
)

from tapearchive.app import create_db_connection
from tapearchive.config import AppConfig

from tq.database import CustomJSONEncoder

# TODO: Separate flask from the rest of the application

API_V1_PREFIX = "/api/v1"

LOGGER = logging.getLogger(__name__)


def create_apispec(app: Flask, api:Api) -> Swagger:
    # Create an APISpec
    spec = APISpec(
        title="Tape Archive API",
        version="0.0.1",
        openapi_version="2.0",
        plugins=[
            MarshmallowPlugin(),
        ],
    )

    with app.test_request_context():
        spec.components.schema("CatalogEntrySchema", schema=catalog.CatalogEntrySchema)
        
    template = spec.to_flasgger(
        app,
        paths=spec.to_dict()["paths"],
    )


    return Swagger(app, template=template)


def create_flask_app(config: AppConfig):
    connection_pool = create_db_connection(config)
    app = Flask(__name__)
    api = Api(app)

    catalog_controller = catalog.CatalogController(connection_pool)

    @api.representation("application/json")
    def output_json(data, code, headers=None):
        resp = make_response(json.dumps(data, cls=CustomJSONEncoder), code)
        resp.headers.extend(headers or {})
        return resp

    # TODO: Add error handlers

    api.add_resource(status.ContianerHeartbeat, f"{API_V1_PREFIX}/heartbeat")
    api.add_resource(
        catalog.CatalogEntryView,
        f"{API_V1_PREFIX}/catalog/<string:catalog_name>",
        resource_class_args=[catalog_controller],
    )
    api.add_resource(
        catalog.CatalogListView,
        f"{API_V1_PREFIX}/catalog_names/",
        resource_class_args=[catalog_controller],
    )

    create_apispec(app, api)

    return app
