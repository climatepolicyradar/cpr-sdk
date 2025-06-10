import pytest

from cpr_sdk.config import VESPA_URL
from cpr_sdk.search_intention_testing.models import PassagesTestCase
from cpr_sdk.search_intention_testing.executors import do_test_passage_thresholds

test_cases = [
    PassagesTestCase(
        document_id="CCLW.legislative.9630.4040",
        description="Energy Efficiency Act 2016",
        search_terms="energy efficiency",
        expected_passages=[
            '"Minimum Energy Performance Standards and labelling (MEPSL) product" is an electrical appliance or a product that affects the amount of energy used by another product and is listed in Schedule 1A of the Regulations with the standards applicable to it;',
            "(b) the product has an energy label that complies with the energy performance standards and method of testing provide under Schedule 1A for that product;",
        ],
        forbidden_passages=[
            "'product class\" means a category of electrical appliances, grouped as class based on the functions they perform, the materials they contain, their capacity or any other feature;",
        ],
    ),
    PassagesTestCase(
        document_id="UNFCCC.document.i00001260.n0000",
        description="Grenada National Adaptation Plan. NAP1",
        search_terms="marine",
        expected_passages=[
            "7.1 A Coastal Zone Management unit is established by 2020.",
            "Link to establishment of a Coastal Zone Management Unit and Board as per the above. Costing based on short term capacity building for Task Force (50,000 per year for 5 years).",
        ],
        forbidden_passages=[
            "11.1 The Meteorological Office has established a central repository for climate-related data that is operational with information being shared among agencies by 2020. 11.2 The National Hydrological and Meteorological service is established and operationalised to collect climate - related data from all available sources by 2021.",
            "MCPMLG - Youth",
            "1.1 At least 12 Ministries/ Agencies have active CC Focal Points. 1.2 Evidence that National Climate Change Committee meets on a regular basis and is functioning at the national level, involving the private sector, CBOs and NGOs (with specific attention given to youth and gender groups).",
        ],
    ),
    PassagesTestCase(
        document_id="CCLW.executive.9724.rtl_174",
        description="Zimbabwe National Adaptation Plan. NAP1",
        search_terms="health adaptation",
        expected_passages=[
            "- A National Plan of Preventive Actions against the effects of climate change on workers' health is approved.",
            "- Training and risk communication to improve the knowledge of both health pro- fessionals and the general public",
        ],
        forbidden_passages=[],
    ),
    PassagesTestCase(
        document_id="CCLW.executive.8502.3203",
        description="National Strategy for the introduction of electric mobility in Malta and Gozo",
        search_terms="electric cars",
        expected_passages=[
            "The development of the electric vehicle industry and the promotion of the introduction of EV require the strengthening of education and research in Finland, and participation in international R&D projects conducted by the EU and others.",
            "However, there seems to be a correlation between education and drivers who replied that they do not know if they consider less polluting cars, with 15.4% of individuals with a primary level education or lower saying that they do not know whether they consider this option. Lack of environmental awareness and education regarding hybrid and EV may be a determining factor for this outcome.",
        ],
        forbidden_passages=[
            "Figure 24 - Considering less pollution vehicles by education category",
            "- Consumer education",
        ],
    ),
    PassagesTestCase(
        document_id="CCLW.executive.10205.4788",
        description="National Adaptation Plan Framework",
        search_terms="youth",
        expected_passages=[
            "Young people will remain key stakeholders in Nigeria's NAP process. Programs will, therefore, be planned to give them all possible opportunities to contribute to the various adaptation initiatives. The programs will also enable young people to be properly targeted in climate change adaptation programming.",
            "Young people at the Climate Innovation Hub in Lafia, Nasarawa State August 2019.",
        ],
        forbidden_passages=[],
    ),
    PassagesTestCase(
        document_id="UNFCCC.non-party.1141.0",
        description="SLOCAT Transport and Climate Change Global Status Report 2nd edition",
        search_terms="electric cars",
        expected_passages=[
            "Electric vehicle",
        ],
        forbidden_passages=[
            "Gender and Sustainable Mobility",
            "Lastly, in order to simultaneously improve access to opportunities and address climate change in transport, policy makers must address the mobility needs of all people, such as women and historically underserved groups (see sidebar on Gender and Sustainable Mobility). For example, public transport is not accessible unless it is safe and secure for women to use.",
        ],
    ),
    PassagesTestCase(
        document_id="UNFCCC.non-party.893.0",
        description="Nationally determined contributions under the Paris Agreement. Synthesis report by the secretariat",
        search_terms="paris agreement",
        expected_passages=[
            "Voluntary cooperation (Article 6 general)",
            "133. Total global GHG emission levels (without LULUCF) taking into account implementation of the latest NDCs of all Parties to the Paris Agreement are estimated to be around 1.3 (0.3-3.5) Gt CO2 eq, or on average 2.3 (2.23-2.38) per cent, by 2025 and 3.4 (1.4-5.5) Gt CO2 eq, or on average 5.9 (2.63-9.29) per cent, by 2030 below the levels indicated in the INDCs as at 4 April 2016.",
        ],
        forbidden_passages=[
            # "89. In addition, some Parties also referred to the standard methods and procedures contained in the 2013 Revised Supplementary Methods and Good Practice Guidance Arising from the Kyoto Protocol and the 2013 Supplement to the 2006 IPCC Guidelines for National Greenhouse Gas Inventories: Wetlands.",
            # "193. Some Parties highlighted South-South, triangular or regional cooperation as support mechanisms for NDC implementation, including for specific aspects of financial assistance, capacity-building and technology development and transfer.",
        ],
    ),
]


@pytest.mark.search_intention
@pytest.mark.parametrize("test_case", [test_case.param for test_case in test_cases])
def test_passage_thresholds(test_case: PassagesTestCase):
    return do_test_passage_thresholds(test_case, VESPA_URL)
