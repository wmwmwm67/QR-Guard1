import streamlit as st
import qrcode
import io
from datetime import datetime

APP_BASE_URL = "https://qr-guard1-42dkbzqoeonc2qm6aczxbu.streamlit.app"

def make_qr_png(url: str) -> bytes:
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

st.set_page_config(page_title="QR-Guard", page_icon="🔐", layout="centered")

# ---------------------------
# Demo "database" in memory
# ---------------------------
if "tags" not in st.session_state:
    st.session_state.tags = {}          # {tag_id: {"contact":..., "note":...}}
if "messages" not in st.session_state:
    st.session_state.messages = {}      # {tag_id: [{"time":..., "text":..., "from":...}, ...]}

# Read tag from QR link
tag_from_qr = st.query_params.get("tag", "")

st.title("🔐 QR-Guard (Cloud Demo)")

tab_owner, tab_finder = st.tabs(["📌 Owner: Register Tag", "🔍 Finder: Found Item"])

# ==========================
# OWNER TAB
# ==========================
with tab_owner:
    st.header("Register your QR-Guard Tag")
    st.caption("Demo version: messages are stored temporarily (good for presentation).")

    tag_id = st.text_input("Tag ID (printed on tag)", placeholder="e.g. QR001").strip().upper()
    contact = st.text_input("Owner contact (email or phone)", placeholder="e.g. 9xxxxxxx or name@email.com").strip()
    note = st.text_area("Optional note to finder", placeholder="e.g. Please message here, thank you!").strip()

    if st.button("Register / Update Tag"):
        if not tag_id:
            st.error("Please enter Tag ID.")
        elif not contact:
            st.error("Please enter owner contact.")
        else:
            st.session_state.tags[tag_id] = {"contact": contact, "note": note}
            st.success(f"Registered tag: {tag_id}")

            scan_url = f"{APP_BASE_URL}/?tag={tag_id}"
            st.write("**Scan URL (encode this into QR):**")
            st.code(scan_url)

            qr_bytes = make_qr_png(scan_url)
            st.image(qr_bytes, caption="Generated QR code")
            st.download_button(
                "Download QR code PNG",
                data=qr_bytes,
                file_name=f"QR-Guard_{tag_id}.png",
                mime="image/png"
            )

# ==========================
# FINDER TAB
# ==========================
with tab_finder:
    st.header("Found an item?")
    st.caption("Scan QR → this page opens → send message anonymously.")

    # If opened via QR link, auto-fill
    if tag_from_qr:
        tag_id_finder = st.text_input("Tag ID", value=tag_from_qr, disabled=True).strip().upper()
    else:
        tag_id_finder = st.text_input("Tag ID", placeholder="e.g. QR001").strip().upper()

    if not tag_id_finder:
        st.info("Enter a Tag ID (or scan a QR).")
    else:
        record = st.session_state.tags.get(tag_id_finder)
        if not record:
            st.error("Tag not registered yet.")
        else:
            if record.get("note"):
                st.write(f"**Owner note:** {record['note']}")

            finder_name = st.text_input("Your name (optional)", placeholder="e.g. Sam").strip()
            msg = st.text_area("Message to owner", placeholder="e.g. I found it at Bugis MRT.").strip()

            if st.button("Send Message"):
                if not msg:
                    st.error("Please type a message.")
                else:
                    st.session_state.messages.setdefault(tag_id_finder, [])
                    st.session_state.messages[tag_id_finder].append({
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "from": finder_name if finder_name else "Anonymous",
                        "text": msg
                    })
                    st.success("Message sent (demo).")

            st.divider()
            st.subheader("Recent messages (demo log)")
            msgs = st.session_state.messages.get(tag_id_finder, [])
            if not msgs:
                st.caption("No messages yet.")
            else:
                for m in reversed(msgs[-10:]):
                    st.write(f"**{m['from']}** • {m['time']}")
                    st.write(m["text"])
                    st.divider()
