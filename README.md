# RSS Parser for Home Assistant

[Deutsch](README.de.md) | **English**

> **Note:** This code has been generated with AI assistance.

RSS Parser is a custom Home Assistant integration for polling RSS and Atom feeds, filtering new entries, and forwarding matching entries to notification entities. All runtime configuration is available in the Home Assistant UI.

## Features

- Any number of feeds; add the integration once per feed
- RSS 2.0 and Atom support
- Include and exclude filters for text and categories
- Optional regular expressions, case sensitivity, and maximum entry age
- Persistent duplicate detection across Home Assistant restarts
- Individual or combined notifications through `notify.send_message`
- Sensor containing the latest matching entry
- `rss_parser_new_entry` event for custom automations
- Conditional HTTP requests using `ETag` and `Last-Modified`
- English and German UI

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mbraunschweiler&repository=HA-RssFeedParser)

### HACS custom repository

1. Open HACS in Home Assistant.
2. Add this GitHub repository as a custom repository of type **Integration**.
3. Search for **RSS Parser** and install it.
4. Restart Home Assistant.
5. Go to **Settings > Devices & services > Add integration** and select **RSS Parser**.

### Manual installation

Copy `custom_components/rss_parser` into the `custom_components` directory of your Home Assistant configuration, restart Home Assistant, and add the integration from the UI.

## Configuration

Add one integration entry for every feed. The setup dialog asks for:

- a display name,
- an HTTP or HTTPS feed URL,
- whether entries already present during the first poll should be sent.

The URL is fetched and parsed before the entry is created. URLs containing embedded credentials are intentionally rejected so credentials do not leak into diagnostics or logs.

Use **Configure** on the integration entry to change polling, filters, and notifications. Use **Reconfigure** to change the name or URL.

### Filtering

Include and exclude values can be separated by commas or new lines. The searchable text consists of the title, summary, author, link, and categories.

The rules are applied in this order:

1. Ignore entries already observed.
2. Apply the maximum age.
3. Apply text exclusions.
4. Apply text inclusions.
5. Apply category exclusions and inclusions.

An exclusion always wins. Empty inclusion fields match every entry. If regular expressions are enabled, every comma- or newline-separated value is compiled and validated before saving.

Observed entries are remembered even if a filter rejects them. Changing filters therefore affects newly received entries, not old entries that were already seen.

### Notifications

Enable notifications and select one or more entities from the `notify` domain. RSS Parser calls Home Assistant's `notify.send_message` action. Notification integrations that expose only legacy actions such as `notify.mobile_app_name` without a corresponding entity are not supported in version 0.1.0.

Messages support these safe placeholders:

- `{title}`
- `{link}`
- `{summary}`
- `{author}`
- `{feed_name}`
- `{published}`

No Jinja expressions are evaluated.

## Automation event

Every new matching entry fires `rss_parser_new_entry`, whether direct notifications are enabled or not. Example:

```yaml
triggers:
  - trigger: event
    event_type: rss_parser_new_entry
conditions:
  - condition: template
    value_template: "{{ trigger.event.data.feed_name == 'Home Assistant Blog' }}"
actions:
  - action: persistent_notification.create
    data:
      title: "{{ trigger.event.data.title }}"
      message: "{{ trigger.event.data.link }}"
```

The event contains `entry_id`, `feed_name`, `title`, `link`, `summary`, `author`, `categories`, and `published`.

## Safety and limits

- Minimum polling interval: 5 minutes
- Maximum response size: 5 MiB
- Stored duplicate IDs per feed: 500
- Maximum matching entries processed per poll: configurable from 1 to 100
- Existing entries are not sent by default during initial setup

If more matching entries arrive than the configured per-poll limit, only the newest entries within the limit are emitted. All observed IDs are marked as processed to prevent a delayed notification flood.

## Development

Install the lightweight test dependencies and run the checks:

```powershell
python -m pip install -r requirements-test.txt
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Pull requests are checked with pytest, Ruff, Hassfest, and the HACS validation action.

## Repository

Source code, releases, and issue tracking are hosted at [mbraunschweiler/HA-RssFeedParser](https://github.com/mbraunschweiler/HA-RssFeedParser).

## License

MIT
