# Switch Lite Color Editor (Prodify Dual)

A focused PRODINFO color editor for the **Nintendo Switch** and **Nintendo Switch Lite**.

Edit the console body/bezel/button colors that show in the system **Controllers** screen — and, on the **Switch Lite**, unlock the **two‑tone special‑edition look** (e.g. Zacian & Zamazenta: cyan left buttons / magenta right buttons) on any standard unit.

> Based on [**PRODIFY** by sthetix](https://github.com/sthetix/PRODIFY). All credit for the original tool, decrypted‑PRODINFO handling and CRC‑16 logic goes to sthetix. This is a community modification that adds the extra CAL0 colour fields, the `ColorModel` field, a Normal/Lite mode toggle and a live preview.

---

## ✨ What's new vs the original PRODIFY

- **Normal / Lite mode toggle** — one app for both console types.
- **Extra CAL0 fields exposed**: `HousingSubColor` (buttons) and **`ColorModel`** (`0x4330`), which the original never edited.
- **One‑click `ColorModel` presets** — *Standard* and *Two‑tone (Zacian)*.
- **Live preview** of body / bezel / buttons.
- Recalculates **CRC‑16 per block + body SHA‑256** automatically (same proven logic as PRODIFY).
- Serial number is **read‑only** (never touched) — this tool is purely cosmetic.

---

## 🔑 The Switch Lite two‑tone discovery

The genuinely new finding documented here (not published anywhere else):

The Switch Lite **two‑tone** controller illustration (different left/right button colours, like the Zacian & Zamazenta edition) **cannot** be reproduced with colour fields alone — the home‑menu colour scheme only carries a single button colour. It is a **separate firmware illustration**, selected by the **`ColorModel`** field at CAL0 offset **`0x4330`** (read by `GetHomeMenuSchemeModel`, set:sys cmd 185).

Confirmed by dumping a real special‑edition unit and replicating it on a standard one:

| Field | Offset | Controls |
|-------|--------|----------|
| **Color Model** | `0x4330` | **Illustration.** `00000000` = standard · `C9000000` = two‑tone (Zacian/Zamazenta) |
| Main Color | `0x4240` | Console body |
| Bezel Color | `0x4230` | Outer bezel / border |
| Sub Color | `0x4220` | Buttons (single tone) / the `+` and `−` symbols in two‑tone mode |

Notes confirmed on hardware:
- `ColorModel = C9000000` works on **any** Lite — the firmware does **not** cross‑check it against the serial/model.
- In two‑tone mode the cyan(left)/magenta(right) button clusters are **baked into the illustration**; you can still recolour the **body** (Main) and the **+/−** symbols (Sub).
- `ColorVariation` (`0x3750`) does **not** affect the two‑tone — only `ColorModel` does.
- The darker/lighter **outer border** in the menu is the **system theme** (light/dark), not a CAL0 field.

---

## 🚀 Usage

1. **Dump** your console's **decrypted** PRODINFO (e.g. with Hekate + NxNandManager → *Dump (decrypted)*).
2. Open the app, **Load PRODINFO** (`.dec`). A `.bak` backup is created automatically.
3. Pick **Normal** or **Lite** mode.
4. Adjust colours / choose a **Color Model** preset.
5. **Save changes**.
6. **Restore** the file to the console (NxNandManager → *Restore (decrypted)*).

> Windows users: grab the prebuilt **`Prodify_Dual.exe`** from [Releases](../../releases) — no Python needed.
> From source: `python Prodify_Dual.py` (Python 3, tkinter included on Windows).

---

## ⚠️ Safety

- **PRODINFO is unique and unrecoverable.** Always keep a full backup (Hekate eMMC backup) **and** the original `.dec` before writing anything.
- This tool edits a **decrypted** PRODINFO file on your PC — it never writes to the console directly. You restore it yourself.
- Colour edits are cosmetic and do **not** touch the device certificate, so they carry **low ban risk** — but "zero risk" does not exist with CFW. Use your own judgement.
- Writing a bad PRODINFO can break console functions. One change at a time, verify, keep backups.

---

## 🙏 Credits

- **[sthetix](https://github.com/sthetix/PRODIFY)** — original PRODIFY tool and PRODINFO/CRC logic.
- CAL0 field offsets documented on [Switchbrew](https://switchbrew.org/wiki/Calibration).
- Switch Lite `ColorModel` two‑tone value reverse‑engineered by dumping a real special‑edition unit.

## 📄 Disclaimer

For educational and personal‑customisation use. You are responsible for your own console. No warranty.
