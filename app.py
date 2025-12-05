import streamlit as st
import fal_client
import os
import base64
import re

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS (Styling) ---
st.markdown("""
    <style>
    .stButton>button {
        background-color: #fa660f;
        color: white;
        border-radius: 8px;
        height: 3.5em;
        font-weight: bold;
        border: none;
    }
    .stButton>button:hover {
        background-color: #d9550a;
        color: white;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* Clean look for selectbox */
    .stSelectbox div[data-baseweb="select"] > div {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---

def load_and_color_svg(file_path, new_color="#fa660f"):
    try:
        with open(file_path, "r") as f:
            svg_content = f.read()
        # Replace black/dark fills with brand color
        svg_content = re.sub(r'fill="[^"]*"', f'fill="{new_color}"', svg_content)
        svg_content = svg_content.replace("black", new_color)
        svg_content = svg_content.replace("#000000", new_color)
        return svg_content
    except Exception as e:
        return None

def encode_image(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        base64_str = base64.b64encode(bytes_data).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_str}"
    return None

# --- AUTHENTICATION ---
ACCESS_PASSWORD = st.secrets.get("APP_PASSWORD", os.environ.get("APP_PASSWORD", ""))

def check_password():
    if not ACCESS_PASSWORD:
        return True 
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if st.session_state.password_correct:
        return True
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info("🔒 Login Required")
        pwd = st.text_input("Password:", type="password")
        if pwd == ACCESS_PASSWORD:
            st.session_state.password_correct = True
            st.rerun()
    return False

if not check_password():
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    # Logo Logic (Small size)
    logo_svg = load_and_color_svg("strategy_logo_black.svg", "#fa660f")
    if logo_svg:
        st.markdown(f'<div style="width: 80px; margin-bottom: 20px;">{logo_svg}</div>', unsafe_allow_html=True)
    else:
        st.header("⚡ AI STUDIO")

    st.divider()
    
    # 1. MODEL SELECTION (Clean names)
    model_name = st.selectbox(
        "Model",
        options=[
            "flux 2 flex",
            "flux 2 flex edit",
            "nano banana pro edit"
        ]
    )
    
    # Model Configuration Map
    # Holds ID and type (txt2img vs edit)
    MODEL_CONFIG = {
        "flux 2 flex": {
            "id": "fal-ai/flux-2-flex",
            "mode": "text_to_image"
        },
        "flux 2 flex edit": {
            "id": "fal-ai/flux-2-flex/edit",
            "mode": "image_edit"
        },
        "nano banana pro edit": {
            "id": "fal-ai/nano-banana-pro/edit",
            "mode": "nano_edit" # Nano Banana has specific API requirements
        }
    }
    
    current_config = MODEL_CONFIG[model_name]

    # 2. SIZE / RATIO SETTINGS
    # Only show Aspect Ratio for text-to-image models
    # Edit models usually preserve original aspect ratio or use "Resolution"
    if current_config["mode"] == "text_to_image":
        ratio_alias = st.radio(
            "Aspect Ratio",
            options=["9:16", "1:1", "16:9"],
            index=2
        )
        ratio_map = {"9:16": "portrait_16_9", "1:1": "square", "16:9": "landscape_16_9"}
        selected_size = ratio_map[ratio_alias]
    elif current_config["mode"] == "nano_edit":
        # Nano Banana uses Resolution Enum (1K, 2K, 4K)
        selected_size = st.radio("Resolution", ["1K", "2K"], index=0)
    else:
        # Flux Edit generally uses input image size, no setting needed here
        selected_size = None

    # 3. IMAGE UPLOAD
    st.divider()
    
    # If mode is EDIT, upload is mandatory. If Txt2Img, it's optional (ref).
    if "edit" in current_config["mode"]:
        upload_label = "Upload Source Image (Required)"
    else:
        upload_label = "Reference Image (Optional)"
        
    uploaded_files = st.file_uploader(
        upload_label, 
        accept_multiple_files=True,
        type=['png', 'jpg', 'jpeg']
    )

# --- MAIN INTERFACE ---
st.title(model_name) # Wyświetla czystą nazwę wybranego modelu

prompt = st.text_area("Prompt", height=100, placeholder="Describe your creation...")

col1, col2 = st.columns([1, 4])
with col1:
    generate_btn = st.button("RUN", use_container_width=True)

# --- GENERATION ENGINE ---
if generate_btn:
    api_key = st.secrets.get("FAL_KEY")
    
    # Validation
    if not api_key:
        st.error("Missing FAL_KEY in secrets.")
    elif not prompt:
        st.warning("Prompt is required.")
    elif "edit" in current_config["mode"] and not uploaded_files:
        st.error(f"You must upload an image to use {model_name}.")
    else:
        with st.status("Processing...", expanded=True) as status:
            try:
                os.environ["FAL_KEY"] = api_key
                model_id = current_config["id"]
                arguments = {"prompt": prompt}
                
                # --- PAYLOAD BUILDER ---
                
                # CASE 1: NANO BANANA PRO EDIT
                # Wymaga parametru 'image_urls' (lista) i 'resolution'
                if current_config["mode"] == "nano_edit":
                    if uploaded_files:
                        # Convert all uploaded files to base64
                        imgs = [encode_image(f) for f in uploaded_files]
                        arguments["image_urls"] = imgs # Note: Plural 'image_urls'
                        arguments["resolution"] = selected_size # e.g. "1K"
                    
                # CASE 2: FLUX 2 FLEX EDIT
                # Wymaga parametru 'image_url' (single) lub references
                elif current_config["mode"] == "image_edit":
                    if uploaded_files:
                        # Use first image as the edit source
                        arguments["image_url"] = encode_image(uploaded_files[0])
                        # Optional: Add extra images as references if needed, but keeping it simple
                        arguments["num_inference_steps"] = 28
                        arguments["guidance_scale"] = 3.5
                        arguments["strength"] = 0.85 # Default strength for edit

                # CASE 3: FLUX 2 FLEX (TEXT TO IMAGE)
                # Standard params
                else:
                    arguments["image_size"] = selected_size
                    arguments["num_inference_steps"] = 28
                    arguments["guidance_scale"] = 3.5
                    # Support for Ref Image in Txt2Img (optional)
                    if uploaded_files:
                         arguments["image_url"] = encode_image(uploaded_files[0])
                
                # --- SUBMIT ---
                st.write(f"Sending request to {model_name}...")
                
                handler = fal_client.submit(
                    model_id,
                    arguments=arguments,
                )
                
                result = handler.get()
                
                # Result parsing
                if 'images' in result and len(result['images']) > 0:
                    image_url = result['images'][0]['url']
                    status.update(label="Done!", state="complete", expanded=False)
                    st.image(image_url, use_container_width=True)
                    st.markdown(f"**[Download]({image_url})**")
                else:
                    st.error("No image returned from API.")
                    st.json(result) # Show debug info if empty
                
            except Exception as e:
                status.update(label="Error", state="error")
                st.error(f"API Error: {e}")