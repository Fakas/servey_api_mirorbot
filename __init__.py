from flask import Flask, send_file, url_for, request
from flask_restplus import Api, Resource, Namespace, reqparse
from os import path, environ
from werkzeug.exceptions import HTTPException, NotFound, UnsupportedMediaType, BadRequest
from werkzeug.datastructures import FileStorage
import json
from .identity import Schema
import os
import fleep
from tinytag import TinyTag

try:
    database_url = environ["SERVEY_DB_URL"]
except KeyError:
    raise EnvironmentError("Environment variable \"SERVEY_DB_URL\" must be set!") from None

sound_extensions = ("ogg", "mp3")

name = "ServeyMcServeface API (Miror Bot)"
app = Flask(name)


class SecureApi(Api):
    @property
    def specs_url(self):
        # HTTPS monkey patch
        scheme = "http" if ":5000" in self.base_url else "https"
        return url_for(self.endpoint("specs"), _external=True, _scheme=scheme)


api = SecureApi(app, doc="/")
api.title = "ServeyMcServeface API (Miror B.ot)"

announce = Namespace("announce")
api.add_namespace(announce)

directory_root = path.dirname(path.abspath(__file__))
directory_assets = path.join(directory_root, "assets")
directory_sounds = path.join(directory_assets, "sounds")

sound_upload = reqparse.RequestParser()
sound_upload.add_argument(
    "audio_file",
    type=FileStorage,
    location="files",
    required=True,
    help="Announce Sound (MP3/Ogg Vorbis)"
)


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
class GetSound(Resource):
    @staticmethod
    @api.doc("Get a user's announce sound")
    @announce.produces("audio/mp3")
    def get(discord_id):
        return send_file(get_announce_sound(discord_id))


@announce.route("/sound/<string:api_token>")
class SetSound(Resource):
    @staticmethod
    @api.doc("Update a user's announce sound")
    @api.expect(sound_upload)
    def post(api_token):
        identity = Schema(database_url)
        # Get user ID
        discord_id = identity.get_api_user(api_token)
        identity.close()
        # Get uploaded file
        sound = sound_upload.parse_args()["audio_file"]
        sound_file = sound.stream
        set_announce_sound(discord_id, sound_file)
        return "Success!"


def get_announce_sound(discord_id):
    identity = Schema(database_url)
    identity.register_event("ANONYMOUS", "ANNOUNCE_SOUND_GET", ip_addr=request.remote_addr)
    identity.close()
    for extension in sound_extensions:
        file_path = path.join(directory_sounds, f"{discord_id}.{extension}")
        if path.exists(file_path):
            return file_path
    raise NotFound(f"Announce sound for user ID \"{discord_id}\" not found!")


def set_announce_sound(discord_id, sound_file):
    identity = Schema(database_url)
    identity.register_event(discord_id, "ANNOUNCE_SOUND_SET", ip_addr=request.remote_addr)
    identity.close()
    # Check file isn't too big
    sound_file.seek(0, os.SEEK_END)
    size = sound_file.tell()
    if size > 500000:
        raise BadRequest("Uploaded file is too large!")
    # Read file
    sound_file.seek(0)
    sound_bytes = sound_file.read()
    # Verify file contents
    info = fleep.get(sound_bytes)
    mime = info.mime[0] if info.mime else None
    if mime == "audio/mpeg":
        extension = "mp3"
    elif mime == "audio/ogg":
        extension = "ogg"
    else:
        raise UnsupportedMediaType("Uploaded file must be audio/mpeg or audio/ogg!")
    # Check audio length
    temp_path = path.join(directory_sounds, f"{discord_id}_temp.{extension}")  # TinyTag sucks and only takes filenames
    with open(temp_path, "wb") as temp_file:
        temp_file.write(sound_bytes)
    tag = TinyTag.get(temp_path)
    if tag.duration > 5:
        raise BadRequest("Uploaded sound is too long!")
    # Remove any existing file
    for ext in sound_extensions:
        try:
            os.remove(path.join(directory_sounds, f"{discord_id}.{ext}"))
        except FileNotFoundError:
            pass
    # Make our temporary file permanent!
    os.rename(temp_path, path.join(directory_sounds, f"{discord_id}.{extension}"))


def main():
    app.run()


if __name__ == "__main__":
    main()
