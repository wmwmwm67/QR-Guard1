import sqlite3
from datetime import datetime
import io

import streamlit as st
import qrcode

DB_PATH = "qrguard.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            tag_id TEXT PRIMARY KEY,
            owner_contact TEXT NOT NULL,
            owner_note TEXT,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_id TEXT NOT NULL,
            finder_name TEXT,
            message_text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(tag_id) REFERENCES tags(tag_id)
        )
    """)
    conn.commit()
    conn.close()

def upsert_tag(tag_id: str, contact: str, note: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tags(tag_id, owner_contact, owner_note, created_at)
        VALUES(?,?,?,?)
        ON CONFLICT(tag_id) DO UPDATE SET
            owner_contact=excluded.owner_contact,
            owner_note=excluded.owner_note
    """, (tag_id, contact, note, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_tag(tag_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT tag_id, owner_contact, owner_note, created_at FROM tags WHERE tag_id=?", (tag_id,))
    row = cur.fetchone()
    conn.close()
    return row

def add_message(tag_id: str, finder_name: str, text: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO messages(tag_id, finder_name, message_text, created_at)
        VALUES(?,?,?,?)
    """, (tag_id, finder_name, text, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def list_messages(tag_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT finder_name, message_text, created_at
        FROM messages
        WHERE tag_id=?
        ORDER BY id DESC
        LIMIT 20
    """, (tag_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def make_qr_png_bytes(url: str) -> bytes:
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ---------------- App ----------------
st.set_page_config(page_title="QR-Guard", page_icon="🔷", layout="centered")
init_db()

st.title("🔷 QR-Guard Prototype (Python)")

tab_register, tab_found = st.tabs(["🧾 Owner: Register Tag", "🔍 Finder: Found Item"])

with tab_register:
    st.subheader("Register your QR-Guard Tag")
    st.caption("This is a demo. In a real system, the owner contact stays hidden from the finder.")

    tag_id = st.text_input("Tag ID (printed on tag)", placeholder="e.g., ABX239").strip().upper()
    contact = st.text_input("Owner contact (email or phone)", placeholder="e.g., alex@email.com or 9xxxxxxx").strip()
    note = st.text_area("Optional note to finder", placeholder="e.g., Please message here, thank you!", height=90).strip()

    if st.button("Register / Update Tag"):
        if not tag_id:
            st.error("Please enter Tag ID.")
        elif not contact:
            st.error("Please enter owner contact.")
        else:
            upsert_tag(tag_id, contact, note)
            st.success(f"Registered tag: {tag_id}")

            # This is the link you'd encode in a QR code.
            # For local demo it uses localhost. For real use, replace with your deployed URL.
       scan_url = f"{st.get_url()}?tag={tag_id}"

            st.write("**Scan URL (put this into a QR code):**")
            st.code(scan_url)

            qr_bytes = make_qr_png_bytes(scan_url)
            st.image(qr_bytes, caption="Generated QR code (demo)")
            st.download_button(
                "Download QR code PNG",
                data=qr_bytes,
                file_name=f"QR-Guard_{tag_id}.png",
                mime="image/png"
            )

with tab_found:
    st.subheader("Found an item? Scan & message the owner")
    st.caption("Finder can message anonymously. Owner contact is not shown here.")

    # Allow auto-fill if scanned link contains ?tag=ABX239
    scanned_tag = st.query_params.get("tag", "")
    tag = st.text_input("Tag ID", value=scanned_tag, placeholder="e.g., ABX239").strip().upper()

    if tag:
        record = get_tag(tag)
        if not record:
            st.warning("This tag is not registered yet.")
        else:
            _, _, owner_note, _ = record
            st.info(f"Tag **{tag}** is registered.")
            if owner_note:
                st.write(f"**Owner note:** {owner_note}")

            finder_name = st.text_input("Your name (optional)", placeholder="e.g., Sam").strip()
            msg = st.text_area("Message to owner", placeholder="e.g., I found your item at Bugis MRT. How can I return it?", height=110).strip()

            if st.button("Send Message"):
                if not msg:
                    st.error("Please type a message.")
                else:
                    add_message(tag, finder_name, msg)
                    st.success("Message sent (stored in database).")

            st.markdown("### Recent messages (demo log)")
            msgs = list_messages(tag)
            if not msgs:
                st.caption("No messages yet.")
            else:
                for name, text, at in msgs:
                    who = name if name else "Anonymous"
                    st.write(f"**{who}** • {at}")
                    st.write(text)
                    st.divider()
    else:
        st.caption("Enter a Tag ID, or scan a QR that links to this app with ?tag=XXXX")
