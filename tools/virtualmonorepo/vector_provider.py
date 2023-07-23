#!/usr/bin/env python3

import json

from virtualmonorepo.log import logger
from virtualmonorepo.httpclient import get


class VectorProvider:

    def __init__(self):
        pass

    def provide(self):
        pass


class HttpVectorProvider(VectorProvider):

    def __init__(self, url):
        self.url = url

    def provide(self) -> str:
        logger.debug("About to read vector from provider. url: {}".format(
            self.url))
        result = None
        response = get(self.url)
        if not response.success():
            if response.error.is_timeout:
                logger.error(
                    "Timeout during fetching new VMR definitions from remote, "
                    +
                    "make sure you have access to the provider network (connect to VPN?). url: {}"
                    .format(self.url))
            else:
                logger.error(
                    "Fetching raw vector from provider failed, " +
                    "make sure you have access to the provider network (connect to VPN?). url: {}, error: {}"
                    .format(self.url, response.error.message))
        else:
            if response.content is not None:
                json_res = json.loads(response.content)
                if len(json_res) == 0:
                    logger.error(
                        f"Failed to resolve vector, unsupported OS/Architecture. url: {self.url}"
                    )
                else:
                    result = response.content
                    logger.debug("Successfully read raw vector from provider")
            else:
                logger.error(f"Vector response is empty. url: {self.url}")

        return result
