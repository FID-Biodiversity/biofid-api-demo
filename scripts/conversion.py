import json
import re
from typing import List, Optional

import pandas as pd
from pandas import DataFrame

from .biofid_data import TaxonLocationData
from .wikidata import Point


def convert_taxon_location_data_to_dataframe(taxon_location_data: List[TaxonLocationData],
                                             coordinates: List[Optional[Point]]) -> DataFrame:

    point_index = _generate_index_from_coordinates(coordinates)

    def map_data(row_data: TaxonLocationData) -> dict:
        document = row_data.source_page.parent_document
        point = point_index.get(row_data.location.wikidata_uri, Point(None, None, None))

        return {
            'taxon_label': row_data.taxon.label,
            'taxon_biofid_uri': row_data.taxon.biofid_uri,
            'taxon_wikidata_uri': row_data.taxon.wikidata_uri,
            'location_label': row_data.location.label,
            'location_wikidata_uri': row_data.location.wikidata_uri,
            'page_url': re.sub(r'\?query=.*', '', row_data.source_page.url),
            'document_title': document.title,
            'document_publication_year': document.publication_year,
            'document_url': document.url,
            'longitude': [point.longitude],
            'latitude': [point.latitude]
        }

    return pd.concat([DataFrame.from_dict(map_data(data)) for data in taxon_location_data], ignore_index=True)


def convert_biofid_response_to_dataframe(response_file_path):
    with open(response_file_path, 'r') as ifile:
        file_content = ifile.read()

    data = json.loads(file_content)
    documents = data['data']

    def map_data(document_metadata: dict) -> dict:
        taxon_count_in_document = sum(int('taxon' in annotation or 'plant_flora' in annotation)
                                      for pages in document_metadata['TextExtracts']
                                      for page in pages
                                      for annotation in page)

        return {
            'taxon_count': taxon_count_in_document,
            'document_publication_year': [document_metadata['PublicationYear']],
            'document_title': document_metadata['Title'],
            'document_url': document_metadata['URL']
        }

    return pd.concat([DataFrame.from_dict(map_data(doc)) for doc in documents], ignore_index=True)


def _generate_index_from_coordinates(coordinates: List[Point]) -> dict:
    return {point.wikidata_uri: point
            for point in coordinates
            }

if __name__ == '__main__':
    convert_biofid_response_to_dataframe('../data/biofid-response-solidago-canadensis-in-germany-part-1.json')