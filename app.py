import streamlit as st
import fal_client
import os
import base64
import re
from PIL import Image
import io
import glob
import requests
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Maxi Generator",
    page_icon="🦡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS (Styling, FONTS & GHOST MODE) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');

    /* 1. NUCLEAR FONT FIX */
    * {
        font-family: 'Inter', sans-serif !important;
    }
    input, textarea, [data-baseweb="select"], [data-testid="stMarkdownContainer"] p {
        font-family: 'Inter', sans-serif !important;
    }

    html, body, [class*="css"] {
        color: #ffffff;
        font-weight: 400;
    }
    
    label, .stMarkdown p, .stCaption, .limit-info {
        font-weight: 500 !important;
    }

    h1, h2, h3 {
        color: #fa660f !important;
        font-weight: 700 !important;
    }
    
    /* 2. GHOST MODE */
    [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
    [data-testid="stHeader"] {visibility: hidden !important; display: none !important;}
    [data-testid="stDecoration"] {visibility: hidden !important; display: none !important;}
    .stDeployButton {display:none !important;}
    [data-testid="stManageAppButton"] {display:none !important;}
    footer {visibility: hidden !important; display: none !important;}
    #MainMenu {visibility: hidden !important; display: none !important;}
    
    .block-container {
        padding-top: 1rem !important;
    }

    /* 3. BUTTONS */
    .stButton>button {
        background-color: #fa660f;
        color: white;
        border-radius: 8px;
        height: 3.5em;
        font-weight: bold !important;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #d9550a;
        color: white;
        transform: scale(1.02);
    }
    
    /* 4. IMAGES */
    .logo-container {
        max-width: 140px;
        width: 100%;
        margin-bottom: 15px;
    }
    .logo-container svg, .logo-container img {
        width: 100% !important;
        height: auto !important;
        display: block;
    }

    /* 5. RESULT IMAGE */
    .result-image-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 20px 0;
        width: 100%;
    }
    .result-image-container img {
        max-height: 650px !important; 
        max-width: 100% !important;
        width: auto !important;
        height: auto !important;
        border-radius: 30px !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    }
    
    .limit-info {
        color: #cccccc !important;
        font-size: 0.8em;
        margin-top: -10px;
        margin-bottom: 20px;
    }
    
    /* 6. CUSTOM SUCCESS BANNER (NOWOŚĆ V25) */
    .success-banner {
        background-color: rgba(250, 102, 15, 0.15); /* Przezroczysty pomarańcz */
        border: 1px solid #fa660f;
        color: #fa660f;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        font-weight: 700;
        margin-top: 20px;
        margin-bottom: 10px;
        width: 100%;
        box-sizing: border-box; /* Gwarancja responsywności */
    }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---

def process_svg_logo(file_path, new_color="#fa660f"):
    try:
        with open(file_path, "r") as f:
            svg_content = f.read()
        svg_content = re.sub(r'fill="[^"]*"', f'fill="{new_color}"', svg_content)
        svg_content = svg_content.replace("black", new_color)
        svg_content = svg_content.replace("#000000", new_color)
        return svg_content
    except Exception as e:
        return None

def compress_and_encode_image(image_source, max_size=1024, quality=80):
    try:
        if isinstance(image_source, str):
            if not os.path.exists(image_source): return None
            img = Image.open(image_source)
        else:
            img = Image.open(image_source)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.thumbnail((max_size, max_size))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        st.error(f"Compression error: {e}")
        return None

def get_mascot_refs(folder_name="mascot"):
    extensions = ['*.jpg', '*.jpeg', '*.png']
    files = []
    if os.path.exists(folder_name):
        for ext in extensions:
            files.extend(glob.glob(os.path.join(folder_name, ext)))
        for ext in extensions:
             files.extend(glob.glob(os.path.join(folder_name, ext.upper())))
    
    if not files: return None
    encoded_files = [compress_and_encode_image(f) for f in files]
    return [f for f in encoded_files if f is not None]

# --- AUTHENTICATION ---
ADMIN_PASS = st.secrets.get("ADMIN_PASSWORD", "")
TEAM_PASS = st.secrets.get("TEAM_PASSWORD", "")

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.role = None

    if st.session_state.authenticated:
        return True

    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        logo_svg = process_svg_logo("strategy_logo_black.svg", "#fa660f")
        if logo_svg:
            st.markdown(f'<div class="logo-container" style="margin: 0 auto 20px auto;">{logo_svg}</div>', unsafe_allow_html=True)
        else:
            st.header("Login")

        input_pass = st.text_input("Enter Access Password:", type="password")
        
        if input_pass:
            if input_pass == ADMIN_PASS:
                st.session_state.authenticated = True
                st.session_state.role = 'admin'
                st.rerun()
            elif input_pass == TEAM_PASS:
                st.session_state.authenticated = True
                st.session_state.role = 'user'
                st.rerun()
            else:
                st.error("Incorrect password")
    return False

if not check_password():
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    if st.session_state.role == 'admin':
        st.success("Role: **Super Admin**")
    else:
        st.info("Role: **Team Member**")
    
    if st.button("Log out"):
        st.session_state.authenticated = False
        st.session_state.role = None
        st.rerun()

# --- HEADER AREA ---
logo_svg = process_svg_logo("strategy_logo_black.svg", "#fa660f")
if logo_svg:
    st.markdown(f'<div class="logo-container">{logo_svg}</div>', unsafe_allow_html=True)

col_head_img, col_head_txt = st.columns([1, 6])
with col_head_img:
    if os.path.exists("maxi_head.png"):
        st.image("maxi_head.png", use_container_width=True)
    else:
        st.write("🦡") 
with col_head_txt:
    st.title("Maxi Generator")
    if st.session_state.role != 'admin':
        st.markdown('<div class="limit-info">⚡ Team Access: Limited to 5 generations per hour.</div>', unsafe_allow_html=True)

# --- SETTINGS AREA ---
with st.container():
    st.markdown("### Settings")
    col_sett_1, col_sett_2 = st.columns([1, 1])
    
    with col_sett_1:
        ratio_alias = st.radio("Format", ["9:16", "1:1", "16:9"], index=2, horizontal=True)
        if ratio_alias == "9:16":
            selected_ratio_val = "9:16"    
        elif ratio_alias == "1:1":
            selected_ratio_val = "1:1"
        else: 
            selected_ratio_val = "16:9"

    with col_sett_2:
        use_style = st.toggle("✨ Strategy Neon Style", value=True)
        st.markdown(
            '<div style="font-size: 11px; color: #888888; margin-top: -5px; line-height: 1.2;">Turn this off if you want a more colorful, less specific style.</div>', 
            unsafe_allow_html=True
        )

# --- PROMPT AREA ---
st.markdown("<br>", unsafe_allow_html=True)
prompt = st.text_area("Prompt", height=100, placeholder="E.g. The honey badger wearing a space suit on Mars...")

generate_btn = st.button("RUN GENERATOR", use_container_width=True)


# --- DATA LOADING ---
mascot_refs = get_mascot_refs()
if not mascot_refs:
     st.error("⚠️ Error: No images in '/mascot' folder.")


# --- QUOTA SYSTEM ---
HOURLY_LIMIT = 5
WINDOW_SECONDS = 3600

def check_quota():
    if st.session_state.role == 'admin': return True
    if 'gen_count' not in st.session_state:
        st.session_state.gen_count = 0
        st.session_state.first_gen_time = time.time()
    now = time.time()
    elapsed = now - st.session_state.first_gen_time
    if elapsed > WINDOW_SECONDS:
        st.session_state.gen_count = 0
        st.session_state.first_gen_time = now
        elapsed = 0
    if st.session_state.gen_count >= HOURLY_LIMIT:
        wait_min = int((WINDOW_SECONDS - elapsed) / 60)
        st.error(f"⛔ **Hourly Limit Reached ({HOURLY_LIMIT}/hour).** Please wait {wait_min} minutes for limit reset.")
        return False
    return True

def increment_quota():
    if st.session_state.role != 'admin':
        if 'gen_count' not in st.session_state: st.session_state.gen_count = 0
        st.session_state.gen_count += 1

# --- HIDDEN STYLE PROMPT ---
HIDDEN_STYLE = "Visual style defined by high contrast dark-mode aesthetic. Shadows, midtones, and blacks are strictly desaturated, rendered in deep graphite, matte charcoal, and cool grey tones. Highlights and light sources are exclusively vibrant neon orange with a soft blooming glow. Lighting is cinematic and dramatic, featuring occasional natural orange lens flares. The overall color grading creates a duotone effect: monochrome darks versus glowing orange lights, maintaining a premium, sleek, and moody atmosphere regardless of the setting."

# --- EXECUTION ---
if generate_btn:
    if check_quota():
        api_key = st.secrets.get("FAL_KEY")
        if not api_key:
            st.error("Missing FAL_KEY.")
        elif not prompt:
            st.warning("Prompt is required.")
        elif not mascot_refs:
            st.error("Admin Error: No mascot refs.")
        else:
            # 1. TWORZYMY PUSTY KONTENER NA STATUS
            status_container = st.empty()
            
            # Używamy kontenera do wyświetlenia statusu
            with status_container.status("✨ Working on our strategic AI magic... Please wait.", expanded=True):
                try:
                    os.environ["FAL_KEY"] = api_key
                    if use_style:
                        final_prompt = f"{prompt}. {HIDDEN_STYLE}"
                    else:
                        final_prompt = prompt 
                    
                    arguments = {
                        "prompt": final_prompt,
                        "num_inference_steps": 4,     
                        "guidance_scale": 0,          
                        "resolution": "2K",           
                        "aspect_ratio": selected_ratio_val,
                        "image_urls": mascot_refs,
                        "safety_tolerance": "2"
                    }

                    handler = fal_client.submit("fal-ai/nano-banana-pro/edit", arguments=arguments)
                    result = handler.get()
                    
                    # Po sukcesie nie aktualizujemy statusu, tylko go czyścimy
                    # status.update(...) <- TO USUWAMY
                    increment_quota() 
                except Exception as e:
                    st.error(f"Details: {e}")
                    result = None

            # 2. CZYSZCZENIE KONTENERA (Status znika całkowicie)
            status_container.empty()

            if result and 'images' in result:
                img_url = result['images'][0]['url']
                
                # 3. WYŚWIETLANIE CUSTOMOWEGO BANERA SUKCESU (Zamiast statusu)
                st.markdown('<div class="success-banner">✨ Strategic Magic Delivered!</div>', unsafe_allow_html=True)
                
                st.markdown(f'<div class="result-image-container"><img src="{img_url}"></div>', unsafe_allow_html=True)
                
                st.warning("⚠️ **Note:** If you like this result, please download it now. It will be overwritten when you generate a new image.")
                
                try:
                    response = requests.get(img_url)
                    response.raise_for_status()
                    img_data = response.content
                    st.download_button(label="📥 Download High-Res Image (2K)", data=img_data, file_name="maxi_generated.jpg", mime="image/jpeg", use_container_width=True)
                except Exception as download_err:
                    st.error(f"Error: {download_err}")
                    st.markdown(f"[Backup Link]({img_url})")
            elif result:
                st.error("API Error.")
                st.json(result)