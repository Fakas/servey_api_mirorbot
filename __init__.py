from flask import Flask, send_file
from flask_restplus import Api, Resource, Namespace
from os import path
from werkzeug.exceptions import HTTPException, NotFound
import json
from . import identity

sound_extensions = ("ogg", "mp3")

name = "ServeyMcServeface API (Miror Bot)"
app = Flask(name)

api = Api(app, doc="/")
api.title = "ServeyMcServeface API (Miror B.ot)"

announce = Namespace("announce")
api.add_namespace(announce)

directory_root = path.dirname(path.abspath(__file__))
directory_assets = path.join(directory_root, "assets")
directory_sounds = path.join(directory_assets, "sounds")


@app.errorhandler(HTTPException)
def exception_handler(exception):
    response = exception.get_response()
    response.data = json.dumps({
        "code": exception.code,
        "name": exception.name,
        "description": exception.description,
    })
    response.content_type = "application/json"
    return response


@announce.route("/sound/<string:discord_id>")
class Sound(Resource):
    @staticmethod
    @api.doc("Get a user's announce sound")
    @announce.produces("audio/mp3")
    def get(discord_id):
        for extension in sound_extensions:
            try:
                file_path = path.join(directory_sounds, f"{discord_id}.{extension}")
                return send_file(file_path)
            except FileNotFoundError:
                continue
        raise NotFound(f"Announce sound for user ID \"{discord_id}\" not found!")


def main():
    app.run()


if __name__ == "__main__":
    main()
