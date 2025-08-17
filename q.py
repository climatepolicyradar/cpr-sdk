from src.cpr_sdk.search_adaptors import VespaSearchAdapter
from src.cpr_sdk.models.search import SearchParameters, ConceptInstanceFilter
from src.cpr_sdk.models.model_profile import VespaModelProfileAdapter

if __name__ == "__main__":
    adaptor = VespaSearchAdapter(
        instance_url="http://localhost:8080", skip_cert_usage=True
    )

    # Basic document search
    print("=== Basic Document Search ===")
    request = SearchParameters(
        # query_string="Climate Change Adaptation and Low Emissions Growth Strategy by 2035",
        document_ids=["CCLW.document.i00000005.n0000"],
    )
    response = adaptor.search(request)
    print(response)
    print()

    # Example 1: Filter by concept ID only (any model version)
    print("=== Filter by Concept ID (Q880) - Any Model Version ===")
    request = SearchParameters(
        query_string="climate",
        concept_instance_filters=[ConceptInstanceFilter(concept_id="Q880")],
    )
    response = adaptor.search(request)
    print(f"Found {response.total_hits} hits for concept Q880")

    # Debug: Show what model versions are available for Q880
    if response.families:
        for family in response.families:
            for hit in family.hits:
                if hasattr(hit, "concepts_instances") and hit.concepts_instances:
                    if "q880" in hit.concepts_instances:
                        instance = hit.concepts_instances["q880"]
                        print(f"Q880 found with model_id_all: {instance.model_id_all}")
                        if hasattr(instance, "spans_by_model_version"):
                            print(
                                f"Available model versions: {list(instance.spans_by_model_version.keys())}"
                            )
                        elif hasattr(instance, "counts_by_model_version"):
                            print(
                                f"Available model versions: {list(instance.counts_by_model_version.keys())}"
                            )
                        break
    print()

    # Example 2: Filter by concept ID and specific model version
    print("=== Filter by Concept ID (Q880) + Specific Model Version (kx7m3p9w) ===")
    request = SearchParameters(
        query_string="climate",
        concept_instance_filters=[
            ConceptInstanceFilter(concept_id="Q880", model_version="kx7m3p9w")
        ],
    )

    # Debug: Show the generated YQL query
    from src.cpr_sdk.yql_builder import YQLBuilder

    yql_builder = YQLBuilder(request)
    print(f"Generated YQL: {yql_builder.to_str()}")

    response = adaptor.search(request)
    print(
        f"Found {response.total_hits} hits for concept Q880 with model version kx7m3p9w"
    )
    print()

    # Example 3: Filter by multiple concepts
    print("=== Filter by Multiple Concepts ===")
    request = SearchParameters(
        query_string="climate",
        concept_instance_filters=[
            ConceptInstanceFilter(concept_id="Q880"),  # Air pollution (any version)
            ConceptInstanceFilter(
                concept_id="Q730", model_version="w3kb7x1s"
            ),  # Specific version
        ],
    )
    response = adaptor.search(request)
    print(f"Found {response.total_hits} hits for multiple concept filters")
    print()

    # Example 4: Combine with other filters
    print("=== Combined Concept Instance + Traditional Filters ===")
    request = SearchParameters(
        query_string="adaptation",
        concept_instance_filters=[ConceptInstanceFilter(concept_id="Q880")],
        year_range=(2020, 2024),
        limit=5,
    )
    response = adaptor.search(request)
    print(f"Found {response.total_hits} hits for concept Q880 published 2020-2024")
    if response.families:
        for family in response.families[:2]:  # Show first 2 families
            for hit in family.hits:
                if hasattr(hit, "concepts_instances") and hit.concepts_instances:
                    print(f"  - Document: {hit.family_name}")
                    print(
                        f"    Concept instances: {list(hit.concepts_instances.keys())}"
                    )
                    print(f"    Concepts versions: {hit.concepts_versions}")
                    break

    # Example Filter by concept ID and specific model version that doesn't exist
    print("=== Filter by Concept ID (Q880) + Unknown Specific Model Version ===")
    request = SearchParameters(
        query_string="climate",
        concept_instance_filters=[
            ConceptInstanceFilter(concept_id="Q880", model_version="x0x1x2x3")
        ],
    )
    response = adaptor.search(request)
    print(
        f"Found {response.total_hits} hits for concept Q880 with unknown model version x0x1x2x3"
    )
    print()

    # Example 5: Model Profile Operations
    print("=== Model Profile Operations ===")
    profile_adaptor = VespaModelProfileAdapter(
        instance_url="http://localhost:8080", skip_cert_usage=True
    )

    # Get all model profiles
    print("Getting all model profiles...")
    try:
        all_profiles = profile_adaptor.get_all_profiles()
        print(f"Found {len(all_profiles)} model profiles:")
    except Exception as e:
        print(f"Error fetching model profiles: {e}")
        all_profiles = []
    for profile in all_profiles:
        print(f"  - {profile.id} ({profile.name}): {len(profile.concepts_versions)} concepts")
        # Show a few concept versions as examples
        concept_examples = list(profile.concepts_versions.items())[:3]
        for concept_id, version in concept_examples:
            print(f"    - {concept_id}: {version}")
        if len(profile.concepts_versions) > 3:
            print(f"    - ... and {len(profile.concepts_versions) - 3} more")
    print()

    # Get specific model profile
    print("Getting specific model profile: 'primaries'")
    primaries_profile = profile_adaptor.get_profile_by_id("primaries")
    if primaries_profile:
        print(f"Found primaries profile with {len(primaries_profile.concepts_versions)} concepts:")
        for concept_id, version in primaries_profile.concepts_versions.items():
            print(f"  - {concept_id}: {version}")
    else:
        print("Primaries profile not found")
    print()

    # Get non-existent profile
    print("Getting non-existent model profile: 'unknown'")
    unknown_profile = profile_adaptor.get_profile_by_id("unknown")
    if unknown_profile:
        print(f"Found unknown profile: {unknown_profile.id}")
    else:
        print("Unknown profile not found (as expected)")
    print()
