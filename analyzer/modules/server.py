from argparse import Namespace, ArgumentParser

from flask import Flask, request # pylint: disable=W0611

from common.util import load_module, MODULES

DEFAULT_SERVER_PORT = 8085

def run(super_args):
    app = Flask(__name__)
    @app.route('/modules')
    def list_modules():
        return MODULES
    @app.route('/module/<string:module_name>', methods=['POST'])
    def run_module(module_name):
        module = load_module(module_name)
        parser = ArgumentParser()
        subparsers = parser.add_subparsers(dest='command')
        module.add_subparser(module_name, subparsers)
        args = [module_name]
        for k,v in request.form.items():
            args += [f'--{k}', v]
        args = parser.parse_args(args)
        vars(super_args).update(vars(args))
        return module.run(super_args)
    app.run()

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
