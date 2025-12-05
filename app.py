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
    
    # Compress and return without printing any message
    encoded_files = [compress_and_encode_image(f) for f in files]
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
            "Maxi Generator", 
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

    # 3. SETTINGS (Unified Aspect Ratio)
    selected_size = None
    selected_ratio_val = None

    # Logic: Show Aspect Ratio for Maxi OR Flux Txt
    if current_config["mode"] == "maxi_preset" or current_config["api_type"] == "flux_txt":
        ratio_alias = st.radio("Aspect Ratio", ["9:16", "1:1", "16:9"], index=2)
        
        # Mapping: Flux needs "landscape_16_9", Nano likes "16:9" usually, 
        # but let's prepare both values just in case.
        if ratio_alias == "9:16":
            selected_size = "portrait_16_9" # For Flux
            selected_ratio_val = "9:16"     # For Nano
        elif ratio_alias == "1:1":
            selected_size = "square"
            selected_ratio_val = "1:1"
        else: # 16:9
            selected_size = "landscape_16_9"
            selected_ratio_val = "16:9"
            
    # For Manual Nano Edit -> still Resolution might be useful, or stick to Aspect
    elif current_config["api_type"] == "nano":
         selected_size = st.radio("Resolution", ["1K", "2K"], index=0)
    
    # 4. DATA LOADING
    uploaded_files = []
    mascot_refs = []
    
    if current_config["mode"] == "maxi_preset":
        mascot_refs = get_mascot_refs()
        if not mascot_refs:
             st.error("⚠️ Error: No images in '/mascot' folder.")
        # SILENT MODE: No text printed here

    elif "edit" in current_config["mode"]:
        st.divider()
        uploaded_files = st.file_uploader("Upload Source Image (Required)", accept_multiple_files=True)
        
    elif current_config["mode"] == "text_to_image":
        st.divider()
        uploaded_files = st.file_uploader("Reference Image (Optional)", accept_multiple_files=True)

# --- MAIN AREA ---

if current_config["mode"] == "maxi_preset":
    col_head_img, col_head_txt = st.columns([1, 6])
    with col_head_img:
        if os.path.exists("maxi_head.png"):
            st.image("maxi_head.png", use_container_width=True)
        else:
            st.write("🦡") 
    with col_head_txt:
        st.title("Maxi Generator")
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
                    arguments["resolution"] = "1K" # Default quality
                    # NEW: Explicit Aspect Ratio
                    arguments["aspect_ratio"] = selected_ratio_val 
                    arguments["image_urls"] = mascot_refs 

                # 2. NANO BANANA MANUAL
                elif current_config["api_type"] == "nano":
                    arguments["num_inference_steps"] = 4
                    arguments["guidance_scale"] = 0
                    arguments["resolution"] = selected_size
                    if uploaded_files:
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