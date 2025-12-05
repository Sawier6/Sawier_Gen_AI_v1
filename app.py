import streamlit as st
import fal_client
import os

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Firmowy Generator AI", page_icon="✨", layout="centered")

# --- PROSTE HASŁO (DLA BEZPIECZEŃSTWA W FIRMIE) ---
# Ustaw hasło w "Secrets" na serwerze lub wpisz je tutaj na sztywno (mniej bezpieczne)
ACCESS_PASSWORD = os.environ.get("APP_PASSWORD", "firma123") 

def check_password():
    """Zwraca True, jeśli użytkownik wpisał poprawne hasło."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.text_input("🔑 Podaj hasło dostępu:", type="password", key="password_input", on_change=password_entered)
    return False

def password_entered():
    if st.session_state["password_input"] == ACCESS_PASSWORD:
        st.session_state.password_correct = True
        del st.session_state["password_input"]
    else:
        st.error("Błędne hasło.")

if not check_password():
    st.stop()  # Zatrzymaj aplikację, jeśli hasło nie zostało podane

# --- GŁÓWNA APLIKACJA (Widoczna po wpisaniu hasła) ---

# Nagłówek
st.title("✨ Nasz Firmowy Kreator")
st.markdown("Wpisz prompt, wybierz format i wygeneruj obraz na koszt firmy.")

# Panel boczny (Ustawienia)
with st.sidebar:
    st.header("⚙️ Parametry")
    
    # Wybór modelu (możesz tu dodać inne modele z Fal.ai)
    model_choice = st.selectbox(
        "Model AI", 
        ["fal-ai/flux/dev", "fal-ai/flux/schnell"], 
        index=0
    )
    
    aspect_ratio = st.selectbox(
        "Format obrazu",
        options=["square_hd", "square", "portrait_4_3", "portrait_16_9", "landscape_16_9"],
        index=4
    )
    
    guidance = st.slider("Kreatywność (Guidance Scale)", 1.0, 10.0, 3.5)
    
    # Pobranie klucza API z sekretów serwera
    api_key = st.secrets.get("FAL_KEY")

# Główny formularz
prompt = st.text_area("Opis obrazka (Prompt):", height=120, placeholder="Np. nowoczesne biurowiec ze szkła i stali, słoneczny dzień, styl fotorealistyczny...")

col1, col2 = st.columns([1, 2])
with col1:
    generate_btn = st.button("🚀 Generuj", type="primary", use_container_width=True)

# Logika generowania
if generate_btn:
    if not api_key:
        st.error("❌ Błąd konfiguracji: Brak klucza API w systemie.")
    elif not prompt:
        st.warning("⚠️ Wpisz opis obrazka.")
    else:
        with st.spinner('⏳ AI przetwarza... (to potrwa ok. 3-5 sekund)'):
            try:
                os.environ["FAL_KEY"] = api_key
                
                # Wywołanie API Fal.ai
                handler = fal_client.submit(
                    model_choice,
                    arguments={
                        "prompt": prompt,
                        "image_size": aspect_ratio,
                        "guidance_scale": guidance,
                        "num_inference_steps": 28,  # Dla Flux Dev
                        "enable_safety_checker": True # Bezpieczeństwo w korpo
                    },
                )
                
                result = handler.get()
                image_url = result['images'][0]['url']
                
                st.image(image_url, caption=f"Prompt: {prompt}", use_column_width=True)
                
                # Przycisk pobierania (Streamlit nie pobiera bezpośrednio, ale dajemy link)
                st.markdown(f"[📥 Kliknij tutaj, aby pobrać w pełnej jakości]({image_url})")
                st.success("Gotowe!")
                
            except Exception as e:
                st.error(f"Wystąpił błąd: {e}")

st.markdown("---")
st.caption("Internal Tool | Powered by Fal.ai Flux")