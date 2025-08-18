"""Data loading utilities for CPR SDK integration."""

import sys
import os
from typing import Dict, List, Optional, Tuple
import streamlit as st

# Add the src directory to Python path to import CPR SDK
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from cpr_sdk.search_adaptors import VespaSearchAdapter
from cpr_sdk.models.search import SearchParameters, Passage
from cpr_sdk.models.model_profile import VespaModelProfileAdapter, ModelProfile


@st.cache_resource
def get_search_adapter(vespa_url: str = "http://localhost:8080") -> VespaSearchAdapter:
    """Get cached VespaSearchAdapter instance."""
    return VespaSearchAdapter(instance_url=vespa_url, skip_cert_usage=True)


@st.cache_resource
def get_model_profile_adapter(vespa_url: str = "http://localhost:8080") -> VespaModelProfileAdapter:
    """Get cached VespaModelProfileAdapter instance."""
    return VespaModelProfileAdapter(instance_url=vespa_url, skip_cert_usage=True)


@st.cache_resource
def load_test_passage(document_id: str = "CCLW.document.i00000005.n0000") -> Optional[Passage]:
    """Load the test passage from Vespa."""
    try:
        adapter = get_search_adapter()
        request = SearchParameters(document_ids=[document_id])
        response = adapter.search(request)
        
        if response.families:
            for family in response.families:
                for hit in family.hits:
                    if hasattr(hit, 'text_block'):  # It's a passage
                        return hit
        
        # If no passage found, try to get any passage from the document
        # This helps debug when specific passage ID doesn't exist
        return None
    except ConnectionError:
        st.error("🔌 Cannot connect to Vespa. Make sure it's running at http://localhost:8080")
        return None
    except Exception as e:
        st.error(f"❌ Error loading passage: {e}")
        return None


@st.cache_resource  
def load_family_document(document_id: str = "CCLW.document.i00000005.n0000"):
    """Load a family document from Vespa that shows counts by model versions."""
    try:
        adapter = get_search_adapter()
        request = SearchParameters(document_ids=[document_id])
        response = adapter.search(request)
        
        if response.families:
            for family in response.families:
                # Return the family object itself, which has concepts_instances with counts
                if hasattr(family, 'concepts_instances') and family.concepts_instances:
                    return family
        
        # If no family found with concepts_instances, return the first family
        if response.families:
            return response.families[0]
        
        return None
    except ConnectionError:
        st.error("🔌 Cannot connect to Vespa. Make sure it's running at http://localhost:8080")
        return None
    except Exception as e:
        st.error(f"Error loading family document: {e}")
        return None


@st.cache_resource
def load_model_profiles() -> Dict[str, ModelProfile]:
    """Load all model profiles from Vespa."""
    try:
        adapter = get_model_profile_adapter()
        profiles = adapter.get_all_profiles()
        return {profile.id: profile for profile in profiles}
    except ConnectionError:
        st.warning("🔌 Cannot connect to Vespa for model profiles")
        return {}
    except Exception as e:
        st.warning(f"⚠️ Could not load model profiles: {e}")
        return {}


def get_available_concepts(passage: Passage) -> Dict[str, List[str]]:
    """Extract available concepts and their model versions from a passage."""
    concepts = {}
    if passage and passage.concepts_instances:
        for concept_id, instance in passage.concepts_instances.items():
            if hasattr(instance, 'spans_by_model_version'):
                concepts[concept_id] = list(instance.spans_by_model_version.keys())
            else:
                # Fallback to model_id_all if spans_by_model_version not available
                concepts[concept_id] = instance.model_id_all.split(',') if instance.model_id_all else []
    return concepts


def get_available_concepts_from_family(family) -> Dict[str, List[str]]:
    """Extract available concepts and their model versions from a family document."""
    concepts = {}
    if family and hasattr(family, 'concepts_instances') and family.concepts_instances:
        for concept_id, instance in family.concepts_instances.items():
            if hasattr(instance, 'counts_by_model_version') and instance.counts_by_model_version:
                concepts[concept_id] = list(instance.counts_by_model_version.keys())
    return concepts


def get_family_concept_counts(family, concept_id: str, model_version: str = None) -> Dict[str, int]:
    """Get counts for a specific concept and optionally model version from family document."""
    if not family or not hasattr(family, 'concepts_instances') or not family.concepts_instances:
        return {}
    
    instance = family.concepts_instances.get(concept_id.lower())
    if not instance or not hasattr(instance, 'counts_by_model_version'):
        return {}
    
    if model_version:
        # Return count for specific model version
        count = instance.counts_by_model_version.get(model_version, 0)
        return {model_version: count}
    else:
        # Return all counts by model version
        return instance.counts_by_model_version


def get_concept_spans(passage: Passage, concept_id: str, model_version: str) -> List[Tuple[int, int]]:
    """Get spans for a specific concept and model version."""
    if not passage or not passage.concepts_instances:
        return []
    
    instance = passage.concepts_instances.get(concept_id.lower())
    if not instance:
        return []
    
    if hasattr(instance, 'spans_by_model_version'):
        spans = instance.spans_by_model_version.get(model_version, [])
        return [(span.start, span.end) for span in spans]
    
    return []


def get_all_concept_spans(passage: Passage, selected_concepts: Dict[str, str]) -> Dict[str, List[Tuple[int, int]]]:
    """Get spans for all selected concepts and their model versions."""
    all_spans = {}
    for key, model_version in selected_concepts.items():
        # Handle both formats: "concept_id" and "concept_id_version"
        if "_" in key and key.count("_") > 1:  # Format: concept_id_version
            concept_id = key.split("_")[0]
        else:  # Format: concept_id
            concept_id = key
        
        spans = get_concept_spans(passage, concept_id, model_version)
        if spans:
            all_spans[f"{concept_id}_{model_version}"] = spans
    return all_spans


def get_concept_statistics(passage: Passage, selected_concepts: Dict[str, str]) -> Dict[str, int]:
    """Get statistics for selected concepts."""
    # Count unique concepts (handle both single version and multi-version selections)
    unique_concepts = set()
    for key in selected_concepts.keys():
        if "_" in key and key.count("_") > 1:  # Format: concept_id_version
            concept_id = key.split("_")[0]
        else:  # Format: concept_id
            concept_id = key
        unique_concepts.add(concept_id)
    
    stats = {
        "total_concepts": len(unique_concepts),
        "total_spans": 0,
        "covered_characters": 0
    }
    
    all_spans = get_all_concept_spans(passage, selected_concepts)
    for spans in all_spans.values():
        stats["total_spans"] += len(spans)
        for start, end in spans:
            stats["covered_characters"] += end - start
    
    if passage and passage.text_block:
        stats["total_characters"] = len(passage.text_block)
        stats["coverage_percentage"] = (stats["covered_characters"] / stats["total_characters"]) * 100
    else:
        stats["total_characters"] = 0
        stats["coverage_percentage"] = 0
    
    return stats