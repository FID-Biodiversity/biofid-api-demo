import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

import itertools
from bs4 import BeautifulSoup as XmlSoup

from .logger import setup_logging
from .wikidata import get_coordinates_for_wikidata_uris

UTF8_STRING = 'utf-8'
XML_PARSER = 'lxml'
log = setup_logging(logging.DEBUG)

CLASS_STRING = 'class'
SEARCH_TERM_STRING = 'search-term'
TAXON_ANNOTATION_CLASS_STRINGS = ['taxon', 'plant_flora', 'animal_flora']


@dataclass
class Page:
    label: str
    url: str
    annotated_text_snippets: List[str]
    parent_document: 'Document'


@dataclass
class Document:
    authors: List[str]
    journal_name: str
    title: str
    url: str
    publication_year: Optional[int]
    pages: List[Page] = field(default_factory=list)


@dataclass
class Taxon:
    label: str
    biofid_uri: str
    wikidata_uri: str


@dataclass
class Location:
    label: str
    wikidata_uri: str


@dataclass
class TaxonLocationData:
    taxon: Taxon
    location: Location
    source_page: Page = None
    extraction_strategy: str = None


class BiofidSearchResponseProcessing:
    def __init__(self, semantic_search_data: dict):
        self.raw_data = semantic_search_data
        self.documents = []

        self._extract_data_to_documents(semantic_search_data)

    def extract_taxon_location_relations(self, strategy_term: str = 'page') -> List[TaxonLocationData]:
        extraction_strategy = {
            'page': SamePageCooccurrence()
        }

        strategy = extraction_strategy[strategy_term]

        return list(itertools.chain.from_iterable(extract_taxon_location_data_from_document(document, strategy)
                                                  for document in self.documents))

    def _extract_data_to_documents(self, data: dict):
        search_data = data['data']
        self.documents = [create_document(document_metadata) for document_metadata in search_data]


def generate_dataframe_from_json_file(json_file_path: str, tsv_output_file_name: str):
    from scripts.commons import read_json_file_content
    from scripts.conversion import convert_taxon_location_data_to_dataframe
    semantic_search_data = read_json_file_content(json_file_path)
    data_processing = BiofidSearchResponseProcessing(semantic_search_data)
    taxon_location_relations = data_processing.extract_taxon_location_relations()

    location_uris = [relationship.location.wikidata_uri
                     for relationship in taxon_location_relations]
    coordinates = get_coordinates_for_wikidata_uris(location_uris)

    df = convert_taxon_location_data_to_dataframe(taxon_location_relations, coordinates)
    df.to_csv(tsv_output_file_name, sep='\t')

    return df


def create_document(document_metadata: dict) -> Document:
    authors = document_metadata.get('Authors', '').split('|')
    journal = document_metadata.get('Journal')
    publication_year = document_metadata.get('PublicationYear')
    title = document_metadata.get('Title')
    url = document_metadata.get('URL')

    document = Document(authors, journal, title, url, publication_year)
    document.pages = [create_page(page_metadata, document)
                      for page_metadata in document_metadata.get('TextExtracts')]

    return document


def create_page(page_metadata: dict, document: Document) -> Page:
    label = page_metadata.get('Label')
    url = page_metadata.get('URL')
    text_snippets = page_metadata.get('TextPreview')

    return Page(label, url, text_snippets, document)


def extract_taxon_location_data_from_document(document: Document, extraction_strategy) -> List[TaxonLocationData]:
    return list(itertools.chain.from_iterable(extraction_strategy.process(page) for page in document.pages))


class SamePageCooccurrence:
    def process(self, page: Page) -> List[TaxonLocationData]:
        merged_page_snippet_text = ' '.join(page.annotated_text_snippets)
        merged_page_snippet_text = f'<root>{merged_page_snippet_text}</root>'
        xml_data = XmlSoup(merged_page_snippet_text, XML_PARSER)
        search_terms = xml_data.find_all('em')
        taxon_search_terms = extract_taxa_from_search_terms(search_terms)
        location_search_terms = extract_locations_from_search_terms(search_terms)

        relationships = create_taxon_location_relations(taxon_search_terms, location_search_terms)

        for relationship in relationships:
            relationship.extraction_strategy = 'SamePageOccurrence'
            relationship.source_page = page

        return relationships


def create_taxon_location_relations(taxon_search_terms, location_search_terms) -> List[TaxonLocationData]:
    if not taxon_search_terms or not location_search_terms:
        return []

    return [compile_relationship(taxon, location) for taxon in taxon_search_terms for location in location_search_terms]


def compile_relationship(taxon, location) -> TaxonLocationData:
    taxon_label, taxon_wikidata_uri, taxon_biofid_uri = get_data_from(taxon)
    taxon_entity = Taxon(taxon_label, taxon_biofid_uri, taxon_wikidata_uri)

    location_label, location_wikidata_uri, _ = get_data_from(location)
    location_entity = Location(location_label, location_wikidata_uri)

    return TaxonLocationData(taxon_entity, location_entity)


def get_data_from(entity):
    """ Returns a tuple of label, Wikidata URI, and BIOfid URI. """
    label = entity.text
    biofid_uri = entity.get('biofid-uri', False) or entity.get('biofid-uri-0')
    biofid_uri = swap_biofid_uri_style_to_new(biofid_uri) if biofid_uri is not None else biofid_uri
    wikidata_uri = entity.get('wikidata')

    return label, wikidata_uri, biofid_uri


def extract_taxa_from_search_terms(search_terms) -> list:
    def is_taxon(term_classes):
        for taxon_class_name in TAXON_ANNOTATION_CLASS_STRINGS:
            if taxon_class_name in term_classes:
                return True
        return False

    return list(filter(lambda x: is_taxon(x.attrs.get(CLASS_STRING, [])), search_terms))


def extract_locations_from_search_terms(search_terms) -> list:
    return list(filter(lambda x: 'location_place' in x.attrs.get(CLASS_STRING, []), search_terms))


def swap_biofid_uri_style_to_new(biofid_uri: str) -> Optional[str]:
    regex_old_uri_styles = [re.search(r'bio-ontologies/(?P<taxon>[A-Z][a-z]+)#GBIF_(?P<id>[0-9]+)$', uri)
                                    for uri in biofid_uri.split()]

    for uri_match in regex_old_uri_styles:
        if uri_match is None:
            continue

        uri_id_number = uri_match.group('id')
        taxon_name = uri_match.group('taxon')

        return f'https://www.biofid.de/bio-ontologies/{taxon_name}/gbif/{uri_id_number}'
    else:
        return biofid_uri


def generate_marker_text(df_row) -> str:
    taxon_text = wrap_text_with_link(df_row['taxon_label'], df_row['taxon_biofid_uri'])
    location_text = wrap_text_with_link(df_row['location_label'], df_row['location_wikidata_uri'])
    source_text = wrap_text_with_link('Source', df_row['page_url'])
    year = df_row['document_publication_year']

    return f'<p>Found hint for <b>{taxon_text}</b> in <b>{location_text}</b> in {year}. <br><br><b>{source_text}</b></p>'


def wrap_text_with_link(text: str, link: str) -> str:
    return f'<a href="{link}">{text}</a>'

if __name__ == '__main__':
    generate_dataframe_from_json_file('/home/apachzelt/Downloads/Taxus-baccata-in-Deutschland.json', 'foo')

