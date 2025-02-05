import pytest
from django_prices_vatlayer.models import VAT
from django_prices_vatlayer.utils import get_tax_for_rate

from ...tests.utils import get_graphql_content

# FIXME we are going to rewrite tax section. Currently, below tests are connected only
#  with vatlayer. After we introduce approach for taxes and API, we should rebuild this
#  tests.


@pytest.fixture
def tax_rates():
    return {
        "standard_rate": 23,
        "reduced_rates": {
            "pharmaceuticals": 8,
            "medical": 8,
            "passenger transport": 8,
            "newspapers": 8,
            "hotels": 8,
            "restaurants": 8,
            "admission to cultural events": 8,
            "admission to sporting events": 8,
            "admission to entertainment events": 8,
            "foodstuffs": 5,
        },
    }


@pytest.fixture
def taxes(tax_rates):
    taxes = {
        "standard": {
            "value": tax_rates["standard_rate"],
            "tax": get_tax_for_rate(tax_rates),
        }
    }
    if tax_rates["reduced_rates"]:
        taxes.update(
            {
                rate: {
                    "value": tax_rates["reduced_rates"][rate],
                    "tax": get_tax_for_rate(tax_rates, rate),
                }
                for rate in tax_rates["reduced_rates"]
            }
        )
    return taxes


@pytest.fixture
def vatlayer(db, tax_rates, taxes):
    VAT.objects.create(country_code="PL", data=tax_rates)

    tax_rates_2 = {
        "standard_rate": 19,
        "reduced_rates": {
            "admission to cultural events": 7,
            "admission to entertainment events": 7,
            "books": 7,
            "foodstuffs": 7,
            "hotels": 7,
            "medical": 7,
            "newspapers": 7,
            "passenger transport": 7,
        },
    }
    VAT.objects.create(country_code="DE", data=tax_rates_2)
    return taxes


def test_query_countries_with_tax(user_api_client, vatlayer, tax_rates):
    # given
    query = """
    query {
        shop {
            countries {
                code
                vat {
                    standardRate
                    reducedRates {
                        rate
                        rateType
                    }
                }
            }
        }
    }
    """

    # when
    response = user_api_client.post_graphql(query)

    # then
    content = get_graphql_content(response)
    data = content["data"]["shop"]["countries"]
    vat = VAT.objects.first()
    country = next(country for country in data if country["code"] == vat.country_code)

    rates_from_response = set(
        [(rate["rateType"], rate["rate"]) for rate in country["vat"]["reducedRates"]]
    )

    reduced_rates = set(
        [
            (tax_rate, tax_rates["reduced_rates"][tax_rate])
            for tax_rate in tax_rates["reduced_rates"]
        ]
    )

    assert country["vat"]["standardRate"] == tax_rates["standard_rate"]
    assert rates_from_response == reduced_rates


def test_query_default_country_with_tax(user_api_client, settings, vatlayer, tax_rates):
    # given
    settings.DEFAULT_COUNTRY = "PL"
    query = """
    query {
        shop {
            defaultCountry {
                code
                vat {
                    standardRate
                }
            }
        }
    }
    """

    # when
    response = user_api_client.post_graphql(query)

    # then
    content = get_graphql_content(response)
    data = content["data"]["shop"]["defaultCountry"]
    assert data["code"] == settings.DEFAULT_COUNTRY
    assert data["vat"]["standardRate"] == tax_rates["standard_rate"]
