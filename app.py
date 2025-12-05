import streamlit as st
import fal_client
import os
import base64
import re
from PIL import Image
import io
import glob

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Studio Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS (Styling) ---
st.markdown("""
    <style>
    /* Button Styling */
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
    
    /* CLEAN INTERFACE */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* LOGO FIX */
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
    
    /* MAXI HEADER STYLING */
    .maxi-header-img {
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---

def process_svg_logo(file_path, new_color="#fa660f"):
    """Loads SVG and changes color."""
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
    """
    CRITICAL FIX: Resizes and compresses images before sending to API
    to avoid 'Request body size exceeded' error.
    Accepts either a file path (str) or a file object (BytesIO).
    """
    try:
        # Load image based on type
        if isinstance(image_source, str): # It's a path
            if not os.path.exists(image_source): return None
            img = Image.open(image_source)
        else: # It's a file object from uploader
            img = Image.open(image_source)

        # Convert to RGB (fixes issues with PNG transparency saving as JPEG)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Resize if larger than max_size (keeps aspect ratio)
        img.thumbnail((max_size, max_size))

        # Save to buffer with compression
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        
        # Encode
        return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        st.error(f"Compression error: {e}")
        return None

def get_mascot_refs(folder_name="mascot"):
    """Loads and COMPRESSES all valid image files from the mascot folder."""
    extensions = ['*.jpg', '*.jpeg', '*.png']
    files = []
    if os.path.exists(folder_name):
        for ext in extensions:
            files.extend(glob.glob(os.path.join(folder_name, ext)))
        for ext in extensions:
             files.extend(glob.glob(os.path.join(folder_name, ext.upper())))
    
    if not files: return None
    
    # Use the new compressor function
    encoded_files = [compress_and_encode_image(f) for f in files]
    # Filter out any Nones in case of error
    return [f for f in encoded_files if f is not None]

# --- AUTHENTICATION ---
ACCESS_PASSWORD = st.secrets.get("APP_PASSWORD", os.environ.get("APP_PASSWORD", ""))
def check_password():
    if not ACCESS_PASSWORD: return True 
    if "password_correct" not in st.session_state: st.session_state.password_correct = False
    if st.session_state.password_correct: return True
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info("🔒 Login Required")
        pwd = st.text_input("Password:", type="password")
        if pwd == ACCESS_PASSWORD:
            st.session_state.password_correct = True
            st.rerun()
    return False
if not check_password(): st.stop()

# --- SIDEBAR CONFIG ---
with st.sidebar:
    # 1. LOGO
    logo_svg = process_svg_logo("strategy_logo_black.svg", "#fa660f")
    if logo_svg:
        st.markdown(f'<div class="logo-container">{logo_svg}</div>', unsafe_allow_html=True)
    else:
        st.header("⚡ AI STUDIO")

    st.divider()
    
    # 2. MODEL SELECTION
    model_name = st.selectbox(
        "Select Mode",
        options=[
            "Maxi Generator", # SKRÓCONA NAZWA
            "flux 2 flex",
            "flux 2 flex edit",
            "nano banana pro edit"
        ]
    )
    
    # --- CONFIGURATION MAP ---
    MODEL_CONFIG = {
        "Maxi Generator": {
            "id": "fal-ai/nano-banana-pro/edit", 
            "mode": "maxi_preset",
            "api_type": "nano"
        },
        "flux 2 flex": {
            "id": "fal-ai/flux-2-flex",
            "mode": "text_to_image",
            "api_type": "flux_txt"
        },
        "flux 2 flex edit": {
            "id": "fal-ai/flux-2-flex/edit",
            "mode": "image_edit",
            "api_type": "flux_edit"
        },
        "nano banana pro edit": {
            "id": "fal-ai/nano-banana-pro/edit",
            "mode": "nano_edit",
            "api_type": "nano"
        }
    }
    
    current_config = MODEL_CONFIG[model_name]

    # 3. SETTINGS
    selected_size = None
    if current_config["api_type"] == "flux_txt":
        ratio_alias = st.radio("Aspect Ratio", ["9:16", "1:1", "16:9"], index=2)
        ratio_map = {"9:16": "portrait_16_9", "1:1": "square", "16:9": "landscape_16_9"}
        selected_size = ratio_map[ratio_alias]
    elif current_config["api_type"] == "nano":
        selected_size = st.radio("Resolution", ["1K", "2K"], index=0)
    
    # 4. DATA LOADING
    uploaded_files = []
    mascot_refs = []
    
    if current_config["mode"] == "maxi_preset":
        mascot_refs = get_mascot_refs()
        if not mascot_refs:
             st.error("⚠️ Error: No images in '/mascot' folder.")
        else:
             st.caption(f"Loaded {len(mascot_refs)} reference images.")

    elif "edit" in current_config["mode"]:
        st.divider()
        uploaded_files = st.file_uploader("Upload Source Image (Required)", accept_multiple_files=True)
        
    elif current_config["mode"] == "text_to_image":
        st.divider()
        uploaded_files = st.file_uploader("Reference Image (Optional)", accept_multiple_files=True)

# --- MAIN AREA ---

# NEW HEADER LOGIC
if current_config["mode"] == "maxi_preset":
    # Layout: Kolumna na obrazek (wąska) | Kolumna na tytuł (szeroka)
    col_head_img, col_head_txt = st.columns([1, 6])
    
    with col_head_img:
        if os.path.exists("maxi_head.png"):
            st.image("maxi_head.png", use_container_width=True)
        else:
            st.warning("No icon") # Fallback if file missing
            
    with col_head_txt:
        st.title("Maxi Generator")
        # SUBHEADLINE USUNIĘTY
else:
    st.title(model_name)

prompt = st.text_area("Prompt", height=100, placeholder="E.g. The honey badger wearing a space suit on Mars...")

col1, col2 = st.columns([1, 4])
with col1:
    generate_btn = st.button("RUN", use_container_width=True)

# --- GENERATION ENGINE ---
if generate_btn:
    api_key = st.secrets.get("FAL_KEY")
    
    if not api_key:
        st.error("Missing FAL_KEY.")
    elif not prompt:
        st.warning("Prompt is required.")
    elif "edit" in current_config["mode"] and current_config["mode"] != "maxi_preset" and not uploaded_files:
        st.error("Upload an image to start editing.")
    elif current_config["mode"] == "maxi_preset" and not mascot_refs:
        st.error("Mascot generation failed: No references.")
    else:
        with st.status("Processing...", expanded=True) as status:
            try:
                os.environ["FAL_KEY"] = api_key
                
                arguments = {
                    "prompt": prompt,
                    "num_inference_steps": 28,
                    "guidance_scale": 3.5,
                    "safety_tolerance": "2"
                }

                # --- PAYLOAD BUILDER ---
                
                # 1. MAXI GENERATOR
                if current_config["mode"] == "maxi_preset":
                    arguments["num_inference_steps"] = 4
                    arguments["guidance_scale"] = 0
                    arguments["resolution"] = selected_size if selected_size else "1K"
                    # Refs are already compressed via get_mascot_refs()
                    arguments["image_urls"] = mascot_refs 

                # 2. NANO BANANA MANUAL
                elif current_config["api_type"] == "nano":
                    arguments["num_inference_steps"] = 4
                    arguments["guidance_scale"] = 0
                    arguments["resolution"] = selected_size
                    if uploaded_files:
                        # Compress uploads too!
                        arguments["image_urls"] = [compress_and_encode_image(f) for f in uploaded_files]

                # 3. FLUX EDIT
                elif current_config["api_type"] == "flux_edit":
                    if uploaded_files:
                        arguments["image_urls"] = [compress_and_encode_image(f) for f in uploaded_files]

                # 4. FLUX TXT
                else:
                    if selected_size: arguments["image_size"] = selected_size
                    if uploaded_files:
                        arguments["image_url"] = compress_and_encode_image(uploaded_files[0])

                # --- SUBMIT ---
                st.write(f"Sending request to {current_config['id']}...")
                
                handler = fal_client.submit(
                    current_config["id"],
                    arguments=arguments,
                )
                
                result = handler.get()
                
                if 'images' in result:
                    img_url = result['images'][0]['url']
                    status.update(label="Done!", state="complete", expanded=False)
                    st.image(img_url, use_container_width=True)
                    st.markdown(f"**[Download Image]({img_url})**")
                else:
                    st.error("API Error: No image returned.")
                    if result: st.json(result)
                    
            except Exception as e:
                status.update(label="Error", state="error")
                st.error(f"Details: {e}")