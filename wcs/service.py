"""
List all coverages, or get full information about a particular coverage
from a WCS endpoint.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Optional

import requests
from requests import HTTPError
from requests.auth import HTTPBasicAuth

from wcs.model import WCSClientException, FullCoverage, BasicCoverage
from wcs.parser import parse_coverage_summaries, parse_describe_coverage

DEFAULT_CONN_TIMEOUT = 10
"""Default timeout to establish a connection to the WCS service: 10 seconds."""
DEFAULT_READ_TIMEOUT = 10 * 60
"""Default timeout to wait for a query to execute: 10 minutes."""


class WebCoverageService:
    """
    Establish a connection to a WCS service, send requests and retrieve results.

    :param endpoint: the WCS server endpoint URL, e.g. https://ows.rasdaman.org/rasdaman/ows
    :param username: optional username for basic authentication to the WCS server
    :param password: optional password for basic authentication to the WCS server
    :param conn_timeout: how long (seconds) to wait for the connection to be established
    :param read_timeout: how long (seconds) to wait for the query to execute

    Example usage:

    .. code:: python

        service = WebCoverageService(
            "https://ows.rasdaman.org/rasdaman/ows")

        coverages = service.list_coverages()
        avg_land_temp = coverages['AvgLandTemp']

        full_avg_land_temp = service.list_full_info('AvgLandTemp')
    """

    def __init__(self,
                 endpoint: str,
                 username: str = None,
                 password: str = None,
                 conn_timeout: int = DEFAULT_CONN_TIMEOUT,
                 read_timeout: int = DEFAULT_READ_TIMEOUT):
        self.endpoint = endpoint
        self.auth = HTTPBasicAuth(username, password) if username and password else None
        """Map of coverage objects retreived from the ``endpoint``, as (name, coverage) pairs."""
        self.conn_timeout = conn_timeout
        self.read_timeout = read_timeout
        self.version = "2.1.0"
        self.service = "WCS"

    def list_coverages(self) -> dict[str, BasicCoverage]:
        """
        Retreives the available coverages from the WCS server with a GetCapabilities request.

        :return: a dict of (coverage name, :class:`wcs.model.BasicCoverage`) pairs
            for each available coverage.

        :raise WCSClientException: if resolving the GetCapabilities or parsing it fails.
        """
        params = {'service': self.service,
                  'request': 'GetCapabilities'}
        response = self._send_request(params)
        coverages = parse_coverage_summaries(response.text)
        return {cov.name: cov for cov in coverages}

    def list_full_info(self, coverage_name) -> FullCoverage:
        """
        Retrieve full information of coverage ``nacoverage_nameme`` with a
        DescribeCoverage request.

        :param coverage_name: coverage name to lookup
        :raise WCSClientException: if the coverage does not exist, or its
            DescribeCoverage document fails to parse.
        """
        params = {'service': self.service,
                  'version': self.version,
                  'outputType': 'GeneralGridCoverage',
                  'request': 'DescribeCoverage',
                  'coverageId': coverage_name}
        response = self._send_request(params)
        return parse_describe_coverage(response.text)

    def _send_request(self, params: dict[str, str]) -> requests.Response:
        """
        Sends a request to the service and return the raw :class:`requests.Response` object.

        :param params: key/value parameters to be added to the :attr:`WebCoverageService.endpoint`.
        :return: the response object from evaluating the query.
        :raise wcs.model.WCSClientException: if the server returns an error status code.
        :meta private:
        """
        # prepare request parameters

        # make request
        response = requests.get(self.endpoint,
                                params=params,
                                auth=self.auth,
                                timeout=(self.conn_timeout, self.read_timeout))

        # check for errors from the server
        try:
            response.raise_for_status()
        except HTTPError as ex:
            err = self._parse_error_xml(response.text)
            if err is not None:
                raise WCSClientException(err) from ex
            raise ex

        return response

    @staticmethod
    def _parse_error_xml(xml_str: Optional[str | bytes]) -> Optional[str]:
        """
        Parse an ows:ExceptionReport returned by the WCS server to extract the
        ows:ExceptionText elements for a human-readable error.
        :param xml_str: the error as a string/bytes; may be None.
        :return: the extracted error message, or None if xml_str is None
        :meta private:
        """
        if xml_str is None:
            return None
        try:
            namespaces = {'ows': 'http://www.opengis.net/ows/2.0'}
            root = ET.fromstring(xml_str)
            exceptions = root.findall('.//ows:Exception', namespaces)
            ret = []
            for ex in exceptions:
                err = ''
                ex_code = ex.get('exceptionCode')
                if ex_code is not None:
                    err = ex_code + ': '
                exception_texts = ex.findall('.//ows:ExceptionText', namespaces)
                for ex_text in exception_texts:
                    err += ex_text.text
                ret.append(err)
            return '\n'.join(ret)
        except ET.ParseError:
            return xml_str
