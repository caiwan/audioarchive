from flask_restful import Resource

class ContianerHeartbeat(Resource):
    def get(self) -> str:
        """
        Returns a heartbeat message to indicate that the container is alive.
        """
        return ""

