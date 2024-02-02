from flask import request
from flask_restful import Resource


class CsvImportController:
    
    def import_csv(self, csv_file) -> None:

        pass


class CsvImportView(Resource):
    def __init__(self, csv_import_controller: CsvImportController):
        self.controller = csv_import_controller

    """
    Upload a CSV file to import into the catalog.
    ---
    post:
        summary: Upload a CSV file to import into the catalog.
        requestBody:
            content:
                text/csv:
                    schema:
                        type: string
                        format: binary
            required: true            
        
    responses:
        '200':
            description: OK
        '400':
            description: Bad Request        
    """

    def post(self) -> None:
        csv_file = request.files["file"]
        self.controller.import_csv(csv_file )
