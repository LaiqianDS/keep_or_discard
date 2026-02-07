from pathlib import Path
from typing import List, Tuple, Optional, Dict
import json
import shutil
import csv
from datetime import datetime

from PIL import Image, ImageOps
import streamlit as st
import streamlit.components.v1 as components

from tools import RAW_EXTS

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
SESSION_VERSION = 2


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
    return img


def session_file() -> Path:
    return Path(".keep_or_discard") / "session_state.json"


def save_session_state() -> None:
    payload = {
        "version": SESSION_VERSION,
        "source_dir": st.session_state.source_dir,
        "mode": st.session_state.mode,
        "idx": st.session_state.idx,
        "mantener": st.session_state.mantener,
        "desechar": st.session_state.desechar,
        "history": st.session_state.history,
    }
    session_path = session_file()
    session_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = session_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    tmp_path.replace(session_path)


def load_session_state() -> None:
    session_path = session_file()
    if not session_path.exists():
        return
    try:
        payload = json.loads(session_path.read_text())
    except json.JSONDecodeError:
        return
    version = int(payload.get("version", 1))
    st.session_state.source_dir = payload.get("source_dir", "media")
    st.session_state.mode = payload.get("mode", "copy")
    st.session_state.idx = int(payload.get("idx", 0))
    mantener = list(payload.get("mantener", []))
    desechar = list(payload.get("desechar", []))
    history = list(payload.get("history", []))
    if version < 2:
        # v1 stored stems; resolve to actual filenames in source dir
        source_dir = Path(st.session_state.source_dir)
        imgs = load_image_paths(str(source_dir))
        stem_map = {}
        for p in imgs:
            stem_map.setdefault(p.stem, p.name)
        mantener = [stem_map.get(x, f"{x}.jpg") for x in mantener]
        desechar = [stem_map.get(x, f"{x}.jpg") for x in desechar]
        history = [(h[0], stem_map.get(h[1], f"{h[1]}.jpg"), h[2]) for h in history]
    st.session_state.mantener = mantener
    st.session_state.desechar = desechar
    st.session_state.history = history


def reset_session_state() -> None:
    st.session_state.idx = 0
    st.session_state.mantener = []
    st.session_state.desechar = []
    st.session_state.history = []
    st.session_state.last_action = None
    session_path = session_file()
    if session_path.exists():
        session_path.unlink()


def stem_without_ext(path: Path) -> str:
    return path.stem


def resolve_source_file(name: str, source_dir: Path) -> Optional[Path]:
    direct = source_dir / name
    if direct.exists():
        return direct
    stem = Path(name).stem
    # Try to match by stem across known image files
    for p in st.session_state.images:
        if p.stem == stem:
            return p
    return None


def ensure_session_flags() -> None:
    if "session_loaded" not in st.session_state:
        st.session_state.session_loaded = False


# ---------------------------- Estado ----------------------------
if "images" not in st.session_state:
    st.session_state.images = load_image_paths("media")
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "mantener" not in st.session_state:
    st.session_state.mantener = []
if "desechar" not in st.session_state:
    st.session_state.desechar = []
if "history" not in st.session_state:
    st.session_state.history = []
if "flash" not in st.session_state:
    st.session_state.flash = None  # "left" | "right" | None
if "kb_seq" not in st.session_state:
    st.session_state.kb_seq = 0  # fuerza recrear listener
if "fit_to_window" not in st.session_state:
    st.session_state.fit_to_window = True
if "dry_run" not in st.session_state:
    st.session_state.dry_run = True
if "confirm_move" not in st.session_state:
    st.session_state.confirm_move = False
if "confirm_cleanup" not in st.session_state:
    st.session_state.confirm_cleanup = False
if "mode" not in st.session_state:
    st.session_state.mode = "copy"
if "source_dir" not in st.session_state:
    st.session_state.source_dir = "media"
if "include_ambiguous_raws" not in st.session_state:
    st.session_state.include_ambiguous_raws = True
if "last_action" not in st.session_state:
    st.session_state.last_action = None

ensure_session_flags()

session_exists = session_file().exists()
if session_exists and not st.session_state.session_loaded:
    st.warning("Se encontró una sesión guardada.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Reabrir sesión", width="stretch"):
            load_session_state()
            st.session_state.images = load_image_paths(st.session_state.source_dir)
            st.session_state.session_loaded = True
            st.rerun()
    with c2:
        if st.button("Empezar desde cero", width="stretch"):
            reset_session_state()
            st.session_state.images = load_image_paths(st.session_state.source_dir)
            st.session_state.session_loaded = True
            st.rerun()
else:
    if not st.session_state.session_loaded:
        load_session_state()
        st.session_state.images = load_image_paths(st.session_state.source_dir)
        st.session_state.session_loaded = True


# ---------------------------- Helpers acciones ----------------------------
def can_advance() -> bool:
    return st.session_state.idx < len(st.session_state.images)


def persist_if_needed() -> None:
    save_session_state()


def preload_next_image() -> None:
    next_idx = st.session_state.idx + 1
    if next_idx < len(st.session_state.images):
        try:
            Image.open(st.session_state.images[next_idx]).convert("RGB")
        except OSError:
            pass


def current_path() -> Optional[Path]:
    if not can_advance():
        return None
    return st.session_state.images[st.session_state.idx]


def swipe_left() -> None:
    path = current_path()
    if not path:
        return
    target = path.name
    st.session_state.desechar.append(target)
    st.session_state.history.append(("left", target, st.session_state.idx))
    st.session_state.idx += 1
    st.session_state.flash = "left"
    persist_if_needed()
    preload_next_image()


def swipe_right() -> None:
    path = current_path()
    if not path:
        return
    target = path.name
    st.session_state.mantener.append(target)
    st.session_state.history.append(("right", target, st.session_state.idx))
    st.session_state.idx += 1
    st.session_state.flash = "right"
    persist_if_needed()
    preload_next_image()


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
    persist_if_needed()

def list_raw_matches(stem: str, source_dir: Path) -> List[Path]:
    matches = []
    for raw_ext in RAW_EXTS:
        raw = source_dir / f"{stem}{raw_ext}"
        if raw.exists():
            matches.append(raw)
    return matches


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    base = path.stem
    ext = path.suffix
    parent = path.parent
    i = 1
    while True:
        candidate = parent / f"{base}_{i}{ext}"
        if not candidate.exists():
            return candidate
        i += 1


def build_transfer_plan() -> Tuple[List[Tuple[Path, Path]], Dict[str, List[str]]]:
    source_dir = Path(st.session_state.source_dir)
    plan = []
    raw_report: Dict[str, List[str]] = {}

    def add_file(src: Optional[Path], dst: Path):
        if src and src.exists():
            plan.append((src, dst))

    for filename in st.session_state.mantener:
        src = resolve_source_file(filename, source_dir)
        dst = Path("keep") / filename
        add_file(src, dst)
        raw_matches = list_raw_matches(src.stem, source_dir) if src else []
        raw_report[filename] = [p.name for p in raw_matches] if src else []
        if len(raw_matches) > 1 and not st.session_state.include_ambiguous_raws:
            continue
        for raw in raw_matches:
            add_file(raw, Path("keep") / raw.name)

    for filename in st.session_state.desechar:
        src = resolve_source_file(filename, source_dir)
        dst = Path("discard") / filename
        add_file(src, dst)
        raw_matches = list_raw_matches(src.stem, source_dir) if src else []
        raw_report[filename] = [p.name for p in raw_matches] if src else []
        if len(raw_matches) > 1 and not st.session_state.include_ambiguous_raws:
            continue
        for raw in raw_matches:
            add_file(raw, Path("discard") / raw.name)

    return plan, raw_report


def total_size_bytes(pairs: List[Tuple[Path, Path]]) -> int:
    total = 0
    for src, _ in pairs:
        try:
            total += src.stat().st_size
        except OSError:
            pass
    return total


def format_bytes(num: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} PB"


def apply_action() -> None:
    if not st.session_state.confirm_move:
        st.warning("Confirma la casilla antes de ejecutar.")
        return

    keep_path = Path("keep")
    discard_path = Path("discard")
    keep_path.mkdir(parents=True, exist_ok=True)
    discard_path.mkdir(parents=True, exist_ok=True)

    for file in st.session_state.mantener:
        src = Path("media") / f"{file}.jpg"
        src2 = Path("media") / f"{file}.png"
        src3 = Path("media") / f"{file}.jpeg"
        raw = Path("media") / f"{file}.{raw_type}"
        dst = keep_path / f"{file}.jpg"
        raw_dst = keep_path / f"{file}.{raw_type}"
        srcs = [src, src2, src3]
        for src in srcs:
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
        if raw.exists():
            raw_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(raw), str(raw_dst))

    for file in st.session_state.desechar:
        src = Path("media") / f"{file}.jpg"
        src2 = Path("media") / f"{file}.png"
        src3 = Path("media") / f"{file}.jpeg"
        dst = discard_path / f"{file}.jpg"
        raw = Path("media") / f"{file}.{raw_type}"
        raw_dst = discard_path / f"{file}.{raw_type}"
        srcs = [src, src2, src3]
        for src in srcs:
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

with st.expander("⚙️ Preferencias rápidas"):
    st.session_state.fit_to_window = st.checkbox(
        "Ajustar imagen a ventana", value=st.session_state.fit_to_window
    )
    st.session_state.dry_run = st.checkbox(
        "Modo simulación (no mover archivos)", value=st.session_state.dry_run
    )
    st.session_state.mode = st.selectbox(
        "Modo de acción",
        options=["copy", "move"],
        format_func=lambda x: "Copiar a keep/discard" if x == "copy" else "Mover a keep/discard",
        index=0 if st.session_state.mode == "copy" else 1,
    )
    st.session_state.include_ambiguous_raws = st.checkbox(
        "Incluir RAWs cuando hay múltiples coincidencias",
        value=st.session_state.include_ambiguous_raws,
    )
    st.session_state.confirm_move = st.checkbox(
        "Confirmo que quiero ejecutar la acción", value=st.session_state.confirm_move
    )
    if st.button("Reiniciar sesión", width="stretch"):
        if st.session_state.session_loaded:
            reset_session_state()
            st.rerun()

if total == 0:
    st.info("No se encontraron imágenes en `./media`. Añade archivos .jpg/.png/.webp y recarga.")
else:
    path = current_path()
    if path is None:
        st.success("Has terminado 🎉. Revisa/descarga las listas o usa **Deshacer**.")
    else:
        img = open_image(path)
        img = ImageOps.exif_transpose(img)
        if st.session_state.fit_to_window:
            st.image(img, width="stretch", caption=f"{path.name}")
        else:
            st.image(img, caption=f"{path.name}")

        st.caption("Atajos: ←/A = Desechar · →/D/Espacio = Mantener · U/Z = Deshacer")

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

st.subheader("Resumen previo")
    plan, raw_report = build_transfer_plan()
keep_count = len(st.session_state.mantener)
discard_count = len(st.session_state.desechar)
total_files = len(plan)
size_bytes = total_size_bytes(plan)
impact = format_bytes(size_bytes) if st.session_state.mode == "copy" else "0 B"
    st.table(
        [
            {"Métrica": "Mantener", "Valor": str(keep_count)},
            {"Métrica": "Desechar", "Valor": str(discard_count)},
            {"Métrica": "Archivos a procesar (incl. RAW)", "Valor": str(total_files)},
            {"Métrica": "Impacto estimado en disco", "Valor": str(impact)},
        ]
    )
    if (keep_count + discard_count) > 0 and total_files == 0:
        st.warning("No se encontraron archivos para procesar. Revisa extensiones o sesión guardada.")

with st.expander("Ver ejemplos y RAWs detectados"):
    st.write("Ejemplos Mantener:")
    if st.session_state.mantener:
        st.code("\n".join(st.session_state.mantener[:5]), language="text")
    else:
        st.caption("Vacío.")
    st.write("Ejemplos Desechar:")
    if st.session_state.desechar:
        st.code("\n".join(st.session_state.desechar[:5]), language="text")
    else:
        st.caption("Vacío.")
    st.write("RAWs detectados por archivo:")
    if raw_report:
        lines = []
        for k, v in raw_report.items():
            if v:
                lines.append(f"{k}: {', '.join(v)}")
        if lines:
            st.code("\n".join(lines), language="text")
        else:
            st.caption("No se detectaron RAWs.")
    else:
        st.caption("No hay selección.")

if st.session_state.dry_run:
    st.warning("Modo simulación activo. Desactívalo para copiar o mover archivos.")

disable_execute = st.session_state.dry_run or (total_files == 0) or (not st.session_state.confirm_move)
st.button("Ejecutar acción", width="stretch", on_click=apply_action, disabled=disable_execute)

if st.session_state.last_action and st.session_state.last_action.get("mode") == "copy":
    st.session_state.confirm_cleanup = st.checkbox(
        "Confirmo que quiero limpiar originales (se moverán a discard/_originals)",
        value=st.session_state.confirm_cleanup,
    )
    st.button("Limpiar originales", width="stretch", on_click=cleanup_originals)

st.write("")

with st.expander("📋 Ver lista MANTENER (archivos)"):
    mantener = st.session_state.mantener
    if mantener:
        st.code("\n".join(mantener), language="text")
    else:
        st.caption("Vacío.")

with st.expander("🗑️ Ver lista DESECHAR (archivos)"):
    desechar = st.session_state.desechar
    if desechar:
        st.code("\n".join(desechar), language="text")
    else:
        st.caption("Vacío.")

if st.button("Exportar decisiones (CSV)", width="stretch"):
    export_dir = Path(".keep_or_discard") / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = export_dir / f"decisions_{timestamp}.csv"
    with export_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "decision"])
        for name in st.session_state.mantener:
            writer.writerow([name, "keep"])
        for name in st.session_state.desechar:
            writer.writerow([name, "discard"])
    st.success(f"Exportado a {export_path}")

# Listener

def read_html():
    with open("src/index.html") as f:
        return f.read()


components.html(read_html(), height=0, width=0)
