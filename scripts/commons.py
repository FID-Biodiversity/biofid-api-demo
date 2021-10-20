import json
import logging
import urllib.parse
from typing import Union, List

import requests

from .logger import setup_logging

UTF8_STRING = 'utf-8'
XML_PARSER = 'lxml'
log = setup_logging(logging.DEBUG)

CLASS_STRING = 'class'
SEARCH_TERM_STRING = 'search-term'
TAXON_ANNOTATION_CLASS_STRINGS = ['taxon', 'plant_flora', 'animal_flora']


class Biofid:
    """ Allows an easy access to the BIOfid API functions. """

    BASE_URL = 'https://www.biofid.de/api/v1/'

    def get_term_context(self, term: str) -> dict:
        """ Calls for the corpus context of a given term or URI.
            These are terms that co-occur with the given term multiple times in the corpus.
        """
        method_name = 'getTermContext'
        parameter_name = 'term'

        return self._get_data(method_name, {parameter_name: term})

    def get_document_metadata(self, document_id: Union[str, List[str]]) -> dict:
        """ Returns the document metadata from the BIOfid corpus for the given document ID(s).
            The document ID can be either a string or a list of document ID strings.
        """
        method_name = 'getDocumentMetadata'
        parameter_name = 'docId'

        return self._get_data(method_name, parameters={parameter_name: document_id})

    def get_biofid_data_for_uri(self, uri: str):
        """ Calls the BIOfid website for knowledge data on the given URI. """
        return call_url(uri)

    def _get_data(self, method_name, parameters) -> dict:
        url_string = generate_url(self.BASE_URL, method_name)

        return call_url(url_string, parameters)


def call_url(url: str, parameters: dict = None, authentication=None,
             response_content_type: str = 'application/json') -> dict:
    """ Calls a given URL and returns the response as dict.
        Parameters are optional.
    """
    log.info(f'Calling URL {url}...')
    log.debug(f'Parameters: {parameters}')
    log.debug(f'Response Content Type: {response_content_type}')

    headers = {'Content-type': response_content_type}
    response = requests.get(url, params=parameters, auth=authentication, headers=headers)
    
    log.debug('Received response!')

    content = response.content.decode(UTF8_STRING)

    if response.status_code != 200:
        log.error(f'The server responded with an error: {response.status_code} -> {content}')
        raise ConnectionError(f'The BIOfid API returned {response.status_code}! '
                              f'Message: {content}')

    log.debug(f'Received content: {content}')

    return json.loads(content)


def get_gbif_occurrences_for_germany(gbif_taxon_key: str, year: str = '2020', country: str = 'DE') -> list:
    response_data = call_url(url=f'https://api.gbif.org/v1/occurrence/search?taxonKey={gbif_taxon_key}'
                                 f'&eventDate={year}&country={country}&limit=300')
    return response_data['results']


def generate_url(base_url: str, method_name: str) -> str:
    return urllib.parse.urljoin(base_url, method_name)


def read_json_file_content(json_file_path: str) -> dict:
    with open(json_file_path, 'r') as json_file:
        json_data = json_file.read()

    return json.loads(json_data)
