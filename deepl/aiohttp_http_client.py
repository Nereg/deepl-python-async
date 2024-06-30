# Copyright 2024 DeepL SE (https://www.deepl.com)
# Use of this source code is governed by an MIT
# license that can be found in the LICENSE file.
import aiohttp
import ssl
from typing import Union, Dict

from .translator_base import HttpResponse
from .iasync_http_client import IAsyncHttpClient
from .ihttp_client import IPreparedRequest
from .translator_base import HttpRequest


class AioHttpHttpClient(IAsyncHttpClient):
    def __init__(
        self,
        proxy: Union[Dict, str, None] = None,
        verify_ssl: Union[bool, str, None] = None,
    ):
        self._ssl = verify_ssl
        self._proxy = proxy
        # if we were passed a path to a file/folder with CA certificates
        if type(self._ssl) is str:
            # pass them onto SSL context
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(
                    ssl_context=ssl.create_default_context(
                        ssl.Purpose.SERVER_AUTH,
                        cafile=self._ssl,
                        capath=self._ssl,
                    )
                ),
                # replicate request's behavior
                # https://docs.aiohttp.org/en/stable/client_advanced.html#proxy-support
                trust_env=True if self._proxy is not None else False,
            )
        else:
            # create default client session
            self._session = aiohttp.ClientSession(
                trust_env=True if self._proxy is not None else False,
            )
        # TODO proxy

        super().__init__()

    async def close(self):
        await self._session.close()

    def prepare_request(self, request: HttpRequest) -> IPreparedRequest:
        return IPreparedRequest(request)

    def return_proxy_url(self) -> str:
        """
        Returns URL of the proxy to use.
        Handles choosing what to use in the dict that requests support
        """
        if type(self._proxy) is str:
            return self._proxy
        elif type(self._proxy) is dict:
            # prefer http proxies, see:
            # https://docs.aiohttp.org/en/stable/client_advanced.html#proxy-support
            if "http" in self._proxy:
                return self._proxy["http"]
            elif "https" in self._proxy:
                return self._proxy["https"]
            else:
                raise ValueError(
                    "No suitable proxy scheme found!"
                )  # TODO: implement this kind of error in exceptions.py
        else:
            raise ValueError("Invalid proxy type!")

    async def send_async_request(
        self, prepared_request: IPreparedRequest, timeout: float
    ) -> HttpResponse:
        request = prepared_request.request

        async with self._session.request(
            request.method,
            request.url,
            headers=request.headers,
            data=request.data,
            json=request.json,
            # disable the SSL verification, if we don't have a path to certificates
            ssl=self._ssl if type(self._ssl) is bool else None,
            # pass the proxy URL, if we have a proxy at all
            proxy=self.return_proxy_url() if self._proxy is not None else None,
            # stream=request.stream, TODO
        ) as response:
            content = await response.text()
            return HttpResponse(
                response.status, content, dict(response.headers)
            )
