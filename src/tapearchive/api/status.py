from flask_restful import Resource

class ContianerHeartbeat(Resource):
    def get(self) -> str:
        return ""

