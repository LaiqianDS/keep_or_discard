from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image, ImageOps
import streamlit as st
import streamlit.components.v1 as components
import shutil

CARD_CSS = """
<style>
:root {
  --bg: #0b0c10;
  --fg: #e5e7eb;
  --muted: #9aa0aa;
  --accent: #8b5cf6;
  --soft: #111217;
  --soft-2: #151722;
  --border: #232533;
  --good: #16a34a;
  --bad: #dc2626;
}

html, body, [data-testid="stAppViewContainer"] { background-color: var(--bg) !important; }
[data-testid="stHeader"] { background: transparent !important; }
h1, h2, h3, h4, h5, h6, p, span, label { color: var(--fg) !important; }

.card {
  position: relative;
  background: linear-gradient(180deg, var(--soft) 0%, var(--soft-2) 100%);
  border: 1px solid var(--border);
  border-radius: 18px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.35);
  padding: 18px;
  transition: box-shadow 200ms ease, border-color 200ms ease;
}
.card.flash-left { box-shadow: 0 0 0 2px rgba(220,38,38,0.5), 0 10px 30px rgba(0,0,0,0.35); }
.card.flash-right{ box-shadow: 0 0 0 2px rgba(22,163,74,0.5), 0 10px 30px rgba(0,0,0,0.35); }

.badge {
  display: inline-block;
  font-size: 12px;
  padding: 4px 10px;
  color: var(--fg);
  background: #1f2430;
  border: 1px solid var(--border);
  border-radius: 999px;
}
.counter {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px; border: 1px solid var(--border); border-radius: 999px;
  background: #131522; font-size: 13px; color: var(--fg);
}
.keyhint {
  font-size: 12px; color: var(--muted);
  border: 1px solid var(--border); background: #151826;
  padding: 2px 6px; border-radius: 6px; margin-left: 6px;
}
hr { border: none; border-top: 1px solid var(--border); margin: 8px 0 16px 0; }

/* Botones */
.stButton>button {
  width: 100%; border-radius: 14px; padding: 10px 14px;
  border: 1px solid var(--border); background: #141728; color: var(--fg);
  transition: transform 80ms ease, background 150ms ease, border-color 150ms ease;
}
.stButton>button:hover { transform: translateY(-1px); border-color: #2f3346; }
.btn-left>button:hover { background: rgba(220,38,38,0.08); }
.btn-right>button:hover { background: rgba(22,163,74,0.08); }
.btn-undo>button:hover { background: rgba(139,92,246,0.12); }

/* Overlay breve de feedback */
.flash-overlay {
  position: absolute; inset: 0; pointer-events: none;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; letter-spacing: 0.08em;
  opacity: 0; transform: scale(0.98);
  transition: opacity 180ms ease, transform 180ms ease;
}
.flash-overlay.show { opacity: 1; transform: scale(1); }
.flash-overlay .label {
  padding: 10px 16px; border-radius: 999px; border: 1px solid var(--border);
  backdrop-filter: blur(2px);
}
.flash-left .label { color: var(--bad); background: rgba(220,38,38,0.08); }
.flash-right .label{ color: var(--good); background: rgba(22,163,74,0.08); }
</style>
"""
st.markdown(CARD_CSS, unsafe_allow_html=True)


# ---------------------------- Config base ----------------------------
st.set_page_config(page_title="Tinder de fotos", page_icon="🖼️", layout="centered")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}


@st.cache_data(show_spinner=False)
def load_image_paths(media_dir: str = "media") -> List[Path]:
    p = Path(media_dir)
    if not p.exists():
        return []
    imgs = [x for x in p.iterdir() if x.suffix.lower() in IMAGE_EXTS and x.is_file()]
    imgs.sort(key=lambda x: x.name.lower())
    return imgs


def open_image(path: Path, max_width: int = 1200) -> Image.Image:
    img = Image.open(path).convert("RGB")
    if max(img.size) > max_width:
        img.thumbnail((max_width, max_width))
    return img


def stem_without_ext(path: Path) -> str:
    return path.stem


# ---------------------------- Estado ----------------------------
if "images" not in st.session_state:
    st.session_state.images: List[Path] = load_image_paths("media")
if "idx" not in st.session_state:
    st.session_state.idx: int = 0
if "mantener" not in st.session_state:
    st.session_state.mantener: List[str] = []
if "desechar" not in st.session_state:
    st.session_state.desechar: List[str] = []
if "history" not in st.session_state:
    st.session_state.history: List[Tuple[str, str, int]] = []
if "flash" not in st.session_state:
    st.session_state.flash: Optional[str] = None  # "left" | "right" | None
if "kb_seq" not in st.session_state:
    st.session_state.kb_seq = 0  # fuerza recrear listener


# ---------------------------- Helpers acciones ----------------------------
def can_advance() -> bool:
    return st.session_state.idx < len(st.session_state.images)


def current_path() -> Optional[Path]:
    if not can_advance():
        return None
    return st.session_state.images[st.session_state.idx]


def swipe_left() -> None:
    path = current_path()
    if not path:
        return
    target = stem_without_ext(path)
    st.session_state.desechar.append(target)
    st.session_state.history.append(("left", target, st.session_state.idx))
    st.session_state.idx += 1
    st.session_state.flash = "left"


def swipe_right() -> None:
    path = current_path()
    if not path:
        return
    target = stem_without_ext(path)
    st.session_state.mantener.append(target)
    st.session_state.history.append(("right", target, st.session_state.idx))
    st.session_state.idx += 1
    st.session_state.flash = "right"


def undo_last() -> None:
    if not st.session_state.history:
        return
    action, target, idx_before = st.session_state.history.pop()
    if action == "left":
        if target in st.session_state.desechar:
            st.session_state.desechar.remove(target)
    elif action == "right":
        if target in st.session_state.mantener:
            st.session_state.mantener.remove(target)
    st.session_state.idx = idx_before
    st.session_state.flash = None

def move_files(raw_type: str = "rw2") -> None:
    keep_path = Path("keep")
    discard_path = Path("discard")
    keep_path.mkdir(parents=True, exist_ok=True)
    discard_path.mkdir(parents=True, exist_ok=True)

    for file in st.session_state.mantener:
        src = Path("media") / f"{file}.jpg"
        raw = Path("media") / f"{file}.{raw_type}"
        dst = keep_path / f"{file}.jpg"
        raw_dst = keep_path / f"{file}.{raw_type}"
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        if raw.exists():
            raw_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(raw), str(raw_dst))

    for file in st.session_state.desechar:
        src = Path("media") / f"{file}.jpg"
        dst = discard_path / f"{file}.jpg"
        raw = Path("media") / f"{file}.{raw_type}"
        raw_dst = discard_path / f"{file}.{raw_type}"
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        if raw.exists():
            raw_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(raw), str(raw_dst))

# ---------------------------- UI ----------------------------
st.title("Keep or Discard")

imgs = st.session_state.images
total = len(imgs)
pos = st.session_state.idx + 1 if st.session_state.idx < total else total

c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1.2])
with c1:
    st.markdown(
        f"<div class='counter'>📁 {total} imágenes</div>", unsafe_allow_html=True
    )
with c2:
    st.markdown(
        f"<div class='counter'>❤️ {len(st.session_state.mantener)}</div>",
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f"<div class='counter'>❌ {len(st.session_state.desechar)}</div>",
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(f"<div class='counter'>📍 {pos}/{total}</div>", unsafe_allow_html=True)

st.write("---")

if total == 0:
    st.info("No se encontraron imágenes en `./media`. Añade archivos .jpg/.png/.webp…")
else:
    path = current_path()
    if path is None:
        st.success("Has terminado 🎉. Revisa/descarga las listas o usa **Deshacer**.")
    else:
        img = open_image(path)
        img = ImageOps.exif_transpose(img)
        st.image(img, width="stretch", caption=f"{path.name}")

        # Botones
        a1, a2, a3 = st.columns([1, 1, 1])
        with a1:
            if st.container().button(
                "Desechar",
                width="stretch",
                key="btn_left",
                on_click=swipe_left,
            ):
                st.rerun()
        with a2:
            if st.container().button(
                "Deshacer",
                width="stretch",
                key="btn_undo",
                disabled=(len(st.session_state.history) == 0),
                on_click=undo_last,
            ):
                st.rerun()
        with a3:
            if st.container().button(
                "Mantener",
                width="stretch",
                key="btn_right",
                on_click=swipe_right,
            ):
                st.rerun()

st.button("Mover archivos", width="stretch", on_click=move_files)

st.write("")

with st.expander("📋 Ver lista MANTENER (stems)"):
    mantener = st.session_state.mantener
    if mantener:
        st.code("\n".join(mantener), language="text")
    else:
        st.caption("Vacío.")

with st.expander("🗑️ Ver lista DESECHAR (rutas)"):
    desechar = st.session_state.desechar
    if desechar:
        st.code("\n".join(desechar), language="text")
    else:
        st.caption("Vacío.")

# Listener

def read_html():
    with open("src/index.html") as f:
        return f.read()


components.html(read_html(), height=0, width=0)
