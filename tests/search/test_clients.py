from cpr_sdk.search.clients import client, Session, Concept, AuthMethods


def test_client():
    assert isinstance(
        client(
            service="concept",
            instance_url="localhost:8080",
            auth=AuthMethods.CloudToken("test"),
        ),
        Concept,
    )


def test_session():
    session = Session(instance_url="localhost:8080", auth=AuthMethods.Local())

    assert isinstance(
        session.client(service="concept"),
        Concept,
    )


def test_concept_get():
    pass


def test_concept_query():
    pass
