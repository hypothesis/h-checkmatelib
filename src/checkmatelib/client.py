"""A client for the Checkmate URL testing service."""

import requests

from checkmatelib._response import BlockResponse
from checkmatelib.exceptions import (
    BadURL,
    CheckmateServiceError,
    handles_request_errors,
)
from checkmatelib.url.canonicalize import CanonicalURL
from checkmatelib.url.domain import Domain


# pylint: disable=too-few-public-methods
class CheckmateClient:
    """A client for the Checkmate URL testing service."""

    MAX_URL_LENGTH = 2000

    def __init__(self, host, api_key):
        """Initialise a client for contacting the Checkmate service.

        CHECKMATE_API_KEY must be present to configure authentication

        :param host: The host including scheme, for the Checkmate service
        :param api_key: API key for Checkmate
        """
        self._host = host.rstrip("/")

        self._api_key = api_key

    @handles_request_errors
    def check_url(  # pylint: disable=inconsistent-return-statements
        self, url, allow_all=False, blocked_for=None, ignore_reasons=None
    ):
        """Check a URL for reasons to block.

        :param url: URL to check
        :param allow_all: If True, bypass Checkmate's allow-list
        :param blocked_for: Sets a context for the blocked pages layout/content
        :param ignore_reasons: Ignore this class of detections. Comma separated
            reasons.

        :raises BadURL: If the provided URL is bad
        :raises CheckmateServiceError: For problems contacting the service
        :raises CheckmateException: For any other issue with Checkmate

        :return: None if the URL is fine or a `CheckmateResponse` if there are
           reasons to block the URL.
        """

        params = {"url": self._clean_url(url)}

        if allow_all:
            params["allow_all"] = True

        if blocked_for:
            params["blocked_for"] = blocked_for

        if ignore_reasons:
            params["ignore_reasons"] = ignore_reasons

        response = requests.get(
            self._host + "/api/check",
            params=params,
            timeout=1,
            auth=(self._api_key, "") if self._api_key else None,
        )

        response.raise_for_status()

        if response.status_code == 204:
            # No news is good news
            return None

        try:
            return BlockResponse(response.json())

        except ValueError as err:
            raise CheckmateServiceError("Unprocessable JSON response") from err

    @classmethod
    def _clean_url(cls, url):
        """Clean the URL before we send it.

        Checkmate will do this for itself, and doesn't trust our input, but
        this allows us to fail fast for bad URLs, before Checkmate has a chance
        to check them. We can also apply extra constraints.
        """

        # Truncate extremely long URLs, so we don't get 400's and fail open
        parts = CanonicalURL.canonical_split(url[: cls.MAX_URL_LENGTH])

        # Enforce that domains are valid and public
        domain = Domain(parts[1])
        if not domain.is_public:
            raise BadURL(f"The domain '{domain}' does not look publicly accessible")

        return CanonicalURL.canonical_join(parts)
