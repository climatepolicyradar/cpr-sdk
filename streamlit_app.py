"""CPR Concept Explorer - Streamlit app to explore concept instance filtering and model profiles."""

import streamlit as st
from typing import Dict, List, Optional, Tuple
from utils.data_loader import (
    load_test_passage,
    load_family_document,
    load_model_profiles, 
    get_available_concepts,
    get_available_concepts_from_family,
    get_family_concept_counts,
    get_all_concept_spans,
    get_concept_statistics,
    get_concepts_from_vespa
)
from utils.visualizer import create_highlighted_passage


def setup_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="CPR Concept Explorer",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("CPR Concept Explorer")
    st.markdown("*Explore concept instance filtering and model profile APIs*")


def render_sidebar(available_concepts: Dict[str, List[str]], model_profiles: Dict) -> Tuple[Dict[str, str], str]:
    """Render sidebar controls and return selected concept configurations."""
    st.sidebar.header("Controls")
    
    # Model Profile Selection
    st.sidebar.subheader("Model Profiles")
    selected_profile_name = None
    selected_profile = None
    
    if model_profiles:
        profile_names = ["No Filter (All Available)"] + list(model_profiles.keys())
        selected_profile_name = st.sidebar.selectbox(
            "Model Profile Filter", 
            options=profile_names,
            index=0,  # Default to "No Filter"
            help="Choose which model profile to use for filtering concepts and versions. 'No Filter' shows all concepts/versions found in the passage."
        )
        
        if selected_profile_name != "No Filter (All Available)":
            selected_profile = model_profiles[selected_profile_name]
            st.sidebar.write(f"Using: {selected_profile.name or selected_profile.id}")
            st.sidebar.write(f"{len(selected_profile.concepts_versions)} concepts defined")
            
            st.sidebar.write("**Profile Details:**")
            for concept_id, concept_version in selected_profile.concepts_versions.items():
                st.sidebar.write(f"• {concept_id.upper()}: {concept_version.canonical_id} (rev: {concept_version.wikibase_revision_id})")
        else:
            st.sidebar.write("No filtering applied - showing all available concepts and versions")
    
    # Show concept details from Vespa
    if available_concepts:
        st.sidebar.write("**Concept Details:**")
        concept_ids = list(available_concepts.keys())
        concept_details = get_concepts_from_vespa(concept_ids)
        
        if concept_details:
            for concept_key, concept_data in concept_details.items():
                concept_id = concept_data.get("id", "").upper()
                preferred_label = concept_data.get("preferred_label", "")
                revision = concept_data.get("revision", "")
                
                label_text = f"{concept_id}: {preferred_label}" if preferred_label else concept_id
                if revision:
                    label_text += f" (rev: {revision})"
                
                st.sidebar.write(f"• {label_text}")
                
                # Show description if available
                if concept_data.get("description"):
                    st.sidebar.caption(f"  {concept_data['description']}")
        else:
            st.sidebar.write("No concept details found in Vespa")
    
    # Filter available concepts based on selected profile
    if selected_profile:
        # Filter to only concepts defined in the selected profile
        profile_concept_ids = set(selected_profile.concepts_versions.keys())
        filtered_concepts = {}
        
        for concept_id, available_versions in available_concepts.items():
            if concept_id in profile_concept_ids:
                profile_concept_version = selected_profile.concepts_versions[concept_id]
                profile_version = profile_concept_version.canonical_id
                
                # Check if the profile's specified version exists in the passage
                if profile_version in available_versions:
                    # Only show the specific version from the profile
                    filtered_concepts[concept_id] = [profile_version]
                else:
                    # Profile version not found in passage - show all available versions
                    # but note the discrepancy
                    filtered_concepts[concept_id] = available_versions
        
        # Show filtering results
        excluded_concepts = set(available_concepts.keys()) - profile_concept_ids
        if excluded_concepts:
            with st.sidebar.expander("Excluded Concepts"):
                for concept_id in sorted(excluded_concepts):
                    st.write(f"• {concept_id.upper()} (not in profile)")
    else:
        # No filtering - show all available concepts and versions
        filtered_concepts = available_concepts.copy()
    
    # Concept Controls
    st.sidebar.subheader("Concept Selection")
    
    # Show filtering status
    total_available = len(available_concepts)
    total_filtered = len(filtered_concepts)
    
    if selected_profile:
        st.sidebar.caption(f"Showing {total_filtered}/{total_available} concepts from {selected_profile_name} profile")
    else:
        st.sidebar.caption(f"Showing all {total_available} available concepts")
    
    selected_concepts = {}
    
    if filtered_concepts:
        for concept_id, model_versions in filtered_concepts.items():
            # Concept toggle with additional info
            concept_label = concept_id.upper()
            if selected_profile and concept_id in selected_profile.concepts_versions:
                profile_concept_version = selected_profile.concepts_versions[concept_id]
                profile_version = profile_concept_version.canonical_id
                if profile_version not in model_versions:
                    concept_label += " (version mismatch)"
            
            concept_enabled = st.sidebar.checkbox(
                concept_label, 
                value=True,
                key=f"concept_{concept_id}"
            )
            
            if concept_enabled and model_versions:
                if len(model_versions) == 1:
                    # Only one version available, use it directly
                    selected_concepts[concept_id] = model_versions[0]
                    version_info = model_versions[0]
                    if selected_profile and concept_id in selected_profile.concepts_versions:
                        profile_concept_version = selected_profile.concepts_versions[concept_id]
                        profile_version = profile_concept_version.canonical_id
                        if model_versions[0] != profile_version:
                            version_info += f" (profile wants {profile_version})"
                    st.sidebar.caption(f"Using: {version_info}")
                else:
                    # Multiple versions available, show selector
                    version_options = ["All versions"] + model_versions
                    
                    # Pre-select profile version if available
                    default_index = 0
                    if selected_profile and concept_id in selected_profile.concepts_versions:
                        profile_concept_version = selected_profile.concepts_versions[concept_id]
                        profile_version = profile_concept_version.canonical_id
                        if profile_version in model_versions:
                            default_index = model_versions.index(profile_version) + 1
                    
                    selected_version = st.sidebar.selectbox(
                        f"Version for {concept_id.upper()}",
                        options=version_options,
                        index=default_index,
                        key=f"version_{concept_id}",
                        help=f"Available: {', '.join(model_versions)}"
                    )
                    
                    if selected_version != "All versions":
                        selected_concepts[concept_id] = selected_version
                    else:
                        # For "All versions", add all model versions
                        for version in model_versions:
                            selected_concepts[f"{concept_id}_{version}"] = version
    else:
        if selected_profile:
            st.sidebar.write(f"No concepts from {selected_profile_name} profile found in this passage")
            st.sidebar.write("Try selecting 'No Filter' to see all available concepts")
        else:
            st.sidebar.write("No concepts found in passage")
    
    return selected_concepts, selected_profile_name


def render_main_content(passage, selected_concepts: Dict[str, str], model_profiles: Dict, selected_profile_name: str = None):
    """Render the main content area with passage and statistics."""
    if not passage:
        st.error("Failed to load test passage")
        st.write("Make sure Vespa is running at http://localhost:8080")
        return
    
    # Show current filtering status
    if selected_profile_name and selected_profile_name != "No Filter (All Available)":
        profile = model_profiles.get(selected_profile_name)
        if profile:
            st.write(f"Filtering by model profile: {selected_profile_name} ({len(profile.concepts_versions)} concepts defined)")
        else:
            st.write(f"Filtering by model profile: {selected_profile_name}")
    else:
        st.write("No filtering applied - showing all available concepts and versions")
    
    # Statistics Panel
    st.subheader("Statistics")
    stats = get_concept_statistics(passage, selected_concepts)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Selected Concepts", stats["total_concepts"])
    with col2:
        st.metric("Total Spans", stats["total_spans"])
    with col3:
        st.metric("Characters Covered", stats["covered_characters"])
    with col4:
        st.metric("Coverage %", f"{stats['coverage_percentage']:.1f}%")
    
    # Passage Display
    st.subheader("Passage Text")
    
    if selected_concepts:
        # Get spans for selected concepts
        concept_spans = get_all_concept_spans(passage, selected_concepts)
        
        if concept_spans:
            # Create highlighted text and legend
            highlighted_text, legend_html = create_highlighted_passage(passage.text_block, concept_spans)
            
            # Display legend
            st.markdown(legend_html, unsafe_allow_html=True)
            
            # Display highlighted passage
            st.markdown(highlighted_text, unsafe_allow_html=True)
        else:
            st.write("No spans found for selected concepts and versions")
            st.text_area("Raw passage text", passage.text_block, height=400, disabled=True)
    else:
        st.write("Select concepts from the sidebar to see highlighting")
        st.text_area("Raw passage text", passage.text_block, height=400, disabled=True)
    
    # Passage Metadata
    with st.expander("Passage Metadata"):
        st.write(f"Document ID: {passage.document_import_id}")
        st.write(f"Family: {passage.family_name}")
        st.write(f"Text Block ID: {passage.text_block_id}")
        st.write(f"Text Block Type: {passage.text_block_type}")
        if passage.text_block_page:
            st.write(f"Page: {passage.text_block_page}")
        st.write(f"Character Count: {len(passage.text_block)}")


def render_family_content(family, selected_concepts: Dict[str, str], model_profiles: Dict, selected_profile_name: str = None):
    """Render content for family documents with concept counts."""
    if not family:
        st.error("Unable to load family document")
        st.write("Please ensure Vespa is running at http://localhost:8080")
        return
    
    # Show current filtering status
    if selected_profile_name and selected_profile_name != "No Filter (All Available)":
        profile = model_profiles.get(selected_profile_name)
        if profile:
            st.write(f"Filtering by model profile: {selected_profile_name} ({len(profile.concepts_versions)} concepts defined)")
        else:
            st.write(f"Filtering by model profile: {selected_profile_name}")
    else:
        st.write("No filtering applied - showing all available concepts and versions")
    
    # Statistics Panel for family
    st.subheader("Statistics")
    
    total_concepts = len(selected_concepts)
    total_count = 0
    
    for concept_id, model_version in selected_concepts.items():
        if "_" in concept_id:
            concept_id = concept_id.split("_")[0]
        counts = get_family_concept_counts(family, concept_id, model_version)
        total_count += sum(counts.values())
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Selected Concepts", total_concepts)
    with col2:
        st.metric("Total Count", total_count)
    
    # Concept Counts Display
    st.subheader("Concept Counts by Model Version")
    
    if selected_concepts:
        for concept_id, model_version in selected_concepts.items():
            if "_" in concept_id:
                concept_id = concept_id.split("_")[0]
            
            counts = get_family_concept_counts(family, concept_id, model_version)
            if counts:
                st.write(f"**{concept_id.upper()}** ({model_version}): {counts[model_version]} instances")
    else:
        st.write("Select concepts from the sidebar to see counts")
    
    # Family Metadata
    with st.expander("Family Metadata"):
        if hasattr(family, 'name'):
            st.write(f"Family Name: {family.name}")
        if hasattr(family, 'document_import_id'):
            st.write(f"Document Import ID: {family.document_import_id}")
        elif hasattr(family, 'family_import_id'):
            st.write(f"Family Import ID: {family.family_import_id}")
        if hasattr(family, 'total_passages'):
            st.write(f"Total Passages: {family.total_passages}")
        if hasattr(family, 'hits') and family.hits:
            st.write(f"Number of Hits: {len(family.hits)}")
        
        # Debug: show available attributes
        st.write("Available attributes:", [attr for attr in dir(family) if not attr.startswith('_')])


def main():
    """Main application entry point."""
    setup_page()
    
    # Document type selector
    doc_type = st.selectbox(
        "Document Type",
        options=["Passage (with spans)", "Family Document (with counts)"],
        index=0,
        help="Choose between passage view (shows highlighted text spans) or family document view (shows concept counts)"
    )
    
    # Load data based on document type
    model_profiles = load_model_profiles()
    
    if doc_type == "Passage (with spans)":
        with st.spinner("Loading passage data from Vespa..."):
            passage = load_test_passage("CCLW.document.i00000005.n0000")
        
        if passage:
            available_concepts = get_available_concepts(passage)
            
            # Render sidebar and get selected concepts + profile info
            selected_concepts, selected_profile_name = render_sidebar(available_concepts, model_profiles)
            
            render_main_content(passage, selected_concepts, model_profiles, selected_profile_name)
        else:
            st.error("Unable to load test passage")
            st.write("Please ensure Vespa is running at http://localhost:8080")
    
    else:  # Family Document
        with st.spinner("Loading family document from Vespa..."):
            family = load_family_document("CCLW.document.i00000005.n0000")
        
        if family:
            available_concepts = get_available_concepts_from_family(family)
            
            # Render sidebar and get selected concepts + profile info
            selected_concepts, selected_profile_name = render_sidebar(available_concepts, model_profiles)
            
            render_family_content(family, selected_concepts, model_profiles, selected_profile_name)
        else:
            st.error("Unable to load family document")
            st.write("Please ensure Vespa is running at http://localhost:8080")


if __name__ == "__main__":
    main()
