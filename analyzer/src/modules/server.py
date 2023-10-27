from argparse import Namespace, ArgumentParser
import json

from flask import Flask, request, abort, jsonify, make_response # pylint: disable=W0611
from flask_cors import CORS

from common.util import load_module, MODULES, map_color_option

DEFAULT_SERVER_PORT = 5000

def run(super_args):
    app = Flask(__name__)
    @app.route('/')
    def healthcheck():
        return 'ayy'
    @app.route('/module/<string:module_name>', methods=['POST'])
    def run_module(module_name):
        try:
            module = load_module(module_name)
        except:
            return make_response(f'Module not found: {module_name}', 400)
        parser = ArgumentParser()
        subparsers = parser.add_subparsers(dest='command')
        module.add_subparser(module_name, subparsers)
        args = [module_name]
        for k,v in request.json.items():
            if type(v) == list:
                args += [f'--{k}'] + [str(e) for e in v]
            else:
                args += [f'--{k}', str(v)]
        args = parser.parse_args(args)
        args = map_color_option(args)
        return module.run(args)
    CORS(app)
    app.run(port=super_args.port)

def add_subparser(action_name, subparsers):
    server_parser = subparsers.add_parser(
        action_name, help='serve analysis data over http')
    server_parser.add_argument(
        '-p',
        '--port',
        type=int,
        default=DEFAULT_SERVER_PORT,
        help='server port'
    )
