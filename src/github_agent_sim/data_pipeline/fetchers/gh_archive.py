"""GH Archive data fetcher using BigQuery public dataset."""

import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncGenerator, Generator

import httpx

from ...config.settings import Settings, get_settings


class GHArchiveFetcher:
    """Fetcher for GH Archive data from BigQuery public dataset."""

    BASE_URL = "https://gharchive.org"
    BIGQUERY_TABLE = "githubarchive:day.{}"

    def __init__(self, settings: Settings | None = None):
        """Initialize the fetcher."""
        self.settings = settings or get_settings()
        self.client = httpx.Client(timeout=30.0)

    def get_date_range(self, days: int = 30) -> list[str]:
        """Get list of date strings for the past N days."""
        today = datetime.now().date()
        dates = []
        for i in range(days):
            date = today - timedelta(days=i)
            dates.append(date.strftime("%Y-%m-%d"))
        return dates

    def get_events_url(self, date: str) -> str:
        """Get the URL for events data on a specific date."""
        return f"{self.BASE_URL}/data/{date}-0.json.gz"

    def fetch_events_for_date(
        self,
        date: str,
        event_types: list[str] | None = None,
        repos: list[str] | None = None,
    ) -> Generator[dict, None, None]:
        """
        Fetch events for a specific date.

        Args:
            date: Date string in YYYY-MM-DD format
            event_types: Filter by event types (e.g., ['PullRequestEvent'])
            repos: Filter by repository names (e.g., ['facebook/react'])

        Yields:
            Event dictionaries
        """
        url = self.get_events_url(date)

        try:
            response = self.client.get(url)
            response.raise_for_status()

            # Decompress and parse
            with gzip.GzipFile(fileobj=response.content) as f:
                for line in f:
                    try:
                        event = json.loads(line.decode("utf-8"))

                        # Filter by event type
                        if event_types and event.get("type") not in event_types:
                            continue

                        # Filter by repo
                        if repos:
                            repo_name = event.get("repo", {}).get("name", "")
                            if repo_name not in repos:
                                continue

                        yield event

                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue

        except httpx.HTTPError as e:
            print(f"Error fetching {date}: {e}")

    def fetch_events(
        self,
        days: int = 30,
        event_types: list[str] | None = None,
        repos: list[str] | None = None,
        limit: int | None = None,
    ) -> Generator[dict, None, None]:
        """
        Fetch events for the past N days.

        Args:
            days: Number of days to fetch
            event_types: Filter by event types
            repos: Filter by repositories
            limit: Maximum number of events to return

        Yields:
            Event dictionaries
        """
        count = 0
        for date in self.get_date_range(days):
            for event in self.fetch_events_for_date(date, event_types, repos):
                yield event
                count += 1
                if limit and count >= limit:
                    return

    async def fetch_events_async(
        self,
        days: int = 30,
        event_types: list[str] | None = None,
        repos: list[str] | None = None,
        limit: int | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Async version of fetch_events."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            count = 0
            for date in self.get_date_range(days):
                url = self.get_events_url(date)
                try:
                    response = await client.get(url)
                    response.raise_for_status()

                    with gzip.GzipFile(fileobj=response.content) as f:
                        for line in f:
                            try:
                                event = json.loads(line.decode("utf-8"))

                                if event_types and event.get("type") not in event_types:
                                    continue

                                if repos:
                                    repo_name = event.get("repo", {}).get("name", "")
                                    if repo_name not in repos:
                                        continue

                                yield event
                                count += 1
                                if limit and count >= limit:
                                    return

                            except (json.JSONDecodeError, UnicodeDecodeError):
                                continue

                except httpx.HTTPError:
                    continue

    def download_and_save(
        self,
        output_dir: Path,
        days: int = 7,
        event_types: list[str] | None = None,
        repos: list[str] | None = None,
    ) -> list[Path]:
        """
        Download events and save to files.

        Args:
            output_dir: Directory to save files
            days: Number of days to fetch
            event_types: Filter by event types
            repos: Filter by repositories

        Returns:
            List of saved file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []
        for date in self.get_date_range(days):
            events = list(self.fetch_events_for_date(date, event_types, repos))

            if events:
                output_file = output_dir / f"events_{date}.jsonl.gz"
                with gzip.open(output_file, "wt", encoding="utf-8") as f:
                    for event in events:
                        f.write(json.dumps(event) + "\n")
                saved_files.append(output_file)
                print(f"Saved {len(events)} events to {output_file}")

        return saved_files


# Event types of interest
EVENT_TYPES = [
    "PushEvent",
    "PullRequestEvent",
    "PullRequestReviewEvent",
    "PullRequestReviewCommentEvent",
    "IssueCommentEvent",
    "IssuesEvent",
]

# Sample repos for testing
SAMPLE_REPOS = [
    "facebook/react",
    "vercel/next.js",
    "microsoft/vscode",
]
