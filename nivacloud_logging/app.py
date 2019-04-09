from nivacloud_logging.log_utils import setup_logging

setup_logging()


# Start with:
# $ gunicorn --workers=2 --preload --access-logfile - --log-level info nivacloud_logging.app:app


def app(environ, start_response):
    data = b'Hello, World!'
    status = '200 OK'
    response_headers = [
        ('Content-Type', 'text/plain'),
        ('Content-Length', str(len(data))),
    ]
    start_response(status, response_headers)
    return iter([data])
