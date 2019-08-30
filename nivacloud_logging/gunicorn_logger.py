import gunicorn.glogging

from nivacloud_logging.log_utils import setup_logging


class Logger(gunicorn.glogging.Logger):
    def __init__(self, cfg):
        super().__init__(cfg)
        # Bleh. This feels hacky and awful, but so does Gunicorn...
        setup_logging(min_level=self.loglevel)
