from flask import jsonify
from functools import wraps
from flask import request, abort
from werkzeug.contrib.cache import SimpleCache
import logging
import configparser
import json
from data_provider_service import DataProviderService
from flask import make_response
import hashlib
import datetime
import time

config = configparser.RawConfigParser()
config.read('config.properties')

logging.basicConfig(filename=config.get('Default', 'log_file'), level=logging.DEBUG)

cache = SimpleCache()

config = configparser.RawConfigParser()
config.read('config.properties')

oracle_connection_string = 'oracle+cx_oracle://{username}:{password}@{hostname}:{port}/{sid}'

db_engine = oracle_connection_string.format(
    username=config.get('DatabaseSection', 'username'),
    password=config.get('DatabaseSection', 'password'),
    hostname=config.get('DatabaseSection', 'hostname'),
    port=config.get('DatabaseSection', 'port'),
    sid=config.get('DatabaseSection', 'sid')
)

DATA_PROVIDER = DataProviderService(db_engine)


# The actual decorator function


def require_app_key(view_function):
    @wraps(view_function)
    # the new, post-decoration function. Note *args and **kwargs here.
    def decorated_function(*args, **kwargs):
        with open('api.key', 'r') as api_key:
            key = api_key.read().replace('\n', '')
            user_name = request.headers.get('x-api-user')
            if user_name:
                user = DATA_PROVIDER.get_user(user_name)
                if user and user.active_user_flag == 'Y':
                    user_validated = 1
                else:
                    user_validated = 0
            else:
                abort(401)
            comp_key = request.headers.get('x-api-key')
            # ip_address = request.headers.getlist("X-Forwarded-For")[0]
            ip_address = request.remote_addr
            call_time = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d%H:%M:%S')
            logging.info("Validating key " + comp_key)
        if ip_address and user_validated == 1 and request.headers.get('x-api-key') and request.headers.get('x-api-key') == key:
            logging.info("Validated")
            validated = 1
            new_log_details_id = DATA_PROVIDER.log_details(user_name, ip_address, call_time, validated)
            if new_log_details_id:
                logging.info("Logged")
                return view_function(*args, **kwargs)
            else:
                #
                # In case we could not log the server is down
                # we send HTTP 404 - Not Found error to the client
                #
                logging.info("failed Logging")
                abort(404)
        else:
            validated = 0
            new_log_details_id = DATA_PROVIDER.log_details(user_name, ip_address, call_time, validated)
            if new_log_details_id:
                logging.info("Logged")
            else:
                logging.info("failed logging")
            abort(401)

    return decorated_function


@require_app_key
def get_ocr_protocols():
    cp = cache.get('protocol-list')
    if cp is not None:
        logging.info("Cached result")
        return cp
    else:
        protocols_list = DATA_PROVIDER.get_protocols()
        if protocols_list:
            data = {"protocols": protocols_list, "total": len(protocols_list)}
            json_data = json.dumps(data)
            cp = jsonify(data)
            cache.set('protocol-list', cp, timeout=config.getfloat('Default', 'timeout'))
            response = make_response(cp, 200)
            # response.headers["ETag"] = str(hashlib.sha256(json_data).hexdigest())
            response.headers["Cache-Control"] = "private, max-age=300"
            return response
        else:
            #
            # In case we did not find any protocols i.e the server is down
            # we send HTTP 404 - Not Found error to the client
            #
            abort(404)
