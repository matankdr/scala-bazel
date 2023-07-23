import http.client as http
import ssl
from typing import Callable

_DEFAULT_HTTP_CONNECTION_TIMEOUT = 3.0


class http_client:
    """
    A simple HTTP client utility which is based on the built in Python http client module in order to avoid third party
    dependencies.

    This implementation is designed to be used by a single thread! It attempts to use a single lazily negotiated and
    cached HTTP connection in order to improve the performance os sequential HTTP calls.
    """

    def __init__(self,
                 host,
                 https=False,
                 port=None,
                 timeout=_DEFAULT_HTTP_CONNECTION_TIMEOUT):

        if https:
            _new_connection_fn = \
                _new_https_connection_fn(host=host, port=port, timeout=timeout, context=ssl.create_default_context())
        else:
            _new_connection_fn = \
                _new_http_connection_fn(host=host, port=port, timeout=timeout)

        self._cached_http_conn = _LazyCachedHTTPConnection(new_conn_fn=_new_connection_fn)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._cached_http_conn.is_initialized():
            self._cached_http_conn.close()

        if exc_val is not None:
            raise exc_val

    def connection(self):
        return self._cached_http_conn


class _LazyCachedHTTPConnection:
    def __init__(self, new_conn_fn: Callable[[], http.HTTPConnection]):
        self._http_conn = None
        self._new_conn = new_conn_fn

    def request(self, method, url, body=None, headers=None, *, encode_chunked=False):
        if headers is None:
            headers = {}

        if self._http_conn is None:
            self._http_conn = self._new_conn()

        try:
            if encode_chunked:
                self._http_conn.request(method=method, url=url, body=body, headers=headers, encode_chunked=encode_chunked)
            else: # support python 3.5 on CI (until we upgrade python on CI)
                self._http_conn.request(method=method, url=url, body=body, headers=headers)
        except ConnectionError:
            self._http_conn.close()

            raise

    def is_initialized(self):
        return self._http_conn is not None

    def __getattr__(self, attr):
        return getattr(self._http_conn, attr)


def _new_https_connection_fn(host, port, timeout, context) -> lambda: http.HTTPSConnection:
    return lambda: http.HTTPSConnection(
        host=host,
        port=port if port is not None else 443,
        timeout=timeout,
        context=context,
    )


def _new_http_connection_fn(host, port, timeout):
    return lambda: http.HTTPConnection(
        host=host,
        port=port if port is not None else 80,
        timeout=timeout,
    )
