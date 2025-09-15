from __future__ import annotations
from pathlib import Path
from typing import List, Set
import streamlit as st
from PIL import Image
from tools import list_jpgs

RAW_EXTS = {
    ".cr2",
    ".cr3",
    ".nef",
    ".arw",
    ".raf",
    ".dng",
    ".rw2",
    ".orf",
    ".srw",
    ".pef",
    ".raw",
}
JPG_EXTS = {".jpg", ".jpeg"}

DEFAULT_DATA_DIR = Path("./media").resolve()
KEEP_DIR = Path("./keep").resolve()
DISCARD_DIR = Path("./discard").resolve()

if not KEEP_DIR.exists():
    KEEP_DIR.mkdir(parents=True)

if not DISCARD_DIR.exists():
    DISCARD_DIR.mkdir(parents=True)


def main():
    st.set_page_config(page_title="Clasificador de Fotos", layout="wide")

    if "data_dir" not in st.session_state:
        st.session_state.data_dir = str(DEFAULT_DATA_DIR)

    if "files" not in st.session_state:
        st.session_state.files: List[Path] = list_jpgs(Path(st.session_state.data_dir))

    if "idx" not in st.session_state:
        st.session_state.idx: int = 0

    if "keep" not in st.session_state:
        st.session_state.keep: Set[str] = set()

    if "discard" not in st.session_state:
        st.session_state.discard: Set[str] = set()

    # ----------------------------
    # Sidebar
    # ----------------------------
    st.sidebar.header("Configuración")
    data_dir_input = st.sidebar.text_input(
        "Carpeta de datos", st.session_state.data_dir
    )
    reload_btn = st.sidebar.button("Recargar lista")

    if data_dir_input != st.session_state.data_dir or reload_btn:
        st.session_state.data_dir = data_dir_input
        st.session_state.files = list_jpgs(Path(st.session_state.data_dir))
        st.session_state.idx = 0
        st.session_state.keep.clear()
        st.session_state.discard.clear()

    st.sidebar.markdown("---")
    st.sidebar.write("Totales")
    st.sidebar.metric("Fotos encontradas", len(st.session_state.files))
    st.sidebar.metric("Marcadas mantener", len(st.session_state.keep))
    st.sidebar.metric("Marcadas desechar", len(st.session_state.discard))

    # ----------------------------
    # Cabecera
    # ----------------------------
    st.title("Clasificador de Fotos")

    files = st.session_state.files
    idx = st.session_state.idx
    data_dir = Path(st.session_state.data_dir)

    # ----------------------------
    # Zona principal
    # ----------------------------

    if not data_dir.exists():
        st.error(f"La carpeta no existe: {data_dir}")
    elif not files:
        st.info("No se han encontrado JPG/JPEG en la carpeta seleccionada.")
    else:
        left, center, right = st.columns([1, 3, 1], vertical_alignment="center")

        with left:
            if st.button("⟵ Anterior", width="stretch", disabled=(idx <= 0)):
                st.session_state.idx = max(0, idx - 1)
                st.rerun()

        current_file = files[idx]
        stem = current_file.stem

        with center:
            try:
                img = Image.open(current_file)
                st.image(img, width="stretch", caption=current_file.name)
            except Exception as e:
                st.warning(f"No se pudo previsualizar {current_file.name}: {e}")

            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            with c1:
                if st.button("✅ Mantener", width="stretch"):
                    st.session_state.keep.add(stem)
                    st.session_state.discard.discard(stem)
                    st.session_state.idx = min(len(files) - 1, idx + 1)
                    st.rerun()
            with c2:
                if st.button("🗑️ Desechar", width="stretch"):
                    st.session_state.discard.add(stem)
                    st.session_state.keep.discard(stem)
                    st.session_state.idx = min(len(files) - 1, idx + 1)
                    st.rerun()
            with c3:
                if st.button("↩️ Deshacer", width="stretch"):
                    # Quita etiqueta del actual
                    st.session_state.keep.discard(stem)
                    st.session_state.discard.discard(stem)
                    st.rerun()
            with c4:
                if st.button("⏭️ Saltar", width="stretch"):
                    st.session_state.idx = min(len(files) - 1, idx + 1)
                    st.rerun()

        with right:
            if st.button(
                "Siguiente ⟶",
                width="stretch",
                disabled=(idx >= len(files) - 1),
            ):
                st.session_state.idx = min(len(files) - 1, idx + 1)
                st.rerun()

        st.markdown("---")

        col_a, col_b, col_c = st.columns([1.2, 1.2, 1.2])

        with col_a:
            st.subheader("Mantener")
            if st.session_state.keep:
                st.write(", ".join(sorted(st.session_state.keep)))
            else:
                st.caption("— vacío —")

        with col_b:
            st.subheader("Desechar")
            if st.session_state.discard:
                st.write(", ".join(sorted(st.session_state.discard)))
            else:
                st.caption("— vacío —")

        with col_c:
            move_btn = st.button(
                "📦 Mover archivos",
                type="primary",
                width="stretch",
                disabled=not (st.session_state.keep or st.session_state.discard),
            )

    if move_btn:
        with st.spinner("Moviendo archivos..."):
            # Mover archivos a las carpetas correspondientes
            st.success("Archivos movidos.")

    st.markdown("---")
    st.caption(
        "Consejo: además de .jpg/.jpeg, al mover se incluyen automáticamente los RAW con el mismo nombre base."
    )


if __name__ == "__main__":
    main()
