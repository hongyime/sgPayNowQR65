#!/usr/bin/env python3
import os
import io
import pickle
import signal
import logging
import datetime
import argparse
from pathlib import Path
from tqdm import tqdm
import qrcode
from PIL import Image

from download_path_manager import prompt_for_download_path

# ----------------------------
# CONFIG (edit as needed)
# ----------------------------
START_PHONE_NUM = 80000000
END_PHONE_NUM   = 99999999
CHECKPOINT_FILENAME = "checkpoint.pkl"
LOG_FILENAME        = "qr_generator.log"
CHECKPOINT_INTERVAL =  10      # save remaining list after every N processed
QR_FILL_RGB         = (144, 19, 123)  # same as your original
QR_BACK_COLOR       = "white"
LOGO_FILENAME       = "paynow_logo.png"  # optional; sits next to script

# ----------------------------
# GLOBALS
# ----------------------------
STOP_REQUESTED = False

# ----------------------------
# LOGGING
# ----------------------------
def setup_logging():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(script_dir, LOG_FILENAME)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filename=log_path,
        filemode="a",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logging.getLogger().addHandler(console)
    logging.info(f"Logging initialized. Log file: {log_path}")

# ----------------------------
# SIGNAL HANDLER
# ----------------------------
def signal_handler(sig, frame):
    global STOP_REQUESTED
    STOP_REQUESTED = True
    logging.warning("Stop requested (Ctrl+C). Will save checkpoint and exit soon...")

signal.signal(signal.SIGINT, signal_handler)

# ----------------------------
# EMV PAYLOAD HELPERS
# ----------------------------
def get_info_string(info):
    """Recursively translate QR dictionary payload into string format."""
    final_string = ""
    for key, value in info.items():
        if isinstance(value, dict):
            temp_len, temp_val = get_info_string(value)
            final_string += key + temp_len + temp_val
        else:
            final_string += key + str(len(value)).zfill(2) + value
    return str(len(final_string)).zfill(2), final_string

def crc16_ccitt(data):
    """Compute CRC-16-CCITT checksum."""
    crc = 0xFFFF
    msb = crc >> 8
    lsb = crc & 255
    for c in data:
        x = ord(c) ^ msb
        x ^= (x >> 4)
        msb = (lsb ^ (x >> 3) ^ (x << 4)) & 255
        lsb = (x ^ (x << 5)) & 255
    return (msb << 8) + lsb

# ----------------------------
# I/O HELPERS
# ----------------------------
def load_logo_bytes():
    """Load optional logo from script directory; return bytes or None."""
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOGO_FILENAME)
    if not os.path.exists(logo_path):
        logging.warning(f"Logo not found at {logo_path}. Proceeding without logo.")
        return None
    try:
        with open(logo_path, "rb") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to load logo: {e}")
        return None

def safe_save(img, filepath):
    """Write via temp file then atomic replace to avoid corruption."""
    tmp = filepath + ".png"
    img.save(tmp)
    os.replace(tmp, filepath)

def save_checkpoint(remaining):
    """Pickle the remaining list to checkpoint file."""
    with open(CHECKPOINT_FILENAME, "wb") as f:
        pickle.dump(remaining, f)
    logging.info(f"Checkpoint saved with {len(remaining)} numbers remaining.")

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILENAME):
        try:
            with open(CHECKPOINT_FILENAME, "rb") as f:
                data = pickle.load(f)
            if isinstance(data, (list, set, tuple)):
                remaining = set(int(x) for x in data)
                logging.info(f"Loaded checkpoint with {len(remaining)} pending numbers.")
                return remaining
        except Exception as e:
            logging.error(f"Failed to load checkpoint: {e}")
    return None

# ----------------------------
# QR GENERATION
# ----------------------------
def generate_paynow_qr(proxy_value, amount, expiry, bill_number, out_path, logo_bytes=None):
    """
    Build EMV payload and generate QR image (+ optional center logo).
    proxy_value example: '+65########'
    amount as string, expiry 'YYYYMMDD'
    """
    info = {
        "00": "01",
        "01": "12",  # point_of_initiation
        "26": {
            "00": "SG.PAYNOW",
            "01": "0",              # proxy type: mobile
            "02": proxy_value,      # proxy value: '+65########'
            "03": "1",              # editable
            "04": expiry,
        },
        "52": "0000",
        "53": "702",
        "54": str(amount),
        "58": "SG",
        "59": "NA",
        "60": "Singapore",
        "62": {"01": bill_number},
    }
    payload = get_info_string(info)[1]
    payload += "6304"
    crc_value = "{:04X}".format(crc16_ccitt(payload))
    payload += crc_value

    qr = qrcode.QRCode(
        version=1,
        box_size=5,
        border=4,
        error_correction=qrcode.constants.ERROR_CORRECT_H
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color=QR_FILL_RGB, back_color=QR_BACK_COLOR).convert("RGB")

    if logo_bytes:
        try:
            logo = Image.open(io.BytesIO(logo_bytes))
            basewidth = 85
            wpercent = basewidth / float(logo.size[0])
            hsize = int(float(logo.size[1]) * wpercent)
            logo = logo.resize((basewidth, hsize), Image.Resampling.LANCZOS)
            pos = ((img.size[0] - logo.size[0]) // 2, (img.size[1] - logo.size[1]) // 2)
            img.paste(logo, pos)
        except Exception as e:
            logging.error(f"Failed to paste logo: {e}")

    filename = os.path.join(out_path, f"{proxy_value}.png")
    safe_save(img, filename)
    return filename

# ----------------------------
# MAIN
# ----------------------------
def main():
    global START_PHONE_NUM, END_PHONE_NUM, CHECKPOINT_FILENAME, LOG_FILENAME, CHECKPOINT_INTERVAL, LOGO_FILENAME

    parser = argparse.ArgumentParser(description="Generate PayNow QR codes.")
    parser.add_argument("--start", type=int, default=START_PHONE_NUM, help="Start phone number")
    parser.add_argument("--end", type=int, default=END_PHONE_NUM, help="End phone number")
    parser.add_argument("--checkpoint", type=str, default=CHECKPOINT_FILENAME, help="Checkpoint filename")
    parser.add_argument("--log", type=str, default=LOG_FILENAME, help="Log filename")
    parser.add_argument("--interval", type=int, default=CHECKPOINT_INTERVAL, help="Checkpoint interval")
    parser.add_argument("--logo", type=str, default=LOGO_FILENAME, help="Logo filename")
    
    args = parser.parse_args()

    START_PHONE_NUM = args.start
    END_PHONE_NUM = args.end
    CHECKPOINT_FILENAME = args.checkpoint
    LOG_FILENAME = args.log
    CHECKPOINT_INTERVAL = args.interval
    LOGO_FILENAME = args.logo

    setup_logging()
    logo_bytes = load_logo_bytes()

    # Use unified path manager for save location
    out_dir = prompt_for_download_path(
        context="PayNow QR codes",
        out_path=None
    )
    os.makedirs(out_dir, exist_ok=True)

    # 1) Load checkpoint if present, else build remaining from range minus existing files
    remaining = load_checkpoint()
    if remaining is None:
        remaining = set(range(START_PHONE_NUM, END_PHONE_NUM + 1))
    elif not remaining:
        logging.info("Nothing to do. All requested QRs seem to be generated.")
        return

    processed_since_ckpt = 0
    expiry = (datetime.datetime.now() + datetime.timedelta(days=9999)).strftime("%Y%m%d")

    # 2) Iterate single-process with tqdm
    for num in tqdm(sorted(remaining), desc="Generating PayNow QRs"):
        if STOP_REQUESTED:
            break
        proxy_value = f"+65{num}"
        try:
            # Skip if file already exists (extra safety)
            out_path = os.path.join(out_dir, f"{proxy_value}.png")
            if os.path.exists(out_path):
                # Remove from remaining and continue
                remaining.discard(num)
                continue

            # Build and save QR
            generate_paynow_qr(
                proxy_value=proxy_value,
                amount="0.01",
                expiry=expiry,
                bill_number=f"sending to {proxy_value}",
                out_path=out_dir,
                logo_bytes=logo_bytes
            )
            logging.info(f"[OK] {proxy_value}")
            # Remove from remaining and maybe checkpoint
            remaining.discard(num)
            processed_since_ckpt += 1
            if processed_since_ckpt >= CHECKPOINT_INTERVAL:
                save_checkpoint(remaining)
                processed_since_ckpt = 0

        except Exception as e:
            logging.error(f"[FAILED] {proxy_value} -> {e}")
            # leave 'num' in remaining so it can be retried on next run

    # 3) Finalize: save or clean checkpoint
    if STOP_REQUESTED or remaining:
        save_checkpoint(remaining)
        logging.warning(f"Stopped/Unfinished. {len(remaining)} remaining. "
                        f"Re-run the script to resume.")
    else:
        # All done; remove checkpoint if exists
        if os.path.exists(CHECKPOINT_FILENAME):
            try:
                os.remove(CHECKPOINT_FILENAME)
            except Exception:
                pass
        logging.info("✅ All QRs generated successfully.")

if __name__ == "__main__":
    main()
