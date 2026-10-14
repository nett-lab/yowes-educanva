"""
QRIS EMVCo Engine (Python Native)
Adopts the proven logic of hirotomasato/paygateme:
- Parses EMVCo TLV (Tag-Length-Value)
- Injects Tag 54 (Transaction Amount)
- Sets Tag 01 to '12' (Dynamic QRIS)
- Computes CRC16-CCITT checksum for Tag 63
"""

from __future__ import annotations
import io
import urllib.parse
from typing import Optional


def crc16_ccitt(data: str | bytes) -> str:
    """Computes CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, no reflect, no xorout).
    Mandated by Indonesia's QRIS (EMVCo) standard. Returns 4 uppercase hex digits.
    """
    if isinstance(data, str):
        raw_bytes = data.encode("utf-8")
    else:
        raw_bytes = data

    crc = 0xFFFF
    for byte in raw_bytes:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def parse_emv_tlv(payload: str) -> dict[str, str]:
    """Parses a flat EMVCo QRIS string into a dictionary of Tag -> Value."""
    raw = payload.encode("utf-8")
    cursor = 0
    tlv_map: dict[str, str] = {}

    while cursor < len(raw):
        if cursor + 4 > len(raw):
            break
        tag = raw[cursor : cursor + 2].decode("utf-8", errors="ignore")
        cursor += 2
        len_str = raw[cursor : cursor + 2].decode("utf-8", errors="ignore")
        cursor += 2

        if not len_str.isdigit():
            break
        length = int(len_str)
        if cursor + length > len(raw):
            break

        val = raw[cursor : cursor + length].decode("utf-8", errors="ignore")
        cursor += length
        tlv_map[tag] = val

    return tlv_map


def build_emv_tlv(tag: str, value: str) -> str:
    """Formats an EMVCo element as Tag (2 chars) + Length (2 chars) + Value."""
    val_bytes = value.encode("utf-8")
    return f"{tag}{len(val_bytes):02d}{value}"


def static_to_dynamic_qris(static_payload: str, amount: int) -> str:
    """Converts a static QRIS payload into a dynamic QRIS string carrying the specified amount.
    
    Steps (equivalent to paygateme qris/convert.go):
    1. Removes existing Tag 63 (CRC).
    2. Changes Tag 01 (Point of Initiation Method) from '11' (Static) to '12' (Dynamic).
    3. Injects Tag 54 (Transaction Amount).
    4. Recomputes CRC-16 and appends Tag 63.
    """
    if amount <= 0:
        raise ValueError("QRIS amount must be a positive integer")

    clean_payload = static_payload.strip()
    # Strip any trailing Tag 63 if present
    crc_index = clean_payload.rfind("6304")
    if crc_index != -1 and crc_index >= len(clean_payload) - 8:
        clean_payload = clean_payload[:crc_index]

    tlv = parse_emv_tlv(clean_payload)
    if "00" not in tlv:
        raise ValueError("Invalid QRIS payload: Tag 00 (Payload Format Indicator) missing")

    # Flip Tag 01 from static (11) to dynamic (12)
    tlv["01"] = "12"
    # Inject Tag 54 with whole rupiah amount
    tlv["54"] = str(amount)

    # Reconstruct in standard EMVCo tag order
    reconstructed_body = ""
    for tag in sorted(tlv.keys()):
        if tag == "63":
            continue
        reconstructed_body += build_emv_tlv(tag, tlv[tag])

    # Append Tag 63 header before computing CRC
    payload_to_sign = reconstructed_body + "6304"
    crc = crc16_ccitt(payload_to_sign)

    return payload_to_sign + crc


def get_qris_qr_image_url(qris_payload: str, size: int = 400) -> str:
    """Generates a reliable direct QR code image URL for Telegram bot sending
    without requiring external heavyweight libraries.
    """
    encoded = urllib.parse.quote(qris_payload)
    return f"https://quickchart.io/qr?text={encoded}&size={size}&margin=1"
