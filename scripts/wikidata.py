import re
from dataclasses import dataclass
from typing import List

from SPARQLWrapper import SPARQLWrapper, JSON

WIKIDATA_SPARQL_ENDPOINT = 'https://query.wikidata.org/sparql'
coordinates_extraction_regex = re.compile(r'Point\((?P<longitude>[0-9.]*?) (?P<latitude>[0-9.]*?)\)')
user_agent = "BIOfid-Search-Evaluator/1.0 (https://biofid.de/en/contact/; biofid@ub.uni-frankfurt.de) Python/3.8"


@dataclass
class Point:
    longitude: float
    latitude: float
    wikidata_uri: str


def get_coordinates_for_wikidata_uris(uris: List[str]) -> List[Point]:
    """ Returns a Point object with the coordinates from the given Wikidata URI.
        Returns None, if there is no Point data available.
    """
    converted_uris = [f'wd:{re.search(r"Q[0-9]*$", uri).group()}' if uri is not None else None for uri in uris]

    coordinate_query_string = f"""
    SELECT ?wikidataUri ?locationUri ?coordinates {{
        VALUES ?locationUri {{ {' '.join(converted_uris)} }}
        ?locationUri wdt:P625 ?coordinates
    }}
    """

    point_data = get_data_from_wikidata(coordinate_query_string)
    return [compile_point(row) for row in point_data]


def get_data_from_wikidata(query_string) -> List[dict]:
    response = query_wikidata(query_string)
    return response['results']['bindings']


def compile_point(wikidata_response_row: dict) -> Point:
    point_string = get_value(wikidata_response_row['coordinates'])
    regex_point_data = coordinates_extraction_regex.search(point_string)
    return Point(latitude=float(regex_point_data.group('latitude')),
                 longitude=float(regex_point_data.group('longitude')),
                 wikidata_uri=get_value(wikidata_response_row.get('locationUri'))
                 )


def get_value(data: dict):
    return data['value']


def query_wikidata(query_string: str) -> str:
    sparql = SPARQLWrapper(WIKIDATA_SPARQL_ENDPOINT, agent=user_agent)
    sparql.setQuery(query_string)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()
