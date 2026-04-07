# content/tasks/events.py - Event fetcher and cleanup tasks

import re
import time
import logging
from datetime import timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.utils import timezone
from django.conf import settings
from dateutil import parser as date_parser
from celery import shared_task

from content.models import Event, EventSource
from content.utils import get_http_session, parse_date_string
from content.constants import (
    TICKETMASTER_PRIORITY_COUNTRIES,
    TICKETMASTER_FALLBACK_COUNTRIES,
    TICKETMASTER_LOCATION_MAP,
    NIGERIAN_EVENT_SITES,
    EVENTBRITE_DEFAULT_LOCATIONS,
)
from accounts.models import UserPreference

try:
    from notifications.tasks import send_event_reminder
except ImportError:
    send_event_reminder = None

logger = logging.getLogger(__name__)


# ==========================================
# EVENT HELPERS
# ==========================================
def _normalize_event_title(title: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", "", title.lower()).split())


def _is_duplicate_event(title: str, venue: str, start_time, source: str) -> bool:
    normalized = _normalize_event_title(title)
    window_start = start_time - timedelta(hours=12)
    window_end = start_time + timedelta(hours=12)

    existing = Event.objects.filter(
        start_time__gte=window_start,
        start_time__lte=window_end,
        venue_name__iexact=venue,
        sources__source_name=source,
    ).distinct()

    return any(_normalize_event_title(e.canonical_title) == normalized for e in existing)


def _extract_proper_categories(classifications: list) -> list:
    categories = []
    for cls in classifications:
        for field in ("segment", "genre", "subGenre"):
            name = cls.get(field, {}).get("name")
            if name and name not in ("Undefined", "Other"):
                categories.append(name)
    return list(dict.fromkeys(c for c in categories if c)) or ["General"]


def _schedule_reminder(event):
    if send_event_reminder and event.start_time > timezone.now() + timedelta(hours=2):
        send_event_reminder.apply_async(
            args=[event.id, 2],
            eta=event.start_time - timedelta(hours=2),
        )


def _trigger_event_summary(event):
    from content.tasks.summaries import generate_event_summary
    generate_event_summary.delay(event.id)


# ==========================================
# TICKETMASTER
# ==========================================
@shared_task(name='content.tasks.fetch_ticketmaster_events', bind=True, max_retries=2, default_retry_delay=60)
def fetch_ticketmaster_events(self):
    """Fetch events from Ticketmaster with Africa/Nigeria priority."""
    if not settings.TICKETMASTER_API_KEY:
        logger.error("TICKETMASTER_API_KEY missing")
        return 0

    session = get_http_session()
    fetched = 0
    now_utc = timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "apikey": settings.TICKETMASTER_API_KEY,
        "size": 50,
        "sort": "date,asc",
        "startDateTime": now_utc,
        "locale": "*",
        "classificationName": "music,sports,arts_theatre,family,festival,miscellaneous",
    }

    # Build country list from user preferences
    user_locations = set()
    for pref in UserPreference.objects.filter(onboarding_completed=True).only("preferred_locations"):
        user_locations.update(pref.preferred_locations)

    target_countries = TICKETMASTER_PRIORITY_COUNTRIES.copy()
    if user_locations:
        user_codes = {TICKETMASTER_LOCATION_MAP.get(loc) for loc in user_locations}
        user_codes.discard(None)
        target_countries = list(dict.fromkeys(
            list(user_codes) + TICKETMASTER_PRIORITY_COUNTRIES + TICKETMASTER_FALLBACK_COUNTRIES
        ))
    else:
        target_countries += TICKETMASTER_FALLBACK_COUNTRIES

    seen = set()
    for country in target_countries[:10]:
        if country in seen:
            continue
        seen.add(country)
        params["countryCode"] = country

        try:
            resp = session.get(
                "https://app.ticketmaster.com/discovery/v2/events.json",
                params=params, timeout=30,
            )
            if resp.status_code == 401:
                logger.error("[Ticketmaster] Auth failed")
                return 0
            if resp.status_code == 429:
                break
            if resp.status_code != 200:
                continue

            events = resp.json().get("_embedded", {}).get("events", [])

            for event in events:
                ext_id = event["id"]
                if EventSource.objects.filter(external_id=ext_id, source_name="ticketmaster").exists():
                    continue

                venue = event.get("_embedded", {}).get("venues", [{}])[0]
                venue_name = venue.get("name", "Venue TBA")
                city = venue.get("city", {}).get("name", "")
                country_name = venue.get("country", {}).get("name", "")
                location_name = ", ".join(filter(None, [city, country_name])) or "International"

                start_str = event.get("dates", {}).get("start", {}).get("dateTime")
                start_time = parse_date_string(start_str, fallback=timezone.now() + timedelta(days=30))

                if _is_duplicate_event(event["name"], venue_name, start_time, "ticketmaster"):
                    continue

                categories = _extract_proper_categories(event.get("classifications", []))

                images = event.get("images", [])
                image_url = next(
                    (img["url"] for img in images if img.get("ratio") == "16_9" and img.get("width", 0) > 800),
                    images[0]["url"] if images else "",
                )

                new_event = Event.objects.create(
                    canonical_title=event["name"][:600],
                    description=event.get("info") or event.get("pleaseNote") or "",
                    image_url=image_url,
                    start_time=start_time,
                    venue_name=venue_name,
                    location_name=location_name,
                    categories=categories,
                    keywords=event.get("keywords", []),
                )

                EventSource.objects.create(
                    event=new_event,
                    url=event.get("url", ""),
                    source_name="ticketmaster",
                    external_id=ext_id,
                )

                fetched += 1
                _schedule_reminder(new_event)
                _trigger_event_summary(new_event)

        except Exception as e:
            logger.error(f"[Ticketmaster] Error for {country}: {e}")

    logger.info(f"[Ticketmaster] COMPLETE: {fetched} events")
    return fetched


# ==========================================
# EVENTBRITE API
# ==========================================
@shared_task(name='content.tasks.fetch_eventbrite_events', bind=True, max_retries=2, default_retry_delay=60)
def fetch_eventbrite_events(self):
    """Fetch events from Eventbrite API."""
    if not settings.EVENTBRITE_PRIVATE_TOKEN:
        logger.error("EVENTBRITE_PRIVATE_TOKEN missing")
        return 0

    session = get_http_session()
    fetched = 0
    headers = {"Authorization": f"Bearer {settings.EVENTBRITE_PRIVATE_TOKEN}"}

    user_locations = set()
    for pref in UserPreference.objects.filter(onboarding_completed=True).only("preferred_locations"):
        user_locations.update(pref.preferred_locations)

    locations = list(user_locations) + [
        "Nigeria", "Lagos", "Abuja", "Ghana", "Accra", "Kenya", "Nairobi",
        "South Africa", "Johannesburg", "Cape Town",
    ] if user_locations else [
        "Nigeria", "Lagos", "Abuja", "Ghana", "Accra", "Kenya", "Nairobi",
        "South Africa", "Johannesburg", "Cape Town",
    ]
    locations = list(set(locations))

    for loc in locations[:5]:
        params = {
            "q": "events",
            "location.address": loc,
            "start_date.range_start": timezone.now().isoformat(),
            "sort_by": "date",
            "expand": "venue,ticket_availability",
            "page_size": 50,
        }

        try:
            resp = session.get(
                "https://www.eventbriteapi.com/v3/events/search/",
                headers=headers, params=params, timeout=30,
            )
            if resp.status_code != 200:
                continue

            for event in resp.json().get("events", []):
                ext_id = event["id"]
                if EventSource.objects.filter(external_id=ext_id, source_name="eventbrite").exists():
                    continue

                venue = event.get("venue", {})
                location_name = venue.get("address", {}).get("localized_address_display", loc)
                start_str = event.get("start", {}).get("utc")
                start_time = date_parser.isoparse(start_str) if start_str else timezone.now()

                new_event = Event.objects.create(
                    canonical_title=event["name"]["text"],
                    description=event.get("summary", "") or event.get("description", {}).get("text", ""),
                    image_url=event.get("logo", {}).get("url") or "",
                    start_time=start_time,
                    venue_name=venue.get("name"),
                    location_name=location_name,
                    categories=event.get("category", {}).get("name", ""),
                    keywords=[],
                )

                EventSource.objects.create(
                    event=new_event,
                    url=event["url"],
                    source_name="eventbrite",
                    external_id=ext_id,
                )

                fetched += 1
                _schedule_reminder(new_event)
                _trigger_event_summary(new_event)

        except Exception as e:
            logger.error(f"Eventbrite fetch failed ({loc}): {e}")

    logger.info(f"[Eventbrite] {fetched} events")
    return fetched


# ==========================================
# EVENTBRITE SCRAPING
# ==========================================
@shared_task(name='content.tasks.fetch_eventbrite_scraped_events', bind=True, max_retries=1, default_retry_delay=120)
def fetch_eventbrite_scraped_events(self):
    """Scrape Eventbrite for local African/Nigerian events."""
    fetched = 0

    user_locations = set()
    for pref in UserPreference.objects.filter(onboarding_completed=True).only("preferred_locations"):
        user_locations.update(pref.preferred_locations)

    base_locations = EVENTBRITE_DEFAULT_LOCATIONS.copy()
    if user_locations:
        normalized = [loc.lower().replace(" ", "-") for loc in user_locations]
        base_locations = list(dict.fromkeys(normalized + base_locations))
    base_locations = base_locations[:5]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for loc in base_locations:
        url = f"https://www.eventbrite.com/d/{loc}/all-events/"
        try:
            resp = requests.get(url, headers=headers, timeout=45)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            event_cards = (
                soup.select("div.eds-event-card-content__content-container")
                or soup.select("div.search-event-card")
                or soup.select("article.event-card")
            )
            if not event_cards:
                continue

            for card in event_cards[:25]:
                title_tag = card.select_one("h3, div.eds-event-card-content__title, a[data-testid='event-card-title-link']")
                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                event_url = title_tag["href"] if title_tag.name == "a" else title_tag.find("a")["href"]
                if not event_url.startswith("http"):
                    event_url = "https://www.eventbrite.com" + event_url

                if Event.objects.filter(sources__url=event_url, sources__source_name="eventbrite_scraped").exists():
                    continue

                img_tag = card.select_one("img")
                image_url = img_tag["src"] if img_tag and img_tag.get("src") else ""

                date_tag = card.select_one("div.eds-event-card-content__primary-content time, p[data-testid='event-card-date']")
                date_str = date_tag.get_text(strip=True) if date_tag else "Upcoming"

                location_tag = card.select_one("p.eds-event-card-content__sub, div[data-testid='event-card-location']")
                location_name = location_tag.get_text(strip=True) if location_tag else loc.replace("-", " ").title()

                start_time = parse_date_string(date_str)

                new_event = Event.objects.create(
                    canonical_title=title,
                    description="",
                    image_url=image_url,
                    start_time=start_time,
                    venue_name="",
                    location_name=location_name,
                    categories=[],
                    keywords=[],
                )

                EventSource.objects.create(
                    event=new_event,
                    url=event_url,
                    source_name="eventbrite_scraped",
                    external_id="",
                )

                fetched += 1
                _trigger_event_summary(new_event)

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout scraping Eventbrite {loc}")
        except Exception as e:
            logger.error(f"Eventbrite scraping error {loc}: {e}")

        time.sleep(5)

    logger.info(f"[Eventbrite scraping] {fetched} events")
    return fetched


# ==========================================
# NIGERIAN LOCAL EVENTS
# ==========================================
@shared_task(name='content.tasks.fetch_local_nigerian_events', bind=True, max_retries=1, default_retry_delay=120)
def fetch_local_nigerian_events(self):
    """Scrape Nigerian event platforms."""
    fetched = 0

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
    }

    for site in NIGERIAN_EVENT_SITES:
        try:
            resp = requests.get(site["url"], headers=headers, timeout=45, allow_redirects=True)
            if resp.status_code != 200:
                continue

            page_text = resp.text
            if len(page_text) < 3000:
                continue
            if any(block in page_text.lower() for block in ("captcha", "access denied", "forbidden")):
                logger.warning(f"[{site['name']}] Bot detection triggered")
                continue

            soup = BeautifulSoup(page_text, "html.parser")

            cards = []
            for selector in site["selectors"]:
                cards = soup.select(selector)
                if cards:
                    break

            if not cards:
                cards = (
                    soup.find_all("div", class_=lambda x: x and ("event" in str(x).lower() or "card" in str(x).lower()))
                    or soup.find_all("article")
                    or soup.select("a[href*='event']")
                    or []
                )

            if not cards:
                continue

            for card in cards[:50]:
                try:
                    link_tag = card.find("a", href=True) if card.name != "a" else card
                    if not link_tag:
                        continue

                    event_url = link_tag.get("href", "").strip()
                    if not event_url or event_url in ("#", "javascript:void(0)", "/"):
                        continue
                    if not event_url.startswith("http"):
                        event_url = urljoin(site["url"], event_url)
                    if not any(kw in event_url.lower() for kw in ("event", "/e/", "show", "ticket", "concert", "festival")):
                        continue
                    if Event.objects.filter(sources__url=event_url).exists():
                        continue

                    # Extract title
                    heading = card.find(["h1", "h2", "h3", "h4", "h5"])
                    title = heading.get_text(strip=True) if heading else ""
                    if not title:
                        title = link_tag.get_text(strip=True)
                    if not title or len(title) < 5:
                        title = link_tag.get("title", "") or card.get("title", "")
                    if not title or len(title) < 5:
                        title = card.get_text(strip=True)[:100]
                    if not title or len(title) < 5:
                        continue

                    # Extract image
                    img_tag = card.find("img")
                    image_url = ""
                    if img_tag:
                        image_url = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("data-lazy-src") or ""
                        if image_url and not image_url.startswith("http"):
                            image_url = urljoin(site["url"], image_url)

                    # Extract date
                    date_tag = card.find(["time", "span", "div"], class_=lambda x: x and "date" in str(x).lower())
                    start_time = timezone.now() + timedelta(days=7)
                    if date_tag:
                        date_str = date_tag.get("datetime") or date_tag.get_text(strip=True)
                        start_time = parse_date_string(date_str, fallback=start_time)

                    # Extract location
                    loc_tag = card.find(["span", "div", "p"], class_=lambda x: x and "location" in str(x).lower())
                    location_name = loc_tag.get_text(strip=True) if loc_tag else "Nigeria"

                    new_event = Event.objects.create(
                        canonical_title=title[:600],
                        description="",
                        image_url=image_url,
                        start_time=start_time,
                        venue_name="",
                        location_name=location_name,
                        categories=[],
                        keywords=[],
                    )

                    EventSource.objects.create(
                        event=new_event,
                        url=event_url,
                        source_name=site["source"],
                        external_id="",
                    )

                    fetched += 1
                    _trigger_event_summary(new_event)

                except Exception:
                    continue

        except requests.exceptions.Timeout:
            logger.warning(f"[{site['name']}] Timeout")
        except Exception as e:
            logger.error(f"[{site['name']}] Error: {e}")

        time.sleep(6)

    logger.info(f"[Nigerian events] {fetched} events")
    return fetched


# ==========================================
# CLEANUP
# ==========================================
@shared_task(name='content.tasks.cleanup_duplicate_events')
def cleanup_duplicate_events():
    """Remove duplicate events."""
    removed = 0
    events = Event.objects.filter(
        sources__source_name__in=["ticketmaster", "eventbrite", "eventbrite_scraped"],
    ).distinct().order_by("canonical_title", "venue_name", "start_time")

    seen = {}
    to_delete = []

    for event in events:
        key = (
            _normalize_event_title(event.canonical_title),
            (event.venue_name or "").lower(),
            event.start_time.strftime("%Y-%m-%d-%H"),
        )

        if key in seen:
            existing = seen[key]
            if len(event.description or "") > len(existing.description or "") or event.image_url:
                to_delete.append(existing.id)
                seen[key] = event
            else:
                to_delete.append(event.id)
        else:
            seen[key] = event

    if to_delete:
        Event.objects.filter(id__in=to_delete).delete()
        removed = len(to_delete)

    logger.info(f"[Cleanup] Removed {removed} duplicate events")
    return removed
