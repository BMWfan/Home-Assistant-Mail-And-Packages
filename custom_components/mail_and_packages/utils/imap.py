"""IMAP connection and search utilities for Mail and Packages."""

import asyncio
import binascii
import datetime
import email
import logging
import re
from dataclasses import dataclass
from email.header import decode_header

import aioimaplib
from aioimaplib import (
    AUTH,
    IMAP4,
    IMAP4_SSL,
    NONAUTH,
    SELECTED,
    AioImapException,
    Cmd,
    Command,
    Exec,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import ssl

from custom_components.mail_and_packages.const import DEFAULT_IMAP_TIMEOUT

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuerySpec:
    """Structured criteria for one collect_queries() entry.

    `query` is the exact IMAP SEARCH string build_search() would produce --
    kept as the search-cache key so the normal per-sensor email_search() path
    (which builds and looks up that same string) still gets cache hits after
    a client-side classification pass. The other fields let the batch
    pre-fetch classify messages from one broad per-folder fetch instead of
    running `query` itself as a real SEARCH command.
    """

    query: str
    addresses: tuple[str, ...]
    subjects: tuple[str, ...]
    since_date: str
    header: str = ""


# Register ESEARCH command if not already present in aioimaplib
if "ESEARCH" not in aioimaplib.Commands:
    aioimaplib.Commands["ESEARCH"] = Cmd("ESEARCH", (AUTH, SELECTED), Exec.is_async)


def encode_imap_utf7(s: str) -> str:
    """Encode a string into IMAP modified UTF-7."""
    res = []
    unicode_buffer = []

    def flush_unicode():
        if unicode_buffer:
            u_str = "".join(unicode_buffer)
            encoded_bytes = u_str.encode("utf-16be")
            b64 = (
                binascii.b2a_base64(encoded_bytes)
                .decode("ascii")
                .rstrip("\n=")
                .replace("/", ",")
            )
            res.append(f"&{b64}-")
            unicode_buffer.clear()

    for char in s:
        ord_c = ord(char)
        if 0x20 <= ord_c <= 0x7E:
            if char == "&":
                flush_unicode()
                res.append("&-")
            else:
                if unicode_buffer:
                    flush_unicode()
                res.append(char)
        else:
            unicode_buffer.append(char)

    flush_unicode()
    return "".join(res)


def decode_imap_utf7(s: str) -> str:
    """Decode a string from IMAP modified UTF-7."""
    res = []
    i = 0
    n = len(s)
    while i < n:
        char = s[i]
        if char == "&":
            end = s.find("-", i + 1)
            if end == -1:
                res.append("&")
                i += 1
            elif end == i + 1:
                res.append("&")
                i += 2
            else:
                b64_part = s[i + 1 : end]
                b64_part = b64_part.replace(",", "/")
                pad = len(b64_part) % 4
                if pad:
                    b64_part += "=" * (4 - pad)
                try:
                    decoded_bytes = binascii.a2b_base64(b64_part)
                    res.append(decoded_bytes.decode("utf-16be"))
                except (binascii.Error, UnicodeDecodeError, ValueError):
                    res.append(s[i : end + 1])
                i = end + 1
        else:
            res.append(char)
            i += 1

    return "".join(res)


_ATOM_SPECIALS = frozenset('(){%*"\\] ')


def _is_imap_atom(s: str) -> bool:
    """Check if the string is a valid IMAP atom."""
    return bool(s) and all(0x20 < ord(c) < 0x7F and c not in _ATOM_SPECIALS for c in s)


def quote_folder(folder: str) -> str:
    """Ensure folder name is properly quoted for IMAP commands."""
    if folder.startswith('"') and folder.endswith('"'):
        return folder
    return folder if _is_imap_atom(folder) else f'"{folder}"'


class InvalidAuth(HomeAssistantError):
    """Raise exception for invalid credentials."""


async def login(
    hass: HomeAssistant,
    host: str,
    port: int,
    user: str,
    pwd: str,
    security: str,
    verify: bool = True,
    oauth_token: str | None = None,
    timeout: float = DEFAULT_IMAP_TIMEOUT,
) -> IMAP4_SSL | IMAP4:
    """Login to IMAP server asynchronously.

    Supports both password and OAuth2 (XOAUTH2) authentication.
    If oauth_token is provided, uses XOAUTH2 SASL mechanism.
    Otherwise falls back to standard LOGIN command.
    """
    ssl_context = (
        ssl.client_context(ssl.SSLCipherList.PYTHON_DEFAULT)
        if verify
        else ssl.create_no_verify_ssl_context()
    )
    if security == "SSL":
        account = IMAP4_SSL(
            host=host, port=port, ssl_context=ssl_context, timeout=timeout
        )
    else:
        account = IMAP4(host=host, port=port, timeout=timeout)

    await account.wait_hello_from_server()

    if account.protocol.state == NONAUTH:
        try:
            if oauth_token:
                await account.xoauth2(user, oauth_token)
            else:
                await account.login(user, pwd)
        except TimeoutError:
            raise
        except (AioImapException, OSError) as err:
            _LOGGER.error("Error logging in to IMAP Server: %s", err)
            raise InvalidAuth from err

    if account.protocol.state not in {AUTH, SELECTED}:
        _LOGGER.error("Error logging in to IMAP Server")
        raise InvalidAuth
    return account


async def selectfolder(account: IMAP4_SSL, folder: str) -> bool:
    """Select folder inside the mailbox asynchronously."""
    if getattr(account, "_current_folder", None) == folder:
        return True

    encoded_folder = encode_imap_utf7(folder)
    quoted_folder = quote_folder(encoded_folder)

    try:
        await account.select(quoted_folder)
    except TimeoutError:
        raise
    except (AioImapException, OSError) as err:
        _LOGGER.error("Error selecting folder %s: %s", folder, err)
        return False
    else:
        account._current_folder = folder  # noqa: SLF001
        return True


def build_search(  # noqa: C901
    address: list,
    date: str,
    subject: str | list[str] = "",
    header: str = "",
    is_yahoo: bool = False,
) -> tuple:
    """Build IMAP search query.

    Return tuple of utf8 flag and search query.
    Non-ASCII characters are stripped from subject to ensure compatibility
    with servers that only support US-ASCII charset (e.g. Microsoft Exchange).
    IMAP SUBJECT performs substring matching, so stripping non-ASCII chars
    still matches the original subject (e.g. 'Livr' matches 'Livré').

    When `header` is provided, each address is matched as either a forwarded
    email (via HEADER substring match) OR a direct email (via FROM), so the
    same config works for carriers that are forwarded through a service like
    SimpleLogin AND carriers whose emails arrive directly in the mailbox.
    IMAP HEADER does substring matching, so "mcinfo@ups.com" will match a
    header value of "UPS <mcinfo@ups.com>".
    """
    the_date = f"SINCE {date}"

    if not address:
        raise ValueError("address list must not be empty")

    # Build the address/header clause
    if header:
        # Each address matches via header (forwarded) OR FROM (direct), so
        # users with mixed setups (some carriers forwarded, others direct)
        # don't need separate configurations.
        parts = [f'OR HEADER "{header}" "{a}" FROM "{a}"' for a in address]
        if len(parts) == 1:
            addr_clause = parts[0]
            if is_yahoo:
                addr_clause = f"({addr_clause})"
        else:
            or_prefix = " ".join(["OR"] * (len(parts) - 1))
            addr_clause = f"{or_prefix} {' '.join(parts)}"
            if is_yahoo:
                addr_clause = f"({addr_clause})"
    elif len(address) == 1:
        addr_clause = f'FROM "{address[0]}"'
    else:
        joined = '" FROM "'.join(address)
        or_prefix = " ".join(["OR"] * (len(address) - 1))
        addr_clause = f'{or_prefix} FROM "{joined}"'
        if is_yahoo:
            addr_clause = f"({addr_clause})"

    # Handle multiple subjects
    subject_part = ""
    if subject:
        subjects = [subject] if isinstance(subject, str) else subject
        safe_subjects = [s.encode("ascii", "ignore").decode("ascii") for s in subjects]
        safe_subjects = [s for s in safe_subjects if s]

        if len(safe_subjects) == 1:
            subject_part = f'SUBJECT "{safe_subjects[0]}"'
        elif len(safe_subjects) > 1:
            subject_prefix = " ".join(["OR"] * (len(safe_subjects) - 1))
            if is_yahoo:
                subject_part = (
                    f'({subject_prefix} SUBJECT "{'" SUBJECT "'.join(safe_subjects)}")'
                )
            else:
                subject_part = (
                    f'{subject_prefix} SUBJECT "{'" SUBJECT "'.join(safe_subjects)}"'
                )

    if is_yahoo:
        if subject_part:
            imap_search = f"({addr_clause} {subject_part} {the_date})"
        else:
            imap_search = f"({addr_clause} {the_date})"
    elif subject_part:
        imap_search = f"{addr_clause} {subject_part} {the_date}"
    else:
        imap_search = f"{addr_clause} {the_date}"

    _LOGGER.debug("DEBUG imap_search: %s", imap_search)

    return (False, imap_search)


def parse_search_response(lines: list[bytes]) -> list[bytes]:
    """Parse IMAP SEARCH response lines and return list of UID/ID bytes.

    Handles both standard server responses (prefixed with b"SEARCH")
    and mocked test inputs (which often contain raw UIDs directly).
    Filters out the SEARCH keyword, tagged OK/status responses,
    and any non-numeric tokens.
    """
    uids = []
    for line in lines:
        if not line:
            continue
        parts = line.split()
        if not parts:
            continue

        if parts[0] == b"SEARCH":
            # Check if this is a search result line, e.g. b"SEARCH 1001 1002"
            # (as opposed to b"SEARCH completed")
            if len(parts) > 1 and parts[1].isdigit():
                uids.extend(parts[1:])
        # Check if this line is just a list of numeric UIDs (mock/test compatibility)
        # and ignore status/existence responses like b"23 EXISTS"
        elif all(p.isdigit() for p in parts):
            uids.extend(parts)

    return uids


def _parse_esearch_line(line_bytes: bytes) -> list[bytes]:
    """Parse a single ESEARCH line and return list of formatted UID bytes: b'folder/uid'."""
    line_str = line_bytes.decode("utf-8", "ignore")

    # Extract the correlator inside parentheses
    start_paren = line_str.find("(")
    end_paren = line_str.find(")", start_paren) if start_paren != -1 else -1
    if start_paren == -1 or end_paren == -1:
        return []

    correlator = line_str[start_paren + 1 : end_paren]

    # Extract mailbox name (could be quoted or unquoted)
    mailbox_match = re.search(r'MAILBOX\s+"([^"]+)"', correlator)
    if not mailbox_match:
        mailbox_match = re.search(r"MAILBOX\s+(\S+)", correlator)
    if not mailbox_match:
        return []
    mailbox = mailbox_match.group(1)
    mailbox = decode_imap_utf7(mailbox)

    # Extract the sequence set after 'UID ALL' anywhere in the line
    seq_match = re.search(r"UID\s+ALL\s+(\S+)", line_str)
    if not seq_match:
        return []
    seq_set = seq_match.group(1)

    uids = []
    for part in seq_set.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            try:
                start_str, end_str = part.split(":", 1)
                start, end = int(start_str), int(end_str)
                if start <= end:
                    uids.extend(str(x) for x in range(start, end + 1))
                else:
                    uids.extend(str(x) for x in range(end, start + 1))
            except ValueError:
                pass
        else:
            uids.append(part)
    return [f"{mailbox}/{uid}".encode() for uid in uids]


def _get_search_cache(account: IMAP4_SSL) -> dict:
    """Return the per-scan search-result cache attached to this connection."""
    if not hasattr(account, "_search_cache"):
        account._search_cache = {}  # noqa: SLF001
    return account._search_cache  # noqa: SLF001


async def _execute_single_search(account: IMAP4_SSL, search_query: str) -> list[bytes]:  # noqa: C901
    """Execute search query. If single folder, use standard search. If multiple, use hybrid ESEARCH/fallback."""
    folders = getattr(account, "_folders", ["INBOX"])
    search_cache = _get_search_cache(account)

    if len(folders) <= 1:
        folder = folders[0] if folders else "INBOX"
        cache_key = (folder, search_query)
        if cache_key in search_cache:
            return search_cache[cache_key]
        res = await account.search(search_query, charset=None)
        result: list[bytes] = []
        if res.result == "OK" and res.lines:
            result = parse_search_response(res.lines)
        search_cache[cache_key] = result
        return result

    all_uids: list[bytes] = []

    # Check for MULTISEARCH capability safely (handling mock/AsyncMock in tests)
    is_multisearch = False
    if hasattr(account, "has_capability"):
        try:
            res = account.has_capability("MULTISEARCH")
            if asyncio.iscoroutine(res):
                res.close()
                is_multisearch = False
            else:
                is_multisearch = bool(res)
        except Exception:  # noqa: BLE001
            pass

    if is_multisearch:
        # ESEARCH IN ("folder1" "folder2") query - cache under a combined key
        cache_key = (tuple(folders), search_query)
        if cache_key in search_cache:
            return search_cache[cache_key]
        folder_list = " ".join([quote_folder(encode_imap_utf7(f)) for f in folders])
        args = ("IN", f"({folder_list})", search_query)
        try:
            timeout = getattr(account, "timeout", None)
            if not isinstance(timeout, (int, float)):
                timeout = None
            res = await account.protocol.execute(
                Command(
                    "ESEARCH",
                    account.protocol.new_tag(),
                    *args,
                    loop=account.protocol.loop,
                    timeout=timeout,
                )
            )
            if res.result == "OK":
                for line in res.lines:
                    if line:
                        all_uids.extend(_parse_esearch_line(line))
        except TimeoutError:
            raise
        except (AioImapException, OSError) as err:
            _LOGGER.error("Error executing ESEARCH: %s", err)
        search_cache[cache_key] = all_uids
    else:
        # Sequential select and search fallback - cache per (folder, query)
        for folder in folders:
            cache_key = (folder, search_query)
            if cache_key in search_cache:
                all_uids.extend(search_cache[cache_key])
                continue
            select_ok = await selectfolder(account, folder)
            if not select_ok:
                search_cache[cache_key] = []
                continue
            try:
                res = await account.uid_search(search_query, charset=None)
                if res.result == "OK" and res.lines:
                    parsed = parse_search_response(res.lines)
                    folder_uids = [
                        f"{folder}/{uid.decode()}".encode() for uid in parsed
                    ]
                else:
                    folder_uids = []
            except TimeoutError:
                raise
            except (AioImapException, OSError) as err:
                _LOGGER.error("Error searching folder %s: %s", folder, err)
                folder_uids = []
            search_cache[cache_key] = folder_uids
            all_uids.extend(folder_uids)

    return all_uids


IMAP_COMMAND_PACING = 0.1
"""Delay between successive IMAP commands on one connection during batch pre-fetch.

Verified NOT to be the root cause of the stall below (a live test with this
pacing active stalled at the identical command position as without it), but
left in place as cheap insurance against separate rate-based throttling.
"""

IMAP_COMMAND_TIMEOUT = 10
"""Per-command timeout during batch pre-fetch, before assuming a stall.

Live diagnostics against Exchange Online / outlook.office365.com showed a
connection silently stops responding to further commands after a certain
number have been issued, regardless of pacing between them (ruling out a
time-based rate limit). This bounds each individual SELECT/SEARCH/FETCH and
triggers a reconnect-and-retry instead of hanging for the whole scan budget.
"""

FETCH_CHUNK_SIZE = 200
"""Max UIDs per batched header FETCH, purely as a safety cap on command size.

Not a throughput lever like the old per-query design -- one broad SEARCH plus
a handful of these chunked FETCHes replaces what used to be one SEARCH per
sensor query (see HANDOFF.md section 2 for why that didn't scale).
"""

_FETCH_BOUNDARY_RE = re.compile(rb"^\d+ FETCH \(")
_UID_RE = re.compile(rb"UID (\d+)")
_INTERNALDATE_RE = re.compile(rb'INTERNALDATE "([^"]+)"')


def _parse_date_prefix(date_str: str) -> datetime.date | None:
    """Parse the DD-Mon-YYYY prefix of an IMAP date string into a date object."""
    try:
        return datetime.datetime.strptime(date_str[:11], "%d-%b-%Y").date()
    except (ValueError, TypeError):
        return None


def _decode_mime_header(value: str) -> str:
    """Decode a possibly MIME-encoded (RFC 2047) header value to plain text."""
    if not value:
        return ""
    decoded = []
    for part_bytes, encoding in decode_header(value):
        if isinstance(part_bytes, bytes):
            try:
                decoded.append(part_bytes.decode(encoding or "utf-8", "ignore"))
            except (LookupError, UnicodeError):
                decoded.append(part_bytes.decode("utf-8", "ignore"))
        else:
            decoded.append(part_bytes)
    return "".join(decoded)


@dataclass
class _FetchRecord:
    """One message's classification-relevant fields, decoded and ready to match."""

    from_header: str
    subject: str
    header_values: dict[str, str]
    internal_date: datetime.date | None


def _parse_fetch_records(lines: list) -> dict[bytes, _FetchRecord]:
    """Parse a batched UID FETCH response into {uid: _FetchRecord}.

    Each message's response starts with a line like `<seq> FETCH (UID <uid>
    INTERNALDATE "..." BODY[HEADER.FIELDS (...)] {N}` followed by the raw
    header bytes and a closing `)`. email.message_from_bytes() tolerates the
    boundary/closing lines mixed in (they just yield no recognizable headers),
    so this only needs to track which UID the in-between bytes belong to.
    """
    records: dict[bytes, _FetchRecord] = {}
    current_uid: bytes | None = None
    current_date: datetime.date | None = None
    buffer: list[bytes] = []

    def flush() -> None:
        if current_uid is not None:
            msg = email.message_from_bytes(b"".join(buffer))
            from_val = _decode_mime_header(msg.get("from") or "")
            subject_val = _decode_mime_header(msg.get("subject") or "")
            header_values = {
                name.lower(): _decode_mime_header(value)
                for name, value in msg.items()
                if name.lower() not in ("from", "subject")
            }
            records[current_uid] = _FetchRecord(
                from_val, subject_val, header_values, current_date
            )

    for line in lines:
        if not isinstance(line, (bytes, bytearray)):
            continue
        line = bytes(line)
        if _FETCH_BOUNDARY_RE.match(line):
            flush()
            uid_match = _UID_RE.search(line)
            current_uid = uid_match.group(1) if uid_match else None
            date_match = _INTERNALDATE_RE.search(line)
            current_date = (
                _parse_date_prefix(date_match.group(1).decode()) if date_match else None
            )
            buffer = []
        else:
            buffer.append(line)
    flush()
    return records


def _query_matches_record(spec: QuerySpec, record: _FetchRecord) -> bool:
    """Check whether one fetched message matches one query's criteria.

    Mirrors build_search()'s FROM/HEADER/SUBJECT/SINCE semantics (all
    case-insensitive substring matches, SINCE by day granularity) so
    classifying client-side produces the same matches the original per-query
    SEARCH would have.
    """
    since = _parse_date_prefix(spec.since_date)
    if since and record.internal_date and record.internal_date < since:
        return False

    from_lower = record.from_header.lower()
    header_lower = (
        record.header_values.get(spec.header.lower(), "").lower() if spec.header else ""
    )
    addr_match = any(
        addr.lower() in from_lower or (spec.header and addr.lower() in header_lower)
        for addr in spec.addresses
    )
    if not addr_match:
        return False

    if not spec.subjects:
        return True
    subject_lower = record.subject.lower()
    return any(s.lower() in subject_lower for s in spec.subjects)


async def _fetch_and_classify(
    account: IMAP4_SSL,
    folder: str,
    uids: list[bytes],
    pending: list[QuerySpec],
    search_cache: dict,
) -> IMAP4_SSL:
    """FETCH headers for `uids` in chunks and classify them against `pending`.

    Populates search_cache[(folder, spec.query)] for every spec in `pending`.
    """
    header_names = sorted({spec.header for spec in pending if spec.header})
    fetch_fields = "FROM SUBJECT" + (
        " " + " ".join(header_names) if header_names else ""
    )
    parts = f"(INTERNALDATE BODY[HEADER.FIELDS ({fetch_fields})])"

    records: dict[bytes, tuple[str, str, datetime.date | None]] = {}
    for i in range(0, len(uids), FETCH_CHUNK_SIZE):
        chunk = uids[i : i + FETCH_CHUNK_SIZE]
        uid_list_str = ",".join(
            uid.decode() if isinstance(uid, bytes) else str(uid) for uid in chunk
        )
        await asyncio.sleep(IMAP_COMMAND_PACING)
        try:
            try:
                async with asyncio.timeout(IMAP_COMMAND_TIMEOUT):
                    res = await account.uid("FETCH", uid_list_str, parts)
            except TimeoutError:
                account = await _reconnect(account)
                select_ok, account = await _select_with_reconnect(account, folder)
                if not select_ok:
                    continue
                async with asyncio.timeout(IMAP_COMMAND_TIMEOUT):
                    res = await account.uid("FETCH", uid_list_str, parts)

            if res.result == "OK" and res.lines:
                records.update(_parse_fetch_records(res.lines))
        except TimeoutError:
            raise
        except (AioImapException, OSError) as err:
            _LOGGER.debug("Batch pre-fetch FETCH error (%s): %s", folder, err)

    for spec in pending:
        matched_uids = [
            uid
            for uid, record in records.items()
            if _query_matches_record(spec, record)
        ]
        if matched_uids:
            _LOGGER.debug(
                "Batch pre-fetch: folder %s classified %d match(es) for query %s: %s",
                folder,
                len(matched_uids),
                spec.query,
                [
                    (
                        uid.decode(),
                        records[uid].from_header,
                        records[uid].subject,
                        records[uid].internal_date,
                    )
                    for uid in matched_uids
                ],
            )
        search_cache[(folder, spec.query)] = [
            f"{folder}/{uid.decode()}".encode() for uid in matched_uids
        ]

    return account


async def _batch_search_single_folder(
    account: IMAP4_SSL,
    folder: str,
    pending: list[QuerySpec],
    search_cache: dict,
) -> IMAP4_SSL:
    """Classify the already-selected single folder against all pending queries."""
    since_dates = [d for spec in pending if (d := _parse_date_prefix(spec.since_date))]
    since_str = min(since_dates).strftime("%d-%b-%Y") if since_dates else None
    search_query = f"SINCE {since_str}" if since_str else "ALL"

    try:
        res = await account.search(search_query, charset=None)
        uids = (
            parse_search_response(res.lines) if res.result == "OK" and res.lines else []
        )
    except TimeoutError:
        raise
    except (AioImapException, OSError) as err:
        _LOGGER.debug("Batch pre-fetch broad search error (single folder): %s", err)
        uids = []

    if not uids:
        for spec in pending:
            search_cache[(folder, spec.query)] = []
        return account

    return await _fetch_and_classify(account, folder, uids, pending, search_cache)


async def _reconnect(account: IMAP4_SSL) -> IMAP4_SSL:
    """Close a stalled connection and open a fresh one for the same mailbox.

    Preserves the folder list and accumulated search cache across the
    reconnect. Requires _login_kwargs/_hass to have been stashed on the
    account by the caller at initial login time.
    """
    login_kwargs = getattr(account, "_login_kwargs", None)
    if not login_kwargs:
        raise AioImapException("Cannot reconnect: no stored login parameters")
    hass = getattr(account, "_hass", None)
    folders = getattr(account, "_folders", ["INBOX"])
    search_cache = getattr(account, "_search_cache", {})

    _LOGGER.warning(
        "Batch pre-fetch: IMAP connection stalled past %ss, reconnecting",
        IMAP_COMMAND_TIMEOUT,
    )
    await logout(account)
    new_account = await login(hass, **login_kwargs)
    new_account._folders = folders  # noqa: SLF001
    new_account._search_cache = search_cache  # noqa: SLF001
    new_account._login_kwargs = login_kwargs  # noqa: SLF001
    new_account._hass = hass  # noqa: SLF001
    new_account._current_folder = None  # noqa: SLF001
    return new_account


async def _select_with_reconnect(
    account: IMAP4_SSL, folder: str
) -> tuple[bool, IMAP4_SSL]:
    """SELECT a folder, reconnecting once and retrying if it stalls."""
    try:
        async with asyncio.timeout(IMAP_COMMAND_TIMEOUT):
            return await selectfolder(account, folder), account
    except TimeoutError:
        account = await _reconnect(account)
        async with asyncio.timeout(IMAP_COMMAND_TIMEOUT):
            return await selectfolder(account, folder), account


async def _batch_search_one_folder(
    account: IMAP4_SSL,
    folder: str,
    pending: list[QuerySpec],
    search_cache: dict,
) -> IMAP4_SSL:
    """SELECT one folder, then classify it against all pending queries.

    Replaces one SEARCH per query with one broad SEARCH (SINCE the earliest
    date any pending query needs) plus a handful of batched header FETCHes,
    classified client-side per query -- see HANDOFF.md section 2 for why
    per-query SEARCHes don't scale on this provider. May reconnect the IMAP
    connection if a command stalls (see IMAP_COMMAND_TIMEOUT) -- callers must
    use the returned account for anything afterward.
    """
    _LOGGER.debug("Batch pre-fetch: SELECT folder %s", folder)
    select_ok, account = await _select_with_reconnect(account, folder)
    if not select_ok:
        for spec in pending:
            search_cache[(folder, spec.query)] = []
        return account

    since_dates = [d for spec in pending if (d := _parse_date_prefix(spec.since_date))]
    since_str = min(since_dates).strftime("%d-%b-%Y") if since_dates else None
    search_query = f"SINCE {since_str}" if since_str else "ALL"
    _LOGGER.debug(
        "Batch pre-fetch: folder %s broad search (%d quer%s) %s",
        folder,
        len(pending),
        "y" if len(pending) == 1 else "ies",
        search_query,
    )

    try:
        try:
            async with asyncio.timeout(IMAP_COMMAND_TIMEOUT):
                res = await account.uid_search(search_query, charset=None)
        except TimeoutError:
            account = await _reconnect(account)
            select_ok, account = await _select_with_reconnect(account, folder)
            if not select_ok:
                for spec in pending:
                    search_cache[(folder, spec.query)] = []
                return account
            async with asyncio.timeout(IMAP_COMMAND_TIMEOUT):
                res = await account.uid_search(search_query, charset=None)

        uids = (
            parse_search_response(res.lines) if res.result == "OK" and res.lines else []
        )
    except TimeoutError:
        raise
    except (AioImapException, OSError) as err:
        _LOGGER.debug("Batch pre-fetch broad search error (%s): %s", folder, err)
        uids = []

    if not uids:
        for spec in pending:
            search_cache[(folder, spec.query)] = []
        return account

    return await _fetch_and_classify(account, folder, uids, pending, search_cache)


async def batch_search_folders(
    account: IMAP4_SSL, queries: list[QuerySpec]
) -> IMAP4_SSL:
    """Pre-populate the search cache: SELECT each folder once, classify once.

    This inverts the normal per-sensor → per-folder loop so that each folder
    needs one broad SEARCH plus a few FETCHes for the entire scan, instead of
    one SEARCH per sensor query. Results are stored in the search cache and
    subsequent email_search / _execute_single_search calls return immediately
    from cache using the same query string build_search() would produce.

    Returns the account to use for the rest of the scan -- it may be a new
    connection object if a stalled command forced a reconnect.
    """
    if not queries:
        return account
    folders = getattr(account, "_folders", ["INBOX"])
    search_cache = _get_search_cache(account)
    unique_specs: dict[str, QuerySpec] = {}
    for spec in queries:
        unique_specs.setdefault(spec.query, spec)
    unique_queries = list(unique_specs.values())

    if len(folders) <= 1:
        folder = folders[0] if folders else "INBOX"
        pending = [s for s in unique_queries if (folder, s.query) not in search_cache]
        if pending:
            account = await _batch_search_single_folder(
                account, folder, pending, search_cache
            )
        return account

    for folder in folders:
        pending = [s for s in unique_queries if (folder, s.query) not in search_cache]
        if not pending:
            continue
        t0 = asyncio.get_event_loop().time()
        account = await _batch_search_one_folder(account, folder, pending, search_cache)
        _LOGGER.debug(
            "Batch pre-fetch: folder %s — %d quer%s in %.1fs",
            folder,
            len(pending),
            "y" if len(pending) == 1 else "ies",
            asyncio.get_event_loop().time() - t0,
        )
    return account


async def email_search(  # noqa: C901
    account: IMAP4_SSL,
    address: list,
    date: str,
    subject: str | list[str] = "",
    header: str = "",
) -> tuple:
    """Search emails with from/header, subject, and date asynchronously.

    Always uses charset=None to avoid sending CHARSET in the IMAP SEARCH
    command, ensuring compatibility with servers like Microsoft Exchange
    that only support US-ASCII.

    When `header` is provided, searches via HEADER criterion instead of FROM,
    matching the original sender in forwarding-service headers.

    If multiple subjects are provided, they are searched in batches of 10
    to keep the search query length safe.
    """
    folders = getattr(account, "_folders", ["INBOX"])
    is_yahoo = False
    if hasattr(account, "host") and isinstance(account.host, str):
        host_lower = account.host.lower()
        is_yahoo = "yahoo" in host_lower or "aol" in host_lower

    if len(folders) <= 1:
        folder = folders[0] if folders else "INBOX"
        search_cache = _get_search_cache(account)

        if not isinstance(subject, list) or len(subject) <= 10:
            _unused, search = build_search(
                address, date, subject, header, is_yahoo=is_yahoo
            )
            cache_key = (folder, search)
            if cache_key in search_cache:
                parsed = search_cache[cache_key]
                return ("OK", [b" ".join(parsed)])
            try:
                res = await account.search(search, charset=None)
            except TimeoutError:
                raise
            except (AioImapException, OSError) as err:
                _LOGGER.error("Error searching emails: %s", err)
                return ("BAD", str(err))
            else:
                parsed = parse_search_response(res.lines)
                if res.result == "OK":
                    search_cache[cache_key] = parsed
                return (res.result, [b" ".join(parsed)])

        # Batch subjects in groups of 10
        all_matched_ids = []
        for i in range(0, len(subject), 10):
            batch = subject[i : i + 10]
            _unused, search = build_search(
                address, date, batch, header, is_yahoo=is_yahoo
            )
            cache_key = (folder, search)
            if cache_key in search_cache:
                all_matched_ids.extend(search_cache[cache_key])
                continue
            try:
                res = await account.search(search, charset=None)
                if res.result == "OK" and res.lines:
                    parsed = parse_search_response(res.lines)
                    search_cache[cache_key] = parsed
                    all_matched_ids.extend(parsed)
            except TimeoutError:
                raise
            except (AioImapException, OSError) as err:
                _LOGGER.error("Error searching emails batch: %s", err)

        # Deduplicate and return in same format as individual search
        unique_ids = list(dict.fromkeys(all_matched_ids))
        return ("OK", [b" ".join(unique_ids)])

    # Multi-folder search logic
    if not isinstance(subject, list) or len(subject) <= 10:
        _unused, search = build_search(
            address, date, subject, header, is_yahoo=is_yahoo
        )
        try:
            uids = await _execute_single_search(account, search)
        except TimeoutError:
            raise
        except (AioImapException, OSError) as err:
            _LOGGER.error("Error searching emails: %s", err)
            return ("BAD", str(err))
        return ("OK", [b" ".join(uids)])

    # Batch subjects in groups of 10
    all_matched_ids = []
    for i in range(0, len(subject), 10):
        batch = subject[i : i + 10]
        _unused, search = build_search(address, date, batch, header, is_yahoo=is_yahoo)
        try:
            uids = await _execute_single_search(account, search)
            all_matched_ids.extend(uids)
        except TimeoutError:
            raise
        except (AioImapException, OSError) as err:
            _LOGGER.error("Error searching emails batch: %s", err)

    # Deduplicate and return in same format as individual search
    unique_ids = list(dict.fromkeys(all_matched_ids))
    return ("OK", [b" ".join(unique_ids)])


async def email_search_since(account: IMAP4_SSL, since_date: str) -> list[bytes]:
    """Search all emails since since_date with no sender or subject filter.

    Returns a list of email UIDs as bytes.
    """
    search_query = f"(SINCE {since_date})"
    _LOGGER.debug("Universal search query: %s", search_query)
    return await _execute_single_search(account, search_query)


async def email_fetch(account: IMAP4_SSL, num, parts: str = "(RFC822)") -> tuple:
    """Download specified email for parsing asynchronously."""
    if account.host == "imap.mail.me.com":
        parts = "BODY[]"

    num_str = num.decode() if isinstance(num, bytes) else str(num)
    if "/" in num_str:
        folder, num_str = num_str.rsplit("/", 1)
        await selectfolder(account, folder)
        try:
            res = await account.uid("FETCH", num_str, parts)
        except TimeoutError:
            raise
        except (AioImapException, OSError) as err:
            _LOGGER.error("Error fetching email %s: %s", num_str, err)
            return ("BAD", str(err))
        else:
            return (res.result, res.lines)

    try:
        res = await account.fetch(num_str, parts)
    except TimeoutError:
        raise
    except (AioImapException, OSError) as err:
        _LOGGER.error("Error fetching email %s: %s", num_str, err)
        return ("BAD", str(err))
    else:
        return (res.result, res.lines)


async def email_fetch_headers(account: IMAP4_SSL, num) -> tuple:
    """Download only the subject header of an email asynchronously."""
    num_str = num.decode() if isinstance(num, bytes) else str(num)
    if "/" in num_str:
        folder, num_str = num_str.rsplit("/", 1)
        await selectfolder(account, folder)
        try:
            res = await account.uid("FETCH", num_str, "(BODY[HEADER.FIELDS (SUBJECT)])")
        except TimeoutError:
            raise
        except (AioImapException, OSError) as err:
            _LOGGER.error("Error fetching email headers %s: %s", num_str, err)
            return ("BAD", str(err))
        else:
            return (res.result, res.lines)

    try:
        res = await account.fetch(num_str, "(BODY[HEADER.FIELDS (SUBJECT)])")
    except TimeoutError:
        raise
    except (AioImapException, OSError) as err:
        _LOGGER.error("Error fetching email headers %s: %s", num_str, err)
        return ("BAD", str(err))
    else:
        return (res.result, res.lines)


async def email_fetch_text(account: IMAP4_SSL, num, parts: str = "(BODY[1])") -> tuple:
    """Download the specific part of the email body asynchronously."""
    if account.host == "imap.mail.me.com":
        parts = "BODY[]"

    num_str = num.decode() if isinstance(num, bytes) else str(num)
    if "/" in num_str:
        folder, num_str = num_str.rsplit("/", 1)
        await selectfolder(account, folder)
        try:
            res = await account.uid("FETCH", num_str, parts)
        except TimeoutError:
            raise
        except (AioImapException, OSError) as err:
            _LOGGER.error("Error fetching email text %s: %s", num_str, err)
            return ("BAD", str(err))
        else:
            return (res.result, res.lines)

    try:
        res = await account.fetch(num_str, parts)
    except TimeoutError:
        raise
    except (AioImapException, OSError) as err:
        _LOGGER.error("Error fetching email text %s: %s", num_str, err)
        return ("BAD", str(err))
    else:
        return (res.result, res.lines)


async def email_fetch_batch(  # noqa: C901
    account: IMAP4_SSL, nums: list[str | bytes], parts: str = "(RFC822)"
) -> tuple:
    """Download specified emails for parsing asynchronously in a batch."""
    if not nums:
        return ("OK", [])

    if account.host == "imap.mail.me.com":
        parts = "BODY[]"

    # Check if any ID contains a folder prefix
    has_folder_prefix = False
    for num in nums:
        num_str = num.decode() if isinstance(num, bytes) else str(num)
        if "/" in num_str:
            has_folder_prefix = True
            break

    if not has_folder_prefix:
        num_strs = [
            num.decode() if isinstance(num, bytes) else str(num) for num in nums
        ]
        num_list_str = ",".join(num_strs)
        try:
            res = await account.fetch(num_list_str, parts)
        except TimeoutError:
            raise
        except (AioImapException, OSError) as err:
            _LOGGER.error("Error fetching emails batch %s: %s", num_list_str, err)
            return ("BAD", str(err))
        else:
            return (res.result, res.lines)

    # Group nums by their folder prefix
    folder_to_nums = {}
    for num in nums:
        num_str = num.decode() if isinstance(num, bytes) else str(num)
        if "/" in num_str:
            folder, actual_num = num_str.rsplit("/", 1)
        else:
            folder, actual_num = None, num_str
        folder_to_nums.setdefault(folder, []).append(actual_num)

    all_results = []
    overall_result = "OK"

    for folder, folder_nums in folder_to_nums.items():
        if folder is not None:
            await selectfolder(account, folder)

        num_list_str = ",".join(folder_nums)
        try:
            res = await account.uid("FETCH", num_list_str, parts)
            if res.result != "OK":
                overall_result = res.result
            all_results.extend(res.lines)
        except TimeoutError:
            raise
        except (AioImapException, OSError) as err:
            _LOGGER.error("Error fetching emails batch %s: %s", num_list_str, err)
            return ("BAD", str(err))

    return (overall_result, all_results)


LOGOUT_TIMEOUT = 5
"""Cap on the LOGOUT round-trip during cleanup.

Deliberately independent of the account's own command timeout (which mirrors
the scan-wide time budget): if a command hung long enough for the caller to
give up and cancel, the same connection's LOGOUT is equally likely to hang.
Without this cap, cleanup after a timed-out scan could itself stall for the
full scan budget again, doubling the time until the failure is reported.
"""


async def logout(account: IMAP4_SSL | IMAP4) -> None:
    """Logout from IMAP server asynchronously."""
    try:
        async with asyncio.timeout(LOGOUT_TIMEOUT):
            await account.logout()
    except (TimeoutError, AioImapException, OSError, asyncio.CancelledError) as err:
        _LOGGER.debug("Error logging out of IMAP Server: %s", err)
