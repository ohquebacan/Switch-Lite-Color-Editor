import tkinter as tk
from tkinter import filedialog, colorchooser
import os
import sys
import hashlib
import struct
import shutil


def resource_path(rel):
    """Ruta a un recurso, funciona en dev y en el .exe de PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

# ---------------------------------------------------------------------------
# Prodify Dual — editor de color para Nintendo Switch (Normal) y Switch LITE
# Basado en PRODIFY (sthetix). Un solo programa con toggle de modo:
#   - Normal: Cuerpo (Main) + Borde (Bezel)  [como el PRODIFY original]
#   - Lite:   agrega Botones (Sub) + Color Model (preset two-tone Zacian)
# Recalcula CRC-16 por bloque y SHA-256 del cuerpo. Trabaja sobre PRODINFO
# DESCIFRADO (.dec / .bin). NO toca el serial ni el certificado.
# ---------------------------------------------------------------------------

SCRIPT_VERSION = "dual-1.0"

CRC_16_TABLE = [
    0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
    0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400
]

# Offsets CAL0 (Switchbrew + pruebas en consola)
OFF_MAIN  = 0x4240   # Cuerpo
OFF_BEZEL = 0x4230   # Borde / bisel
OFF_SUB   = 0x4220   # Botones / +-  (relevante en Lite)
COLORMODEL_OFFSET     = 0x4330

# key -> offset (el orden define filas)
COLOR_OFFSETS = {
    'Cuerpo (Main)':      OFF_MAIN,
    'Borde (Bezel)':      OFF_BEZEL,
    'Botones / +- (Sub)': OFF_SUB,
}
LITE_ONLY_COLORS = {'Botones / +- (Sub)'}

CM_ESTANDAR = "00000000"
CM_TWOTONE  = "C9000000"   # ilustracion two-tone (Zacian & Zamazenta)

prodinfo_file_path = None
original_colors = {}
original_colormodel = ""


def get_crc_16(data):
    crc = 0x55AA
    for byte in data:
        r = CRC_16_TABLE[crc & 0x0F]
        crc = ((crc >> 4) & 0x0FFF) ^ r ^ CRC_16_TABLE[byte & 0x0F]
        r = CRC_16_TABLE[crc & 0x0F]
        crc = ((crc >> 4) & 0x0FFF) ^ r ^ CRC_16_TABLE[(byte >> 4) & 0x0F]
    return crc


def parse_header(file_path):
    with open(file_path, "r+b") as file:
        header = file.read(0x40)
        try:
            magic, version, body_size, model, update_count, pad, crc, body_hash = struct.unpack("<IIIHH14sH32s", header)
            if magic != 0x304C4143:
                raise ValueError("Invalid CAL0 magic")
            return body_size, body_hash
        except (struct.error, ValueError):
            return 32704, None


def compute_sha256(file_path, offset=0x40):
    with open(file_path, "rb") as file:
        file_size = os.path.getsize(file_path)
        body_size, _ = parse_header(file_path)
        if body_size + offset > file_size:
            body_size = file_size - offset
        file.seek(offset)
        return hashlib.sha256(file.read(body_size)).digest()


def is_valid_prodinfo(file_path):
    if not os.path.exists(file_path):
        set_status("Error: archivo no encontrado.")
        return False
    with open(file_path, "rb") as file:
        if file.read(4) != b"CAL0":
            set_status("Error: PRODINFO invalido o cifrado (usa el .dec descifrado).")
            return False
    return True


def write_crc_block(file, offset, data14):
    crc = get_crc_16(data14)
    file.seek(offset)
    file.write(bytes(data14) + crc.to_bytes(2, byteorder="little"))
    file.flush()
    os.fsync(file.fileno())


def set_status(text):
    status_label.config(text=text)


# --------------------------- carga ---------------------------

def open_prodinfo():
    global prodinfo_file_path, original_colors, original_colormodel
    path = filedialog.askopenfilename(
        title="Abrir PRODINFO descifrado",
        filetypes=[("PRODINFO", "*.dec *.bin PRODINFO"), ("Todos", "*.*")]
    )
    if not path:
        return
    if not is_valid_prodinfo(path):
        return
    if not os.access(path, os.W_OK):
        set_status("Error: el archivo es de solo lectura.")
        return

    shutil.copy(path, path + ".bak")
    prodinfo_file_path = path
    original_colors = {}

    with open(path, "rb") as file:
        file.seek(0x250)
        serial = file.read(0xE).decode('ascii', errors='replace').strip()
        serial_value.config(text=serial)

        for key, offset in COLOR_OFFSETS.items():
            file.seek(offset)
            color_hex = file.read(3).hex().upper()
            color_vars[key].set(color_hex)
            color_cards[key].config(bg='#' + color_hex)
            original_colors[key] = color_hex

        file.seek(COLORMODEL_OFFSET)
        cm = file.read(4).hex().upper()
        colormodel_var.set(cm)
        original_colormodel = cm

    file_value.config(text=os.path.basename(path))
    draw_preview()
    set_status("PRODINFO cargado. Backup .bak creado.")


# --------------------------- modo / UI ---------------------------

def on_mode_change():
    lite = mode_var.get() == "lite"
    # mostrar/ocultar campos solo-Lite
    for key in LITE_ONLY_COLORS:
        if lite:
            color_rows[key]['label'].grid()
            color_rows[key]['entry'].grid()
            color_rows[key]['card'].grid()
        else:
            color_rows[key]['label'].grid_remove()
            color_rows[key]['entry'].grid_remove()
            color_rows[key]['card'].grid_remove()
    for w in colormodel_widgets:
        (w.grid() if lite else w.grid_remove())
    draw_preview()


def pick_color(key):
    code = colorchooser.askcolor(title=f"Elegir {key}")
    if code and code[0]:
        hex_color = ''.join(f'{int(c):02X}' for c in code[0])
        color_vars[key].set(hex_color)
        draw_preview()


def on_color_typed(key, *args):
    val = color_vars[key].get().lstrip('#').upper()
    if len(val) > 6:
        color_vars[key].set(val[:6])
        return
    if len(val) == 6 and all(c in "0123456789ABCDEF" for c in val):
        color_cards[key].config(bg='#' + val)
    draw_preview()


def set_model_preset(value):
    colormodel_var.set(value)
    set_status(f"Color Model = {value}  ({'Two-tone Zacian' if value == CM_TWOTONE else 'Estandar'})")
    draw_preview()


def hexval(key, fallback):
    v = color_vars[key].get().lstrip('#').upper()
    return ('#' + v) if (len(v) == 6 and all(c in "0123456789ABCDEF" for c in v)) else fallback


def draw_preview(*args):
    canvas.delete("all")
    main = hexval('Cuerpo (Main)', '#cccccc')
    bezel = hexval('Borde (Bezel)', '#333333')

    if mode_var.get() == "normal":
        # Switch con Joy-Cons: cuerpo (contorno grueso) + bezel pegado por dentro + pantalla
        canvas.create_rectangle(12, 30, 40, 94, fill="#e8e8e8", outline="#333", width=2)    # JC izq
        canvas.create_rectangle(200, 30, 228, 94, fill="#e8e8e8", outline="#333", width=2)  # JC der
        canvas.create_rectangle(52, 22, 188, 102, outline=main, width=9)                    # cuerpo (grueso)
        canvas.create_rectangle(60, 30, 180, 94, outline=bezel, width=6, fill="white")      # bezel pegado + pantalla
    else:
        # Switch Lite (unibody): cuerpo = Main, bezel bordea la pantalla, botones segun Sub/two-tone
        sub = hexval('Botones / +- (Sub)', '#888888')
        two = colormodel_var.get().strip().upper() == CM_TWOTONE
        left = "#00B7E0" if two else sub
        right = "#E01080" if two else sub
        canvas.create_rectangle(34, 22, 206, 102, fill=main, outline="#333", width=2)       # cuerpo
        canvas.create_rectangle(72, 32, 168, 92, fill=bezel, outline="")                    # marco bezel
        canvas.create_rectangle(79, 39, 161, 85, fill="white", outline="")                  # pantalla dentro del bezel
        # cluster botones izq
        for cx, cy in [(52, 46), (52, 78), (42, 62), (62, 62)]:
            canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill=left, outline="")
        # cluster botones der
        for cx, cy in [(188, 46), (188, 78), (178, 62), (198, 62)]:
            canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill=right, outline="")
        # simbolos +/- = Sub
        canvas.create_text(52, 30, text="−", fill=sub, font=("Arial", 13, "bold"))
        canvas.create_text(188, 30, text="+", fill=sub, font=("Arial", 13, "bold"))


# --------------------------- guardado ---------------------------

def update_prodinfo():
    if not prodinfo_file_path:
        set_status("Primero carga un PRODINFO.")
        return

    for key in COLOR_OFFSETS:
        val = color_vars[key].get().lstrip('#').upper()
        if len(val) != 6 or not all(c in "0123456789ABCDEF" for c in val):
            set_status(f"Color invalido en {key} (6 hex).")
            return
    cm_new = colormodel_var.get().strip().upper()
    if len(cm_new) != 8 or not all(c in "0123456789ABCDEF" for c in cm_new):
        set_status("Color Model debe ser 8 hex (ej. 00000000 o C9000000).")
        return

    changed = (
        any(color_vars[k].get().lstrip('#').upper() != original_colors[k] for k in COLOR_OFFSETS)
        or cm_new != original_colormodel
    )
    if not changed:
        set_status("No hay cambios.")
        return

    try:
        with open(prodinfo_file_path, 'r+b') as file:
            file.seek(0x10)
            count = int.from_bytes(file.read(2), byteorder="little") + 1
            file.seek(0x10)
            file.write(count.to_bytes(2, byteorder="little"))
            file.flush(); os.fsync(file.fileno())
            file.seek(0)
            header = bytearray(file.read(0x1E))
            file.seek(0x1E)
            file.write(get_crc_16(header).to_bytes(2, byteorder="little"))
            file.flush(); os.fsync(file.fileno())

            for key, offset in COLOR_OFFSETS.items():
                val = color_vars[key].get().lstrip('#').upper()
                if val != original_colors[key]:
                    data14 = list(bytes.fromhex(val)) + [0xFF] + [0x00] * 10
                    write_crc_block(file, offset, data14)

            if cm_new != original_colormodel:
                file.seek(COLORMODEL_OFFSET)
                blk = bytearray(file.read(14))
                blk[0:4] = bytes.fromhex(cm_new)
                write_crc_block(file, COLORMODEL_OFFSET, blk)

            new_sha = compute_sha256(prodinfo_file_path, offset=0x40)
            file.seek(0x20)
            file.write(new_sha)
            file.flush(); os.fsync(file.fileno())

            file.seek(0x0)
            big = file.read(0x8000)
            file.seek(0x8000)
            file.write(get_crc_16(big).to_bytes(2, byteorder="little") + b'\x00\x00')
            file.flush(); os.fsync(file.fileno())

        for k in COLOR_OFFSETS:
            original_colors[k] = color_vars[k].get().lstrip('#').upper()
        globals()['original_colormodel'] = cm_new
        set_status("PRODINFO actualizado. Restauralo a la consola.")
    except Exception as e:
        set_status(f"Error al guardar: {e}")


# =========================== UI ===========================

root = tk.Tk()
root.title(f"Prodify Dual — Switch / Switch Lite ({SCRIPT_VERSION})")
root.geometry("460x500")
root.resizable(False, False)
# icono de la ventana (tolerante: .ico en Windows, .png como fallback)
try:
    root.iconbitmap(resource_path("icon.ico"))
except Exception:
    try:
        root.iconphoto(True, tk.PhotoImage(file=resource_path("icon.png")))
    except Exception:
        pass

color_vars = {}
color_cards = {}
color_rows = {}
colormodel_var = tk.StringVar(value=CM_ESTANDAR)
mode_var = tk.StringVar(value="lite")

frame = tk.Frame(root)
frame.pack(padx=16, pady=10, fill="x")

# toggle de modo
mode_frame = tk.Frame(frame)
mode_frame.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
tk.Label(mode_frame, text="Modo:").pack(side="left", padx=(0, 8))
tk.Radiobutton(mode_frame, text="Switch Normal", variable=mode_var, value="normal",
               command=on_mode_change).pack(side="left")
tk.Radiobutton(mode_frame, text="Switch Lite", variable=mode_var, value="lite",
               command=on_mode_change).pack(side="left")

# serial (solo lectura)
tk.Label(frame, text="Serial (solo lectura)").grid(row=1, column=0, sticky="w", pady=4)
serial_value = tk.Label(frame, text="—", anchor="w")
serial_value.grid(row=1, column=1, columnspan=2, sticky="w", pady=4)

# filas de color
r = 2
for key in COLOR_OFFSETS:
    lbl = tk.Label(frame, text=key)
    lbl.grid(row=r, column=0, sticky="w", pady=4)
    var = tk.StringVar()
    color_vars[key] = var
    entry = tk.Entry(frame, textvariable=var, width=12)
    entry.grid(row=r, column=1, sticky="w", pady=4)
    var.trace("w", lambda *a, k=key: on_color_typed(k))
    card = tk.Label(frame, width=4, height=1, bg="white", relief="solid")
    card.grid(row=r, column=2, sticky="w", padx=6)
    card.bind("<Button-1>", lambda e, k=key: pick_color(k))
    color_cards[key] = card
    color_rows[key] = {'label': lbl, 'entry': entry, 'card': card}
    r += 1

# color model + presets (solo Lite)
cm_label = tk.Label(frame, text="Color Model (hex)")
cm_label.grid(row=r, column=0, sticky="w", pady=4)
cm_entry = tk.Entry(frame, textvariable=colormodel_var, width=12)
cm_entry.grid(row=r, column=1, sticky="w", pady=4)
r += 1
preset_frame = tk.Frame(frame)
preset_frame.grid(row=r, column=0, columnspan=3, sticky="w", pady=(0, 4))
tk.Label(preset_frame, text="Preset:").pack(side="left", padx=(0, 6))
tk.Button(preset_frame, text="Estandar", width=10,
          command=lambda: set_model_preset(CM_ESTANDAR)).pack(side="left", padx=3)
tk.Button(preset_frame, text="Two-tone (Zacian)", width=16,
          command=lambda: set_model_preset(CM_TWOTONE)).pack(side="left", padx=3)
colormodel_widgets = [cm_label, cm_entry, preset_frame]
r += 1

# archivo
tk.Label(frame, text="Archivo:").grid(row=r, column=0, sticky="w", pady=4)
file_value = tk.Label(frame, text="—", anchor="w")
file_value.grid(row=r, column=1, columnspan=2, sticky="w", pady=4)

# preview
canvas = tk.Canvas(root, width=240, height=124, bg="#f3f3f3", highlightthickness=0)
canvas.pack(pady=(4, 8))

# botones de accion
btns = tk.Frame(root)
btns.pack(pady=(0, 8))
tk.Button(btns, text="Cargar PRODINFO", command=open_prodinfo).pack(side="left", padx=8)
tk.Button(btns, text="Guardar cambios", command=update_prodinfo).pack(side="left", padx=8)

status_label = tk.Label(root, text="Carga un PRODINFO descifrado para empezar.", fg="#444")
status_label.pack(pady=(0, 8))

on_mode_change()  # aplica visibilidad inicial + preview
root.mainloop()
