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
    initial_sidebar_state="expanded"
)

# --- CSS (Styling, FONTS & GHOST MODE) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #ffffff;
        font-weight: 400;
    }
    
    label, .stMarkdown p, .stCaption {
        font-weight: 500;
    }

    h1 {
        color: #fa660f !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
    }
    
    /* GHOST MODE */
    [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
    [data-testid="stHeader"] {visibility: hidden !important; display: none !important;}
    [data-testid="stDecoration"] {visibility: hidden !important; display: none !important;}
    .stDeployButton {display:none !important;}
    footer {visibility: hidden !important; display: none !important;}
    #MainMenu {visibility: hidden !important; display: none !important;}
    
    .block-container {
        padding-top: 2rem !important;
    }

    /* BUTTONS */
    .stButton>button {
        background-color: #fa660f;
        color: white;
        border-radius: 8px;
        height: 3.5em;
        font-weight: bold;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #d9550a;
        color: white;
        transform: scale(1.02);
    }
    
    /* IMAGES (LOGO) */
    .logo-container {
        max-width: 180px;
        width: 100%;
        margin-bottom: 20px;
    }
    .logo-container svg, .logo-container img {
        width: 100% !important;
        height: auto !important;
        display: block;
    }

    /* RESULT IMAGE STYLING */
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
        font-size: 0.9em;
        margin-top: -15px;
        margin-bottom: 20px;
        font-weight: 400;
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

# --- SIMPLE AUTHENTICATION (TWO PASSWORDS) ---

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
        
        # Logo in Login
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
    # Role Display
    if st.session_state.role == 'admin':
        st.success("Role: **Super Admin (Unlimited)**")
    else:
        st.info("Role: **Team Member**")
        
    # Logout
    if st.button("Log out"):
        st.session_state.authenticated = False
        st.session_state.role = None
        st.rerun()

    logo_svg = process_svg_logo("strategy_logo_black.svg", "#fa660f")
    if logo_svg:
        st.markdown(f'<div class="logo-container">{logo_svg}</div>', unsafe_allow_html=True)
    else:
        st.header("⚡ AI STUDIO")

    st.divider()
    
    st.markdown("**Settings**")
    
    ratio_alias = st.radio("Aspect Ratio", ["9:16", "1:1", "16:9"], index=2)
    
    if ratio_alias == "9:16":
        selected_ratio_val = "9:16"    
    elif ratio_alias == "1:1":
        selected_ratio_val = "1:1"
    else: 
        selected_ratio_val = "16:9"
    
    # --- NOWY PRZEŁĄCZNIK STYLU ---
    st.markdown("<br>", unsafe_allow_html=True) # Odstęp
    use_style = st.toggle("✨ Strategy Neon Style", value=True)
    
    mascot_refs = get_mascot_refs()
    if not mascot_refs:
         st.error("⚠️ Error: No images in '/mascot' folder.")

# --- MAIN AREA ---

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

prompt = st.text_area("Prompt", height=100, placeholder="E.g. The honey badger wearing a space suit on Mars...")

col1, col2 = st.columns([1, 4])
with col1:
    generate_btn = st.button("RUN GENERATOR", use_container_width=True)

# --- QUOTA SYSTEM (5 PER HOUR) ---
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
HIDDEN_STYLE = "Cinematic premium night-time fashion vibe. Color palette dominated by dark grey, graphite, and matte black, accented with bright orange glow and neon orange highlights. The background remains desaturated in greyscale, while key elements feature orange light. Lighting is soft directional cinematic with thin glowing orange strips, neon reflections, and light trails, creating high contrast against the dark environment. The background is a slightly blurred futuristic city or architectural setting featuring polished metal, wet pavement reflections, and glass surfaces."

# --- EXECUTION ---
if generate_btn:
    
    if check_quota():
        api_key = st.secrets.get("FAL_KEY")
        
        if not api_key:
            st.error("Missing FAL_KEY.")
        elif not prompt:
            st.warning("Prompt is required.")
        elif not mascot_refs:
            st.error("Administrator Error: No mascot references found.")
        else:
            with st.status("✨ Working on our strategic AI magic... Please wait.", expanded=True) as status:
                try:
                    os.environ["FAL_KEY"] = api_key
                    
                    # --- LOGIKA PRZEŁĄCZNIKA ---
                    if use_style:
                        final_prompt = f"{prompt}. {HIDDEN_STYLE}"
                    else:
                        final_prompt = prompt # Czysty prompt użytkownika
                    
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
                    
                    status.update(label="✨ Strategic Magic Delivered!", state="complete", expanded=False)
                    increment_quota() 
                    
                except Exception as e:
                    status.update(label="Error", state="error")
                    st.error(f"Details: {e}")
                    result = None

            if result and 'images' in result:
                img_url = result['images'][0]['url']
                
                st.markdown(f'<div class="result-image-container"><img src="{img_url}"></div>', unsafe_allow_html=True)
                
                st.warning("⚠️ **Note:** If you like this result, please download it now. It will be overwritten when you generate a new image.")

                try:
                    response = requests.get(img_url)
                    response.raise_for_status()
                    img_data = response.content
                    
                    st.download_button(
                        label="📥 Download High-Res Image (2K)",
                        data=img_data,
                        file_name="maxi_generated.jpg",
                        mime="image/jpeg",
                        use_container_width=True
                    )
                except Exception as download_err:
                    st.error(f"Could not prepare download: {download_err}")
                    st.markdown(f"[Backup Link]({img_url})")
            
            elif result:
                st.error("API Error: No image returned.")
                st.json(result)