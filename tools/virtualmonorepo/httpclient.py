#!/usr/bin/env python3

from urllib.request import urlopen
from urllib.error import URLError
import socket

from virtualmonorepo.log import logger


class ErrorResponse:

    def __init__(self, exception):
        self.message = str(exception)
        self.is_timeout = exception is URLError


class HttpResponse:

    error: ErrorResponse

    def __init__(self, content, error=None):
        self.content = content
        self.error = error

    def success(self):
        return self.error is None


def get(url, timeout=30):
    response = None
    try:
        raw_text = urlopen(url, timeout=timeout).read().decode('utf-8')
        response = HttpResponse(raw_text)
    except URLError as url_err:
        logger.error("HTTP Get request failed. URLError = {}".format(url_err))
        response = HttpResponse(None, ErrorResponse(url_err))
    except socket.timeout as socket_timeout:
        logger.error(
            "HTTP Get request failed due to timeout ({} sec)".format(timeout))
        response = HttpResponse(None, ErrorResponse(socket_timeout))

    return response
