import pytest
from requests.exceptions import HTTPError, InvalidURL, Timeout

from checkmatelib.client import CheckmateClient
from checkmatelib.exceptions import BadURL, CheckmateException, CheckmateServiceError


class TestCheckmateClient:
    def test_it_with_an_unblocked_response(self, client, response):
        response.status_code = 204

        hits = client.check_url("http://good.example.com")

        assert not hits
        response.json.assert_not_called()

    def test_it_with_a_blocked_response(
        self, client, requests, response, BlockResponse
    ):
        hits = client.check_url("http://bad.example.com")

        requests.get.assert_called_once_with(
            "http://checkmate.example.com/api/check",
            params={"url": "http://bad.example.com"},
            timeout=1,
        )

        assert hits == BlockResponse.return_value
        BlockResponse.assert_called_once_with(response.json.return_value)

    @pytest.mark.parametrize(
        "exception,expected",
        (
            (Timeout, CheckmateServiceError),
            (InvalidURL, BadURL),
            (HTTPError, CheckmateException),
        ),
    )
    def test_failed_connection(self, client, requests, exception, expected):
        requests.get.side_effect = exception("Something bad")
        with pytest.raises(expected):
            client.check_url("http://bad.example.com")

    def test_failed_response(self, client, response):
        response.raise_for_status.side_effect = HTTPError("Something bad")

        with pytest.raises(CheckmateException):
            client.check_url("http://bad.example.com")

    def test_it_with_a_bad_json_payload(self, client, response):
        response.json.side_effect = ValueError

        with pytest.raises(CheckmateException):
            client.check_url("http://bad.example.com")

    @pytest.mark.parametrize("url", ("http://", "/", "http:///", "http:///path", "/"))
    def test_it_with_bad_urls(self, client, url):
        with pytest.raises(BadURL):
            client.check_url(url)

    @pytest.fixture
    def client(self):
        return CheckmateClient(host="http://checkmate.example.com/")

    @pytest.fixture
    def response(self, requests):
        response = requests.get.return_value
        response.status_code = 200

        return response


@pytest.fixture(autouse=True)
def BlockResponse(patch):
    return patch("checkmatelib.client.BlockResponse")


@pytest.fixture(autouse=True)
def requests(patch):
    requests = patch("checkmatelib.client.requests")

    return requests
