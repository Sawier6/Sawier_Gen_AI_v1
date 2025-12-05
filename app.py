import streamlit as st
import fal_client
import os
import base64
import re

# --- KONFIGURACJA STRONY ---
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
    /* Ukrycie stopki Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- FUNKCJE POMOCNICZE ---

def load_and_color_svg(file_path, new_color="#fa660f"):
    """Wczytuje SVG i zmienia kolor czarny na wybrany."""
    try:
        with open(file_path, "r") as f:
            svg_content = f.read()
        
        # Prosta zamiana kolorów (zamienia black i hex #000000)
        # Możesz dodać więcej wariantów, jeśli logo ma inne odcienie
        svg_content = re.sub(r'fill="[^"]*"', f'fill="{new_color}"', svg_content)
        svg_content = svg_content.replace("black", new_color)
        svg_content = svg_content.replace("#000000", new_color)
        svg_content = svg_content.replace("#000", new_color)
        
        return svg_content
    except Exception as e:
        return None

def encode_image(uploaded_file):
    """Zamienia wgrany plik na format zrozumiały dla API (base64)."""
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        base64_str = base64.b64encode(bytes_data).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_str}"
    return None

# --- ZABEZPIECZENIE HASŁEM ---
ACCESS_PASSWORD = st.secrets.get("APP_PASSWORD", os.environ.get("APP_PASSWORD", ""))

def check_password():
    """Prosty mechanizm logowania."""
    if not ACCESS_PASSWORD:
        return True # Jeśli hasło nie ustawione, wpuszczamy wszystkich
        
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    
    if st.session_state.password_correct:
        return True
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.info("🔒 Aplikacja chroniona hasłem")
        pwd = st.text_input("Podaj hasło:", type="password")
        if pwd == ACCESS_PASSWORD:
            st.session_state.password_correct = True
            st.rerun()
        elif pwd:
            st.error("Błędne hasło")
    return False

if not check_password():
    st.stop()

# --- SIDEBAR (Ustawienia) ---
with st.sidebar:
    # 1. LOGO ZMIENIONE NA POMARAŃCZOWO
    logo_svg = load_and_color_svg("strategy_logo_black.svg", "#fa660f")
    if logo_svg:
        # Renderujemy SVG jako HTML
        st.markdown(f'<div style="max-width: 200px; margin-bottom: 20px;">{logo_svg}</div>', unsafe_allow_html=True)
    else:
        st.header("🍊 YOUR BRAND")

    st.divider()
    st.subheader("⚙️ Ustawienia Modelu")

    # 2. WYBÓR MODELI (Flux 2 = Pro 1.1)
    model_alias = st.selectbox(
        "Wybierz Model",
        options=["Flux 1.1 Pro (Najlepsza jakość)", "Flux Dev (Standard)", "Nano Banana Pro (Szybki)"],
        index=0
    )
    
    # Mapowanie nazw na prawdziwe ID modeli z fal.ai
    model_map = {
        "Flux 1.1 Pro (Najlepsza jakość)": "fal-ai/flux-pro/v1.1",
        "Flux Dev (Standard)": "fal-ai/flux/dev",
        # Uwaga: Nano Banana Pro to nazwa wymyślona, podpinam tu szybki model SDXL jako przykład
        "Nano Banana Pro (Szybki)": "fal-ai/fast-lightning-sdxl" 
    }
    selected_model_id = model_map[model_alias]

    # 3. ASPECT RATIO (9x16, 1x1, 16x9)
    ratio_alias = st.radio(
        "Proporcje obrazu",
        options=["9:16 (Story)", "1:1 (Kwadrat)", "16:9 (Poziom)"],
        index=2
    )
    
    ratio_map = {
        "9:16 (Story)": "portrait_16_9", # Fal używa takiej nomenklatury dla pionu
        "1:1 (Kwadrat)": "square",
        "16:9 (Poziom)": "landscape_16_9"
    }
    selected_ratio = ratio_map[ratio_alias]

    # 4. REFERENCE IMAGES (Do 6 plików)
    st.divider()
    st.subheader("🖼️ Reference Images")
    uploaded_refs = st.file_uploader(
        "Wgraj zdjęcia referencyjne (max 6)", 
        accept_multiple_files=True,
        type=['png', 'jpg', 'jpeg']
    )
    
    if uploaded_refs and len(uploaded_refs) > 6:
        st.warning("⚠️ Maksymalnie 6 plików! Użyję tylko pierwszych 6.")
        uploaded_refs = uploaded_refs[:6]

# --- GŁÓWNA STRONA ---
st.title("✨ Generator AI")
st.caption(f"Wybrany model: {model_alias}")

# Pole promptu
prompt = st.text_area("Opisz co chcesz wygenerować:", height=120, placeholder="Np. Futurystyczny samochód sportowy w kolorze pomarańczowym, kinowe oświetlenie...")

col1, col2 = st.columns([1, 3])
with col1:
    generate_btn = st.button("🚀 GENERUJ", use_container_width=True)

# --- LOGIKA GENEROWANIA ---
if generate_btn:
    api_key = st.secrets.get("FAL_KEY")
    
    if not api_key:
        st.error("Błąd: Brak klucza API w sekcji Secrets.")
    elif not prompt:
        st.warning("Wpisz opis obrazka.")
    else:
        with st.status("🍊 AI pracuje...", expanded=True) as status:
            try:
                os.environ["FAL_KEY"] = api_key
                
                # Przygotowanie argumentów
                arguments = {
                    "prompt": prompt,
                    "image_size": selected_ratio,
                    "num_inference_steps": 28,
                    "guidance_scale": 3.5,
                    "safety_tolerance": "2"
                }

                # Obsługa Reference Images (Image-to-Image)
                # WAŻNE: Standardowe API Flux obsługuje zazwyczaj 1 obraz jako input (img2img).
                # Jeśli wgrano zdjęcia, dodajemy PIERWSZE jako image_url.
                if uploaded_refs:
                    st.write(f"Przetwarzanie {len(uploaded_refs)} zdjęć referencyjnych...")
                    main_ref_image = encode_image(uploaded_refs[0])
                    arguments["image_url"] = main_ref_image
                    arguments["strength"] = 0.75 # Siła wpływu zdjęcia (do dostosowania)
                    
                    # Jeśli używasz modelu Dev, przełączamy na img2img endpoint (często wymagane)
                    if "dev" in selected_model_id:
                        selected_model_id = "fal-ai/flux/dev/image-to-image"
                        
                    st.info("ℹ️ Używam pierwszego zdjęcia jako głównego odniesienia (Standard API Limit).")

                st.write("Wysyłanie do klastra GPU...")
                
                handler = fal_client.submit(
                    selected_model_id,
                    arguments=arguments,
                )
                
                result = handler.get()
                image_url = result['images'][0]['url']
                
                status.update(label="✅ Gotowe!", state="complete", expanded=False)
                
                st.image(image_url, use_container_width=True)
                st.markdown(f"**[📥 Pobierz obraz w pełnej jakości]({image_url})**")
                
            except Exception as e:
                status.update(label="❌ Błąd", state="error")
                st.error(f"Wystąpił problem: {e}")
                # Debugging - wyświetl błąd jeśli to problem z modelem
                if "404" in str(e):
                    st.error("Wybrany model nie odpowiada. Sprawdź ID modelu w kodzie.")