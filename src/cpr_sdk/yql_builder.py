from string import Template
from vespa.querybuilder import QueryField, Query
import vespa.querybuilder as qb
from typing import Optional


from cpr_sdk.models.search import (
    Filters,
    SearchClassifiersProfileParameters,
    SearchConceptParameters,
    SearchParameters,
)


class YQLBuilder:
    """Used to assemble YQL queries"""

    yql_base = Template(
        """
        select * from sources $SOURCES
            where $WHERE_CLAUSE
        limit 0
        |
            $CONTINUATION
        all(
            group(family_import_id)
            output(count())
            max($LIMIT)
            $SORT
            each(
                output(count())
                max($MAX_HITS_PER_FAMILY)
                each(
                    output(
                        summary(search_summary)
                    )
                )
            )
        )
    """
    )

    def __init__(self, params: SearchParameters, sensitive: bool = False) -> None:
        self.params = params
        self.sensitive = sensitive

    def _escape_apostrophes(self, value: Optional[str]) -> str:
        """Escape a apostrophes for safe inclusion in a single-quoted YQL literal."""
        if value is None:
            return ""
        return value.replace("'", "\\'")

    def build_sources(self) -> str:
        """Creates the part of the query that determines which sources to search"""
        if self.params.documents_only:
            return "family_document"
        else:
            return "family_document, document_passage"

    def build_search_term(self) -> str:
        """Create the part of the query that matches a users search text"""
        if self.params.all_results:
            return "( true )"
        if self.params.exact_match:
            return """
                (
                    (family_name_not_stemmed contains({stem: false}@query_string)) or
                    (family_description_not_stemmed contains({stem: false}@query_string)) or
                    (text_block_not_stemmed contains ({stem: false}@query_string))
                )
            """
        elif self.sensitive:
            return """
                (
                    (userInput(@query_string)) 
                )
            """
        elif self.params.by_document_title:
            return """
                (
                    (document_title_index contains(@query_string))
                )
            """
        else:
            # if specified in the search parameters, add a threshold for the distance
            # between the query and the text_embedding
            distance_threshold_clause = (
                f', "distanceThreshold": {self.params.distance_threshold}'
                if self.params.distance_threshold is not None
                else ""
            )

            return f"""
                (
                    (userInput(@query_string)) 
                    or (
                        [{{\"targetNumHits\": 1000{distance_threshold_clause}}}]
                        nearestNeighbor(text_embedding,query_embedding)
                    )
                )
            """

    def build_metadata_filter(self) -> Optional[str]:
        """Create the part of the query that limits to specific metadata"""
        metadata_filters = []
        if self.params.metadata:
            for metadata in self.params.metadata:
                name_escaped = self._escape_apostrophes(metadata.name)
                value_escaped = self._escape_apostrophes(metadata.value)
                metadata_filters.append(
                    f"""
                    (
                        metadata contains sameElement(
                            name contains '{name_escaped}',
                            value contains '{value_escaped}'
                        )
                    )
                    """
                )
            return f"({' and '.join(metadata_filters)})"
        return None

    def build_concepts_filter(self) -> Optional[str]:
        """
        Create the part of the query that limits to specific concepts.

        e.g:
        - `concepts.name contains 'floods' and concepts.name contains 'environment'`
        - `concepts.parent_concept_ids_flat matches 'Q123' and concepts.name contains 'environment'`
        """
        if self.params.concept_filters:
            concepts_query = []
            for concept in self.params.concept_filters:
                if concept.name == "parent_concept_ids_flat":
                    concepts_query.append(
                        f"concepts.{concept.name} matches '{concept.value}'"
                    )
                else:
                    concepts_query.append(
                        f"concepts.{concept.name} contains '{concept.value}'"
                    )
            return f"({' and '.join(concepts_query)})"
        return None

    def build_corpus_type_name_filter(self) -> Optional[str]:
        """Create the part of the query that limits to specific corpora"""
        if self.params.corpus_type_names:
            corpora = ", ".join([f"'{c}'" for c in self.params.corpus_type_names])
            return f"(corpus_type_name in({corpora}))"

    def build_corpus_import_ids_filter(self) -> Optional[str]:
        """Create the part of the query that limits to specific corpora import id"""
        if self.params.corpus_import_ids:
            corpora = ", ".join([f"'{c}'" for c in self.params.corpus_import_ids])
            return f"(corpus_import_id in({corpora}))"

    def build_family_filter(self) -> Optional[str]:
        """Create the part of the query that limits to specific families"""
        if self.params.family_ids:
            families = ", ".join([f"'{f}'" for f in self.params.family_ids])
            return f"(family_import_id in({families}))"
        return None

    def build_document_filter(self) -> Optional[str]:
        """Create the part of the query that limits to specific documents"""
        if self.params.document_ids:
            documents = ", ".join([f"'{d}'" for d in self.params.document_ids])
            return f"(document_import_id in({documents}))"
        return None

    def _inclusive_filters(self, filters: Filters, field_name: str) -> Optional[str]:
        values = getattr(filters, field_name)
        query_filters = []
        for value in values:
            query_filters.append(f'({field_name} contains "{value}")')
        if query_filters:
            return f"({' or '.join(query_filters)})"

    def build_year_start_filter(self) -> Optional[str]:
        """Create the part of the query that filters on a year range"""
        if self.params.year_range:
            start, _ = self.params.year_range
            if start:
                return f"(family_publication_year >= {start})"
        return None

    def build_year_end_filter(self) -> Optional[str]:
        """Create the part of the query that filters on a year range"""
        if self.params.year_range:
            _, end = self.params.year_range
            if end:
                return f"(family_publication_year <= {end})"
        return None

    def build_concept_count_filter(self) -> Optional[str]:
        """Create the part of the query that filters on concept counts"""
        concept_count_filters_subqueries = []
        if self.params.concept_count_filters:
            for concept_count_filter in self.params.concept_count_filters:
                concept_count_filters_subqueries.append(
                    f"""
                    {"!" if concept_count_filter.negate else ""}
                    (
                        concept_counts contains sameElement(
                            {
                        (
                            f'key contains "{concept_count_filter.concept_id}", '
                            if concept_count_filter.concept_id is not None
                            else ""
                        )
                    }
                            value {concept_count_filter.operand.value} {
                        concept_count_filter.count
                    }
                        )
                    )
                    """
                )

            return f"({' and '.join(concept_count_filters_subqueries)})"
        return None

    def build_concept_v2_passage_filter(self) -> str | None:
        """
        Create the part of the query that filters passage spans by v2 concepts.

        Based on navigator-infra system tests, uses concepts_v2_flat matches pattern:
        - `spans contains sameElement(concepts_v2_flat matches 'y28e4s6n:kx7m3p9w')`
        - `spans contains sameElement(concepts_v2_flat matches 'y28e4s6n')`  # concept only
        """
        if not self.params.concept_v2_passage_filters:
            return None

        passage_filters: list[str] = []

        for filter_obj in self.params.concept_v2_passage_filters:
            match_patterns: list[str] = []

            # > Having a prefix using the ^ will be faster than not having one.
            match (
                filter_obj.concept_id,
                filter_obj.concept_wikibase_id,
                filter_obj.classifier_id,
            ):
                case (None, None, None):
                    raise ValueError("At least one constraint must be provided")
                case (None, None, classifier_id):
                    match_patterns.append(f"concepts_v2_flat matches '{classifier_id}'")
                case (None, concept_wikibase_id, None):
                    match_patterns.append(
                        f"concepts_v2_flat matches '{concept_wikibase_id}'"
                    )
                case (concept_id, None, None):
                    match_patterns.append(f"concepts_v2_flat matches '^{concept_id}'")

                case (concept_id, concept_wikibase_id, None):
                    match_patterns.append(
                        f"concepts_v2_flat matches '^{concept_id}:{concept_wikibase_id}'"
                    )
                case (concept_id, None, classifier_id):
                    match_patterns.append(
                        f"concepts_v2_flat matches '^{concept_id}:.*:{classifier_id}'"
                    )
                case (None, concept_wikibase_id, classifier_id):
                    match_patterns.append(
                        f"concepts_v2_flat matches '.*:{concept_wikibase_id}:{classifier_id}'"
                    )

                case (concept_id, concept_wikibase_id, classifier_id):
                    match_patterns.append(
                        f"concepts_v2_flat matches '^{concept_id}:{concept_wikibase_id}:{classifier_id}'"
                    )

            for pattern in match_patterns:
                document_filter = f"spans contains sameElement({pattern})"
                if filter_obj.negate:
                    document_filter = f"!({document_filter})"
                passage_filters.append(document_filter)

        if not passage_filters:
            return None

        return f"({' and '.join(passage_filters)})"

    def build_concept_v2_document_filter(self) -> str | None:
        """
        Create the part of the query that filters documents by v2 concept counts.

        Based on navigator-infra system tests:
        - `concepts_v2 contains sameElement(concept_id contains 'y28e4s6n')`
        - `concepts_v2 contains sameElement(concept_id contains 'y28e4s6n', classifier_id contains 'kx7m3p9w')`
        - `concepts_v2 contains sameElement(concept_wikibase_id contains 'Q100', count > 5)`
        """
        if not self.params.concept_v2_document_filters:
            return None

        document_filters: list[str] = []

        for filter_obj in self.params.concept_v2_document_filters:
            concept_conditions: list[str] = []

            if filter_obj.concept_id:
                concept_conditions.append(
                    f"concept_id contains '{filter_obj.concept_id}'"
                )
            if filter_obj.concept_wikibase_id:
                concept_conditions.append(
                    f"concept_wikibase_id contains '{filter_obj.concept_wikibase_id}'"
                )
            if filter_obj.classifier_id:
                concept_conditions.append(
                    f"classifier_id contains '{filter_obj.classifier_id}'"
                )

            if filter_obj.count is not None and filter_obj.operand is not None:
                concept_conditions.append(
                    f"count {filter_obj.operand.value} {filter_obj.count}"
                )

            if concept_conditions:
                conditions_str = ", ".join(concept_conditions)
                document_filter = f"concepts_v2 contains sameElement({conditions_str})"
                if filter_obj.negate:
                    document_filter = f"!({document_filter})"
                document_filters.append(document_filter)

        if not document_filters:
            return None

        return f"({' and '.join(document_filters)})"

    def build_where_clause(self) -> str:
        """Create the part of the query that adds filters"""
        filters = []
        filters.append(self.build_search_term())
        filters.append(self.build_family_filter())
        filters.append(self.build_document_filter())
        filters.append(self.build_corpus_type_name_filter())
        filters.append(self.build_corpus_import_ids_filter())
        filters.append(self.build_metadata_filter())
        filters.append(self.build_concepts_filter())
        if f := self.params.filters:
            filters.append(self._inclusive_filters(f, "family_geographies"))
            filters.append(self._inclusive_filters(f, "family_geography"))
            filters.append(self._inclusive_filters(f, "family_category"))
            filters.append(self._inclusive_filters(f, "document_languages"))
            filters.append(self._inclusive_filters(f, "family_source"))
        filters.append(self.build_year_start_filter())
        filters.append(self.build_year_end_filter())
        filters.append(self.build_concept_count_filter())
        filters.append(self.build_concept_v2_passage_filter())
        filters.append(self.build_concept_v2_document_filter())
        return " and ".join([f for f in filters if f])  # Remove empty

    def build_continuation(self) -> str:
        """Create the part of the query that adds continuation tokens"""
        if self.params.continuation_tokens:
            continuations = ", ".join(f"'{c}'" for c in self.params.continuation_tokens)
            return f"{{ 'continuations': [{continuations}] }}"
        else:
            return ""

    def build_limit(self) -> int:
        """Create the part of the query limiting the number of families returned"""
        return self.params.limit

    def build_sort(self) -> str:
        """Creates the part of the query used for sorting by different fields"""
        sort_by = self.params.vespa_sort_by
        sort_order = self.params.vespa_sort_order

        if not sort_by or not sort_order:
            return ""
        return f"order({sort_order}max({sort_by}))"

    def build_max_hits_per_family(self) -> int:
        """Create the part of the query limiting passages within a family returned"""
        return self.params.max_hits_per_family

    def to_str(self) -> str:
        """Assemble the yql from parts using the template"""
        yql = self.yql_base.substitute(
            SOURCES=self.build_sources(),
            WHERE_CLAUSE=self.build_where_clause(),
            CONTINUATION=self.build_continuation(),
            LIMIT=self.build_limit(),
            SORT=self.build_sort(),
            MAX_HITS_PER_FAMILY=self.build_max_hits_per_family(),
        )
        return " ".join(yql.split())


class ConceptYQLBuilder:
    """Used to assemble YQL queries for concepts"""

    @staticmethod
    def build(parameters: SearchConceptParameters) -> str:
        """Build a query for concepts"""
        q: Query = qb.select("*").from_(  # pyright: ignore[reportGeneralTypeIssues]
            "concept"
        )

        # Track if we have any filters
        has_filters = False
        if any(
            [
                parameters.id,
                parameters.wikibase_id,
                parameters.wikibase_revision,
                parameters.preferred_label,
            ]
        ):
            if parameters.id:
                q = q.where(QueryField("id").contains(parameters.id))
                has_filters = True

            if parameters.wikibase_id:
                q = q.where(QueryField("wikibase_id").contains(parameters.wikibase_id))
                has_filters = True

            if parameters.wikibase_revision:
                q = q.where(
                    QueryField("wikibase_revision").contains(
                        parameters.wikibase_revision
                    )
                )
                has_filters = True

            if parameters.preferred_label:
                q = q.where(
                    QueryField("preferred_label").contains(parameters.preferred_label)
                )
                has_filters = True
        else:
            # If no filters provided, add 'where true' as fallback
            if not has_filters:
                q = q.where(True)

        q = q.set_limit(parameters.limit)

        # Convert to string
        yql_str = str(q)

        # Add continuation tokens if present (following the same pattern as YQLBuilder for families)
        if parameters.continuation_tokens:
            continuations = ", ".join(f"'{c}'" for c in parameters.continuation_tokens)
            continuation_clause = f" | {{ 'continuations': [{continuations}] }}"
            yql_str += continuation_clause

        return yql_str


class ClassifiersProfileYQLBuilder:
    """Used to assemble YQL queries for classifiers profiles"""

    @staticmethod
    def build(parameters: SearchClassifiersProfileParameters) -> str:
        """Build a query for classifiers profiles"""
        q: Query = qb.select("*").from_(  # pyright: ignore[reportGeneralTypeIssues]
            "classifiers_profile"
        )

        # Track if we have any filters
        has_filters = False
        if any([parameters.id, parameters.name]):
            if parameters.id:
                q = q.where(QueryField("id").contains(parameters.id))
                has_filters = True

            if parameters.name:
                q = q.where(QueryField("name").contains(parameters.name))
                has_filters = True
        else:
            # If no filters provided, add 'where true' as fallback
            if not has_filters:
                q = q.where(True)

        q = q.set_limit(parameters.limit)

        # Convert to string
        yql_str = str(q)

        return yql_str
