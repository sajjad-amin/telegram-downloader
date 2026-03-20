import re

def parse_telegram_link(url):
    """Parses a Telegram message link and returns (chat_id, message_id)."""
    # Channel message link like t.me/c/123/456
    private_match = re.search(r't\.me/c/(\d+)/(\d+)', url)
    if private_match:
        return int(f"-100{private_match.group(1)}"), int(private_match.group(2))

    # Public message link like t.me/channel/123
    public_match = re.search(r't\.me/([^/]+)/(\d+)', url)
    if public_match:
        return public_match.group(1), int(public_match.group(2))

    # Simple channel link like t.me/channel
    channel_match = re.search(r't\.me/([^/]+)', url)
    if channel_match:
        return channel_match.group(1), None

    return None, None

def parse_channel_entity(url):
    """Returns the channel name/id and optionally the message_id from a link."""
    entity, message_id = parse_telegram_link(url)
    return entity, message_id
