import streamlit as st
from PIL import Image, ImageFilter, ImageEnhance
import io
from typing import Optional, Tuple
from rembg import remove, new_session
import requests
import base64

# ==========================================
# STREAMLIT PAGE CONFIGURATION
# ==========================================
# MUST be the very first Streamlit command in the script!
st.set_page_config(page_title="Local Product Photo Studio", page_icon="✨", layout="wide")

# ==========================================
# CONFIGURATION
# ==========================================
# OPTIMIZATION: Pull API key from Streamlit Secrets to prevent exposing it in public repos
# Set this up in Streamlit Cloud Dashboard -> App Settings -> Secrets
# Example secret format: IMGBB_API_KEY = "your_actual_key_here"
IMGBB_API_KEY = st.secrets.get("IMGBB_API_KEY", "YOUR_API_KEY_HERE") 

# OPTIMIZATION: Reduced from 2048 to 1024 to prevent cloud server crashes
MAX_IMAGE_SIZE = 1024 
MAX_FILE_SIZE_MB = 10

BACKGROUND_STYLES = {
    "Pure White": (255, 255, 255, 255),
    "Soft Gray": (240, 240, 240, 255),
    "Natural White": (250, 250, 248, 255),
    "Transparent": (0, 0, 0, 0)
}

LIGHTING_PRESETS = [
    "Original (No Change)",
    "E-commerce Studio (Brighter, Crisp)",
    "Dramatic (High Contrast)",
    "Soft & Diffused (Low Contrast, Bright)"
]

SHADOW_STYLES = [
    "No Shadow",
    "Realistic Drop Shadow",
    "Contact Shadow",
    "Soft Float Shadow"
]

# ==========================================
# CACHED AI MODEL (CLOUD OPTIMIZATION)
# ==========================================
@st.cache_resource
def get_rembg_session():
    """Loads the lightweight AI model once and keeps it in memory to drastically speed up processing."""
    return new_session("u2netp")

# ==========================================
# PROCESSING FUNCTIONS
# ==========================================
def optimize_image(image: Image.Image) -> Image.Image:
    """Optimize image size for processing."""
    width, height = image.size
    max_dim = max(width, height)

    if max_dim > MAX_IMAGE_SIZE:
        scale = MAX_IMAGE_SIZE / max_dim
        new_width = int(width * scale)
        new_height = int(height * scale)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    return image

def apply_shadow(product_img: Image.Image, shadow_style: str) -> Image.Image:
    """Programmatically generate a shadow based on the product's alpha channel."""
    if shadow_style == "No Shadow":
        return product_img

    alpha = product_img.split()[3]
    shadow = Image.new('RGBA', product_img.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 120), mask=alpha) 

    if shadow_style == "Realistic Drop Shadow":
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=15))
        offset_x, offset_y = 10, 20
    elif shadow_style == "Soft Float Shadow":
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=25))
        offset_x, offset_y = 0, 35
    elif shadow_style == "Contact Shadow":
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=5))
        offset_x, offset_y = 0, 5

    shadow_canvas = Image.new('RGBA', product_img.size, (0, 0, 0, 0))
    shadow_canvas.paste(shadow, (offset_x, offset_y))

    result = Image.alpha_composite(shadow_canvas, product_img)
    return result

def apply_lighting(img: Image.Image, style: str) -> Image.Image:
    """Apply math-based photo enhancements to simulate lighting."""
    if style == "Original (No Change)":
        return img
        
    enhancer_c = ImageEnhance.Contrast(img)
    enhancer_b = ImageEnhance.Brightness(img)
    
    if style == "E-commerce Studio (Brighter, Crisp)":
        img = enhancer_b.enhance(1.1)
        img = enhancer_c.enhance(1.05)
    elif style == "Dramatic (High Contrast)":
        img = enhancer_c.enhance(1.3)
    elif style == "Soft & Diffused (Low Contrast, Bright)":
        img = enhancer_c.enhance(0.9)
        img = enhancer_b.enhance(1.05)
        
    return img

def process_product_image(image: Image.Image, bg_name: str, shadow_name: str, lighting_name: str) -> Image.Image:
    """Main processing pipeline: Remove BG -> Light -> Shadow -> Add new BG"""
    
    # Use the cached, fast AI model
    session = get_rembg_session()
    no_bg_image = remove(image, session=session)
    
    lit_image = apply_lighting(no_bg_image, lighting_name)
    shadowed_image = apply_shadow(lit_image, shadow_name)
    
    if bg_name == "Transparent":
        return shadowed_image
        
    bg_color = BACKGROUND_STYLES[bg_name]
    final_canvas = Image.new('RGBA', shadowed_image.size, bg_color)
    final_image = Image.alpha_composite(final_canvas, shadowed_image)
    
    return final_image

def image_to_bytes(image: Image.Image, format: str = "JPEG", quality: int = 95) -> bytes:
    """Convert PIL Image to bytes."""
    buf = io.BytesIO()
    if format == "JPEG":
        image = image.convert("RGB")
    image.save(buf, format=format, quality=quality if format == "JPEG" else None)
    return buf.getvalue()

def upload_to_imgbb(image_bytes: bytes, api_key: str) -> str:
    """Uploads image bytes to ImgBB and returns the public URL."""
    url = "https://api.imgbb.com/1/upload"
    encoded_image = base64.b64encode(image_bytes).decode('utf-8')
    
    payload = {
        "key": api_key,
        "image": encoded_image
    }
    
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status() 
        data = response.json()
        if data.get("success"):
            return data["data"]["url"] 
        else:
            return f"Error: {data.get('status_code')}"
    except Exception as e:
        return f"Upload failed: {e}"

# ==========================================
# STREAMLIT UI
# ==========================================
st.markdown("""
<style>
    .main-header { text-align: center; padding: 1rem 0; }
    .stDownloadButton button, .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>✨ Local Product Photo Studio</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>100% Free, offline background removal and studio styling.</p>", unsafe_allow_html=True)

# Sidebar setup
with st.sidebar:
    st.header("⚙️ Settings")
    
    st.subheader("🎨 Style Options")
    background_choice = st.selectbox("Background", options=list(BACKGROUND_STYLES.keys()))
    lighting_choice = st.selectbox("Lighting Adjustments", options=LIGHTING_PRESETS)
    shadow_choice = st.selectbox("Shadow Style", options=SHADOW_STYLES)
    
    st.divider()
    
    with st.expander("🔧 Output Options"):
        output_format = st.selectbox("Format", options=["JPEG (Smaller)", "PNG (Lossless)"])
        if output_format == "JPEG (Smaller)":
            jpeg_quality = st.slider("JPEG Quality", 80, 100, 95)
            if background_choice == "Transparent":
                st.warning("JPEG does not support transparency. Background will turn black.")

# Main App Layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("📤 Upload Image")
    uploaded_file = st.file_uploader("Choose a product image", type=["jpg", "jpeg", "png", "webp"])

if 'processed_image' not in st.session_state:
    st.session_state.processed_image = None
if 'processing_done' not in st.session_state:
    st.session_state.processing_done = False

if uploaded_file is not None:
    raw_image = Image.open(uploaded_file).convert("RGBA")
    
    with col1:
        st.image(raw_image, caption="Original Image", use_column_width=True)
        st.divider()
        
        process_button = st.button("🎨 Process Image Locally", type="primary", use_container_width=True)
        
        if process_button:
            st.session_state.processing_done = False
            
            with st.spinner("🤖 Extracting background and applying styles..."):
                optimized_image = optimize_image(raw_image)
                
                try:
                    final_result = process_product_image(
                        optimized_image, 
                        background_choice, 
                        shadow_choice, 
                        lighting_choice
                    )
                    st.session_state.processed_image = final_result
                    st.session_state.processing_done = True
                    st.success("✅ Transformation complete!")
                except Exception as e:
                    st.error(f"❌ Processing error: {e}")

    # Display Results and Download/Share options
    if st.session_state.processing_done and st.session_state.processed_image:
        with col2:
            st.subheader("📊 Result")
            st.image(st.session_state.processed_image, caption="Enhanced Product", use_column_width=True)
            
            st.divider()
            
            # Setup image bytes for download and upload
            format_str = "JPEG" if output_format == "JPEG (Smaller)" else "PNG"
            file_ext = format_str.lower()
            mime_type = f"image/{file_ext}"
            quality = jpeg_quality if format_str == "JPEG" else None
            
            image_bytes = image_to_bytes(st.session_state.processed_image, format=format_str, quality=quality)
            
            # 3 Columns for the action bar
            dl_col1, dl_col2, dl_col3 = st.columns([2, 1, 2])
            
            with dl_col1:
                st.download_button(
                    label=f"⬇️ Download {format_str}",
                    data=image_bytes,
                    file_name=f"studio_{uploaded_file.name.rsplit('.', 1)[0]}.{file_ext}",
                    mime=mime_type,
                    use_container_width=True
                )
                
            with dl_col2:
                file_size_kb = len(image_bytes) / 1024
                st.metric("File Size", f"{file_size_kb:.1f} KB")
                
            with dl_col3:
                if st.button("🔗 Create Shareable Link", use_container_width=True):
                    if IMGBB_API_KEY == "YOUR_API_KEY_HERE" or not IMGBB_API_KEY.strip():
                        st.error("Missing ImgBB API key! Set it in Streamlit Cloud Secrets.")
                    else:
                        with st.spinner("Uploading to cloud..."):
                            link = upload_to_imgbb(image_bytes, IMGBB_API_KEY)
                            
                            if link.startswith("http"):
                                st.success("Success!")
                                st.code(link, language="text")
                            else:
                                st.error(link)
else:
    st.info("👆 Upload a product image to get started!")
