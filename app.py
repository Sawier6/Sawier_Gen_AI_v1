import streamlit as st
import fal_client
import os
import base64
import re

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Creative Studio Pro",
    page_icon="🍊",
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
    /* Hide Streamlit footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---

def load_and_color_svg(file_path, new_color="#fa660f"):
    """Loads SVG and replaces black/dark colors with the brand color."""
    try:
        with open(file_path, "r") as f:
            svg_content = f.read()
        
        # Color replacement logic
        svg_content = re.sub(r'fill="[^"]*"', f'fill="{new_color}"', svg_content)
        svg_content = svg_content.replace("black", new_color)
        svg_content = svg_content.replace("#000000", new_color)
        svg_content = svg_content.replace("#000", new_color)
        
        return svg_content
    except Exception as e:
        return None

def encode_image(uploaded_file):
    """Encodes uploaded file to base64 for the API."""
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        base64_str = base64.b64encode(bytes_data).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_str}"
    return None

# --- PASSWORD PROTECTION ---
ACCESS_PASSWORD = st.secrets.get("APP_PASSWORD", os.environ.get("APP_PASSWORD", ""))

def check_password():
    """Simple password gate."""
    if not ACCESS_PASSWORD:
        return True 
        
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    
    if st.session_state.password_correct:
        return True
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info("🔒 Restricted Access")
        pwd = st.text_input("Enter Password:", type="password")
        if pwd == ACCESS_PASSWORD:
            st.session_state.password_correct = True
            st.rerun()
        elif pwd:
            st.error("Incorrect password")
    return False

if not check_password():
    st.stop()

# --- SIDEBAR (Settings) ---
with st.sidebar:
    # 1. LOGO - RESIZED
    logo_svg = load_and_color_svg("strategy_logo_black.svg", "#fa660f")
    if logo_svg:
        # Changed max-width from 200px to 80px (approx 2.5x smaller)
        st.markdown(f'<div style="width: 80px; margin-bottom: 20px;">{logo_svg}</div>', unsafe_allow_html=True)
    else:
        st.header("🍊 YOUR BRAND")

    st.divider()
    st.subheader("⚙️ Model Settings")

    # 2. MODEL SELECTION
    model_alias = st.selectbox(
        "Select Model",
        options=["Flux 1.1 Pro (Best Quality)", "Flux Dev (Standard)", "Nano Banana Pro (Fastest)"],
        index=0
    )
    
    # Mapping aliases to real Model IDs
    model_map = {
        "Flux 1.1 Pro (Best Quality)": "fal-ai/flux-pro/v1.1",
        "Flux Dev (Standard)": "fal-ai/flux/dev",
        "Nano Banana Pro (Fastest)": "fal-ai/fast-lightning-sdxl" 
    }
    selected_model_id = model_map[model_alias]

    # 3. ASPECT RATIO
    ratio_alias = st.radio(
        "Aspect Ratio",
        options=["9:16 (Story)", "1:1 (Square)", "16:9 (Landscape)"],
        index=2
    )
    
    ratio_map = {
        "9:16 (Story)": "portrait_16_9",
        "1:1 (Square)": "square",
        "16:9 (Landscape)": "landscape_16_9"
    }
    selected_ratio = ratio_map[ratio_alias]

    # 4. REFERENCE IMAGES
    st.divider()
    st.subheader("🖼️ Reference Images")
    uploaded_refs = st.file_uploader(
        "Upload reference images (Max 6)", 
        accept_multiple_files=True,
        type=['png', 'jpg', 'jpeg']
    )
    
    if uploaded_refs and len(uploaded_refs) > 6:
        st.warning("⚠️ Max 6 files. Only the first 6 will be processed.")
        uploaded_refs = uploaded_refs[:6]

# --- MAIN PAGE ---
st.title("✨ AI Image Generator")
st.caption(f"Current Model: {model_alias}")

# Prompt Input
prompt = st.text_area("Describe the image you want to generate:", height=120, placeholder="E.g. A futuristic sports car in orange color, cinematic lighting, photorealistic 8k...")

col1, col2 = st.columns([1, 3])
with col1:
    generate_btn = st.button("🚀 GENERATE", use_container_width=True)

# --- GENERATION LOGIC ---
if generate_btn:
    api_key = st.secrets.get("FAL_KEY")
    
    if not api_key:
        st.error("Error: FAL_KEY not found in Secrets.")
    elif not prompt:
        st.warning("Please enter a prompt description.")
    else:
        with st.status("🍊 AI is working...", expanded=True) as status:
            try:
                os.environ["FAL_KEY"] = api_key
                
                # --- INTELLIGENT STEPS CONFIGURATION ---
                # "Nano Banana" (Lightning) supports ONLY 4 or 8 steps.
                # Flux supports 28+. We adjust this automatically to prevent errors.
                if "lightning" in selected_model_id:
                    num_steps = 4 
                    guidance = 0 # Lightning models usually ignore or need 0 guidance
                else:
                    num_steps = 28
                    guidance = 3.5

                # Basic arguments
                arguments = {
                    "prompt": prompt,
                    "image_size": selected_ratio,
                    "num_inference_steps": num_steps,
                    "guidance_scale": guidance,
                    "safety_tolerance": "2"
                }

                # --- REFERENCE IMAGE HANDLING ---
                if uploaded_refs:
                    st.write(f"Processing {len(uploaded_refs)} reference images...")
                    main_ref_image = encode_image(uploaded_refs[0])
                    arguments["image_url"] = main_ref_image
                    
                    # If Flux Dev is used, we swap to the img2img endpoint
                    if "flux/dev" in selected_model_id:
                        selected_model_id = "fal-ai/flux/dev/image-to-image"
                        arguments["strength"] = 0.75
                    
                    # Nano Banana/Lightning usually handles img2img via image_url natively
                    # but assumes specific strength logic.
                    if "lightning" in selected_model_id:
                         arguments["strength"] = 0.50 # Moderate influence

                    st.info("ℹ️ Using the first image as the main reference.")

                st.write("Sending to GPU cluster...")
                
                handler = fal_client.submit(
                    selected_model_id,
                    arguments=arguments,
                )
                
                result = handler.get()
                image_url = result['images'][0]['url']
                
                status.update(label="✅ Generation Complete!", state="complete", expanded=False)
                
                st.image(image_url, use_container_width=True)
                st.markdown(f"**[📥 Download High Resolution Image]({image_url})**")
                
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Something went wrong: {e}")
                # Debug info
                if "unexpected value" in str(e):
                    st.error(f"Model settings mismatch. Tried using {num_steps} steps for a model that doesn't support it.")