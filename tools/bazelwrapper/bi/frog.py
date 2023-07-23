import gzip
import json
import os
from typing import List
from urllib.parse import urlencode, quote

from bazelwrapper.utils.logging import get_default_logger
from bazelwrapper.utils.simple_http_client import http_client

_FROG_HOSTNAME_ENV_VAR_NAME = "WIX_DEVEX_DEBUG_FROG_HOSTNAME"
_FROG_HOSTNAME = 'frog.wix.com'

_JSON_CONTENT_HEADERS = {'Content-Type': 'application/json; charset=UTF-8'}
_FORM_CONTENT_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
}
_FORM_GZIP_CONTENT_HEADERS = {
    **_FORM_CONTENT_HEADERS,
    'Content-Encoding': 'gzip'
}
_DEFAULT_HTTP_CONNECTION_TIMEOUT = 10.0


class ProjectMeta:
    def __init__(self, project, source_id):
        self.project = project
        self.source_id = source_id

    def __eq__(self, other):
        return isinstance(other, EventMeta) and \
               self.__dict__.__eq__(other.__dict__)


class EventMeta(ProjectMeta):
    def __init__(self, project, source_id, event_id):
        super().__init__(project, source_id)
        self.event_id = event_id

    def __eq__(self, other):
        return isinstance(other, EventMeta) and \
               self.__dict__.__eq__(other.__dict__)


class BiEvent:
    def __init__(self, data: dict, headers: dict, meta: EventMeta):
        self.data = data
        self.headers = headers
        self.meta = meta

    def to_bi_schema(self, include_headers=True) -> dict:
        bi_event = self.data

        if include_headers:
            bi_event = {**self.headers, **self.data}

        return bi_event


class BatchEvent:
    def __init__(self, dt: int, f: BiEvent):
        self._dt = dt
        self._f = f

    def to_bi_schema(self):
        return {
            "dt": self._dt,
            "f": {
                **self._f.to_bi_schema(include_headers=False),
                "evid": self._f.meta.event_id
            }
        }


class Batch:
    def __init__(self, dt: int, g: dict, e: List[BatchEvent], meta: ProjectMeta):
        """
        Constructs a frog batch object. Parameter names deliberately follow BI protocol names.
        See: https://kb.wixpress.com/display/BI/Batch+reporting+api

        :param dt: batch time offset
        :param g: common event fields
        :param e: batch event list
        :param meta: target BI project meta-data
        """
        self._dt = dt
        self._g = {**g, "src": meta.source_id}
        self._e = e
        self.meta = meta

    def payload(self):
        return {
            "dt": self._dt,
            "g": self._g,
            "e": [event.to_bi_schema() for event in self._e],
        }


class client(http_client):
    """
    A context manager style http client for frog devex endpoints
    """

    def __init__(self, timeout=_DEFAULT_HTTP_CONNECTION_TIMEOUT):
        super().__init__(host=_frog_hostname(), timeout=timeout)

    def post_form(self, event: BiEvent, use_gzip=False):
        logger = get_default_logger()
        is_successful = False
        response = None

        def prepare_body():
            utf8_data = urlencode(
                query=_bi_payload_for(event),
                quote_via=quote,
            ).encode('utf-8')

            if use_gzip:
                return gzip.compress(utf8_data)
            else:
                return utf8_data

        try:
            connection = self.connection()
            connection.request(
                method='POST',
                url=_endpoint(event.meta),
                body=prepare_body(),
                headers=_FORM_CONTENT_HEADERS if not use_gzip else _FORM_GZIP_CONTENT_HEADERS,
            )
            response = connection.getresponse()
            status = response.status

            is_successful = 200 <= status <= 300
            if not is_successful:
                logger.warn("{status} {reason}".format(status=status, reason=response.reason))

            response.read()

        finally:
            if response is not None:
                response.close()

        return is_successful

    def post_batch(self, batch: Batch, use_gzip=False):
        logger = get_default_logger()
        is_successful = False
        response = None

        def prepare_body():
            utf8_data = json.dumps(batch.payload()).encode("utf-8")

            if use_gzip:
                return gzip.compress(utf8_data)
            else:
                return utf8_data

        try:
            connection = self.connection()
            connection.request(
                method='POST',
                url=_endpoint(batch.meta),
                body=prepare_body(),
                headers=_JSON_CONTENT_HEADERS,
            )
            response = connection.getresponse()
            status = response.status

            is_successful = 200 <= status <= 300
            if not is_successful:
                logger.warn("{status} {reason}".format(status=status, reason=response.reason))

            response.read()

        finally:
            if response is not None:
                response.close()

        return is_successful


def _bi_payload_for(event: BiEvent):
    return {
        'src': event.meta.source_id,
        'evid': event.meta.event_id,
        **event.to_bi_schema(include_headers=True).copy()
    }


def _endpoint(meta: ProjectMeta):
    return "/{endpoint}".format(endpoint=meta.project)


def _frog_hostname():
    return os.getenv(_FROG_HOSTNAME_ENV_VAR_NAME, _FROG_HOSTNAME)
