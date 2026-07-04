import os
import socket

from app import create_app, socketio

app = create_app()


def is_port_available(port, host='127.0.0.1'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def get_available_port(start_port=5000, host='127.0.0.1', max_attempts=20):
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(port, host):
            return port
    raise RuntimeError('No available local port found for the website.')


if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')
    requested_port = int(os.environ.get('PORT', '5000'))
    port = requested_port if is_port_available(requested_port, host) else get_available_port(requested_port, host)
    print(f'Starting website at http://{host}:{port}')
    socketio.run(app, host=host, port=port, debug=False, use_reloader=False)
