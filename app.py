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

# --- CSS (Styling & RESPONSIVE LOGO FIX) ---
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
    
    /* --- LOGO FIX (PURE CSS) --- */
    /* To jest kluczowe: kontener logo ma max szerokość 180px, 
       a obrazek w środku ma 100% tej szerokości i automatyczną wysokość. */
    .logo-container {
        max-width: 180px; /* Maksymalny rozmiar */
        width: 100%;      /* Responsywność */
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
    """Loads SVG and changes color. CSS handles sizing now."""
    try:
        with open(file_path, "r") as f:
            svg_content = f.read()
        
        # Color replacement only
        svg_content = re.sub(r'fill="[^"]*"', f'fill="{new_color}"', svg_content)
        svg_content = svg_content.replace("black", new_color)
        svg_content = svg_content.replace("#000000", new_color)
        
        return svg_content
    except Exception as e:
        return None

def encode_image_path(image_path):
    """Encodes a local file from disk."""
    if os.path.exists(image_path):
        with open(image_path, "rb") as image_file:
            return "data:image/jpeg;base64," + base64.b64encode(image_file.read()).decode('utf-8')
    return None

def encode_uploaded_file(uploaded_file):
    """Encodes a user-uploaded file."""
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        base64_str = base64.b64encode(bytes_data).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_str}"
    return None

def get_mascot_refs(folder_name="mascot"):
    """Loads all valid image files from the mascot folder."""
    extensions = ['*.jpg', '*.jpeg', '*.png']
    files = []
    if os.path.exists(folder_name):
        for ext in extensions:
            files.extend(glob.glob(os.path.join(folder_name, ext)))
        for ext in extensions:
             files.extend(glob.glob(os.path.join(folder_name, ext.upper())))
    
    if not files: return None
    
    st.info(f"ℹ️ Loaded {len(files)} reference images for Maxi Generator.")
    return [encode_image_path(f) for f in files]

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
    # 1. LOGO (Updated Logic)
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
            "Maxi Generator (Mascot)", # NOWA NAZWA
            "flux 2 flex",
            "flux 2 flex edit",
            "nano banana pro edit"
        ]
    )
    
    # --- CONFIGURATION MAP ---
    MODEL_CONFIG = {
        "Maxi Generator (Mascot)": {
            # TERAZ UŻYWAMY NANO BANANA PRO EDIT
            "id": "fal-ai/nano-banana-pro/edit", 
            "mode": "maxi_preset",
            "api_type": "nano" # Helper flag
        },
        "flux 2 flex": {
            "id": "fal-ai/flux-2-flex",
            "mode": "text_to_image",
            "api_type": "flux_txt"
        },
        "flux 2 flex edit": {
            "id": "fal-ai/flux-2-flex/edit",
            "mode": "image_edit",
            "api_type": "flux_edit" # New API requires image_urls
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
    # Text-to-Image models handle Aspect Ratio
    if current_config["api_type"] == "flux_txt":
        ratio_alias = st.radio("Aspect Ratio", ["9:16", "1:1", "16:9"], index=2)
        ratio_map = {"9:16": "portrait_16_9", "1:1": "square", "16:9": "landscape_16_9"}
        selected_size = ratio_map[ratio_alias]
        
    # Nano Banana models handle Resolution
    elif current_config["api_type"] == "nano":
        selected_size = st.radio("Resolution", ["1K", "2K"], index=0)
    
    # Flux Edit handles size automatically based on input

    # 4. UPLOADER LOGIC
    uploaded_files = []
    mascot_refs = []
    
    # Tryb Mascot -> Ładujemy pliki z folderu
    if current_config["mode"] == "maxi_preset":
        mascot_refs = get_mascot_refs()
        if not mascot_refs:
             st.error("⚠️ Error: No images found in '/mascot' folder.")

    # Tryb Edit -> Uploader wymagany
    elif "edit" in current_config["mode"]:
        st.divider()
        uploaded_files = st.file_uploader("Upload Source Image (Required)", accept_multiple_files=True)
        
    # Tryb Text -> Uploader opcjonalny
    elif current_config["mode"] == "text_to_image":
        st.divider()
        uploaded_files = st.file_uploader("Reference Image (Optional)", accept_multiple_files=True)

# --- MAIN AREA ---
if current_config["mode"] == "maxi_preset":
    st.title("🦡 Maxi Generator")
    st.markdown("Create new visuals with our Honey Badger brand hero.")
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
    # Check uploads for manual edit modes
    elif "edit" in current_config["mode"] and current_config["mode"] != "maxi_preset" and not uploaded_files:
        st.error("Upload an image to start editing.")
    # Check uploads for mascot mode
    elif current_config["mode"] == "maxi_preset" and not mascot_refs:
        st.error("Mascot generation failed: No reference images loaded.")
    else:
        with st.status("Processing...", expanded=True) as status:
            try:
                os.environ["FAL_KEY"] = api_key
                
                # BASE ARGUMENTS
                arguments = {
                    "prompt": prompt,
                    "num_inference_steps": 28,
                    "guidance_scale": 3.5,
                    "safety_tolerance": "2"
                }

                # --- PAYLOAD BUILDER ---
                
                # 1. MAXI GENERATOR (Mascot Preset - Nano Banana)
                if current_config["mode"] == "maxi_preset":
                    arguments["num_inference_steps"] = 4 # Lightning constraint
                    arguments["guidance_scale"] = 0
                    arguments["resolution"] = selected_size if selected_size else "1K"
                    # Podajemy WSZYSTKIE pliki z folderu mascot
                    arguments["image_urls"] = mascot_refs

                # 2. NANO BANANA EDIT (Manual Upload)
                elif current_config["api_type"] == "nano":
                    arguments["num_inference_steps"] = 4
                    arguments["guidance_scale"] = 0
                    arguments["resolution"] = selected_size
                    if uploaded_files:
                        arguments["image_urls"] = [encode_uploaded_file(f) for f in uploaded_files]

                # 3. FLUX 2 FLEX EDIT (Manual Upload) - NAPRAWA BŁĘDU
                elif current_config["api_type"] == "flux_edit":
                    if uploaded_files:
                        # API WYMAGA LISTY 'image_urls', a nie pojedynczego 'image_url'
                        arguments["image_urls"] = [encode_uploaded_file(f) for f in uploaded_files]
                        # Opcjonalnie strength
                        # arguments["strength"] = 0.85 

                # 4. FLUX 2 FLEX (Text to Image)
                else:
                    if selected_size: arguments["image_size"] = selected_size
                    if uploaded_files:
                        # Tutaj stare API może jeszcze chcieć 'image_url'
                        arguments["image_url"] = encode_uploaded_file(uploaded_files[0])

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
                    if result: st.json(result) # Debugging
                    
            except Exception as e:
                status.update(label="Error", state="error")
                st.error(f"Details: {e}")