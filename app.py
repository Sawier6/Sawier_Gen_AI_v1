import streamlit as st
import fal_client
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Creative Studio",
    page_icon="🎨",
    layout="wide" # Zmieniłem na wide, żeby mieć więcej miejsca
)

# --- CUSTOM CSS (Styling) ---
# To usuwa stopkę "Made with Streamlit" i poprawia wygląd
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- PASSWORD PROTECTION ---
ACCESS_PASSWORD = st.secrets.get("APP_PASSWORD", os.environ.get("APP_PASSWORD", "admin123"))

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    
    if st.session_state.password_correct:
        return True
    
    # Proste i ładne okno logowania
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.header("🔒 Login Required")
        pwd = st.text_input("Enter Access Password:", type="password")
        if pwd == ACCESS_PASSWORD:
            st.session_state.password_correct = True
            st.rerun()
        elif pwd:
            st.error("Incorrect password")
    return False

if not check_password():
    st.stop()

# --- SIDEBAR (Settings & Logo) ---
with st.sidebar:
    # 1. LOGO FIRMY
    # Jeśli wgrałeś plik logo.png, to się wyświetli. Jak nie - pokaże tekst.
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.header("🚀 YOUR COMPANY")
    
    st.divider()
    
    st.subheader("⚙️ Configuration")
    
    # 2. WIĘCEJ MODELI
    model_name = st.selectbox(
        "Select AI Model",
        options=[
            "fal-ai/flux/dev",
            "fal-ai/flux/schnell",
            "fal-ai/flux-pro/v1.1", # Ultra quality (może być droższy)
            "fal-ai/auraflow"       # Alternatywa
        ],
        format_func=lambda x: {
            "fal-ai/flux/dev": "Flux Dev (Balanced - Recommended)",
            "fal-ai/flux/schnell": "Flux Schnell (Super Fast)",
            "fal-ai/flux-pro/v1.1": "Flux Pro 1.1 (Ultra Realism)",
            "fal-ai/auraflow": "AuraFlow (Creative)"
        }.get(x, x)
    )
    
    # 3. FORMAT OBRAZU
    aspect_ratio = st.selectbox(
        "Aspect Ratio",
        options=["square_hd", "square", "portrait_4_3", "portrait_16_9", "landscape_16_9", "landscape_21_9"],
        index=4,
        format_func=lambda x: x.replace("_", " ").title()
    )

    # 4. ZAAWANSOWANE (Ukryte w rozwijanym menu)
    with st.expander("Advanced Settings"):
        guidance = st.slider("Guidance Scale (Creativity)", 1.0, 10.0, 3.5)
        steps = st.slider("Inference Steps", 10, 50, 28)
        safety_checker = st.checkbox("Enable Safety Checker", value=True)

    st.divider()
    st.caption("Internal Tool v2.0")

# --- MAIN AREA ---
st.title("✨ AI Image Generator")
st.markdown("Create stunning visuals for your projects in seconds.")

# Input Area
prompt = st.text_area("Describe your image...", height=150, placeholder="Example: A futuristic glass office building in downtown Warsaw, golden hour light, photorealistic 8k...")

# Generate Button (Central and Big)
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    generate_btn = st.button("✨ GENERATE IMAGE", type="primary")

# --- GENERATION LOGIC ---
if generate_btn:
    api_key = st.secrets.get("FAL_KEY")
    
    if not api_key:
        st.error("❌ Configuration Error: FAL_KEY missing in secrets.")
    elif not prompt:
        st.warning("⚠️ Please enter a prompt description.")
    else:
        # Placeholder na czas generowania
        with st.status("🤖 AI is working...", expanded=True) as status:
            try:
                st.write("Connecting to GPU cluster...")
                os.environ["FAL_KEY"] = api_key
                
                handler = fal_client.submit(
                    model_name,
                    arguments={
                        "prompt": prompt,
                        "image_size": aspect_ratio,
                        "guidance_scale": guidance,
                        "num_inference_steps": steps,
                        "enable_safety_checker": safety_checker,
                        "safety_tolerance": "2" # Mniej restrykcyjny
                    },
                )
                
                st.write("Rendering image...")
                result = handler.get()
                image_url = result['images'][0]['url']
                
                status.update(label="✅ Generation Complete!", state="complete", expanded=False)
                
                # Wyświetlanie wyniku
                st.image(image_url, use_container_width=True)
                
                # Sekcja pobierania
                st.success("Your image is ready!")
                st.markdown(f"**[📥 Download High Resolution Image]({image_url})**")
                
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Something went wrong: {e}")