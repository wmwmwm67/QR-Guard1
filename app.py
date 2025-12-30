import streamlit as st
import sqlite3
import qrcode
import io
from datetime import datetime

# =========================
# CONFIG
# =========================
APP_BASE_URL = "https://qr-guard1-42dkbzqoeonc2qm6aczxbu.streamlit.app"
DB_PATH = "qrguard.db"

# =========================
# DATABASE
# =========================
def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            tag_id TEXT PRIMARY KEY,
            contact TEXT,
            note TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_id TEXT,
            message TEXT,
            time TEXT
        )
    """)
    conn.commit()

def upsert_tag(tag_id, contact, note):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO tags (tag_id, contact, note)
        VALUES (?, ?, ?)
        ON CONFLICT(tag_id) DO UPDATE SET
        contact=excluded.contact,
        note=excluded.note
    """, (tag_id, contact, note))
    conn.commit()

def get_tag(tag_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT contact, note FROM tags WHERE tag_id=?", (tag_id,))
    return c.fetchone()

def save_message(tag_id, message):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (tag_id, message, time) VALUES (?, ?, ?)",
        (tag_id, message, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()

# =========================
# QR CODE
# =========================
def make_qr_png(url):
    qr = qrcode.make(url)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return buf.getvalue()

# =========================
# APP START
# =========================
st.set_page_config(page_title="QR-Guard", page_icon="🔐")
init_db()

query_params = st.experimental_get_query_params()
tag_from_qr = query_params.get("tag", [None])[0]

tab_owner, tab_finder = st.tabs(["📄 Owner: Register Tag", "🔍 Finder: Found Item"])

# =========================
# OWNER TAB
# =========================
with tab_owner:
    st.header("Register your QR-Guard Tag")
    st.caption("This is a demo. Owner contact stays hidden from finder.")

    tag_id = st.text_input("Tag ID (printed on tag)", placeholder="e.g. QR001")
    contact = st.text_input("Owner contact (email or phone)")
    note = st.text_area("Optional note to finder")

    if st.button("Register / Update Tag"):
        if tag_id and contact:
            upsert_tag(tag_id.strip(), contact.strip(), note.strip())
            st.success(f"Registered tag: {tag_id}")

            scan_url = f"{APP_BASE_URL}/?tag={tag_id}"
            st.write("**Scan URL (encode this into the QR):**")
            st.code(scan_url)

            qr_bytes = make_qr_png(scan_url)
            st.image(qr_bytes, caption="Generated QR code")
            st.download_button(
                "Download QR code PNG",
                data=qr_bytes,
                file_name=f"QR-Guard_{tag_id}.png",
                mime="image/png"
            )
        else:
            st.error("Please enter Tag ID and contact.")

# =========================
# FINDER TAB
# =========================
with tab_finder:
    st.header("Found a QR-Guard Item")

    tag_id_finder = st.text_input(
        "Tag ID",
        value=tag_from_qr if tag_from_qr else "",
        disabled=bool(tag_from_qr)
    )

    message = st.text_area("Message to owner", placeholder="I found your item at ...")

    if st.button("Send Message"):
        tag = get_tag(tag_id_finder)
        if tag:
            save_message(tag_id_finder, message)
            st.success("Message sent to owner anonymously.")
        else:
            st.error("Tag not found.")
