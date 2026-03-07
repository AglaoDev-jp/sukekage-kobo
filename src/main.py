"""
Copyright © 2026 AglaoDev-jp
Licensed under the MIT License.
See LICENSE for details.

External Libraries:

- Tkinter:  
  Copyright © Regents of the University of California, Sun Microsystems, Inc., Scriptics Corporation, and other parties  
  Licensed under the Tcl/Tk License. For full details, see:  
  [Tcl/Tk License](https://www.tcl.tk/software/tcltk/license.html)

- Pillow (a friendly fork of the Python Imaging Library, PIL):  
  The Python Imaging Library (PIL) is  
  Copyright © 1997-2011 by Secret Labs AB  
  Copyright © 1995-2011 Fredrik Lundh and Contributors.  
  Pillow is the friendly PIL fork. It is  
  Copyright © 2010-2024 by Jeffrey A. Clark and contributors  
  Licensed under the PIL Software License (MIT-CMU style). See LICENSE-Pillow.txt or visit:  
  [Pillow License](https://pillow.readthedocs.io/en/stable/about.html#license)

*This file was created and refined with support from OpenAI’s conversational AI, ChatGPT.*

Special thanks to all developers and contributors who made these libraries possible.

---

透け影工房（Tkinter + Pillow）
- 単発（1枚）と一括（フォルダ）の影絵生成
- プレビュー（入力/出力）と、パラメータ調整
- 進捗表示、キャンセル、ログ、例外通知
- 処理中に固まらない（thread + after でUI更新）

"""

from __future__ import annotations

import threading
import queue
import time
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Dict, List

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageFilter, ImageChops, ImageTk

# ============================================================
# 影絵生成ロジック
# ============================================================

@dataclass
class SilhouetteParams:
    # 透け感（最終アルファ）
    target_alpha: int = 200  # 0-255

    # 輪郭フェザー（アルファをぼかす）
    feather_radius_outline: float = 1.5  # 0-10

    # 影の基本の暗さ（0=真っ黒, 24くらい=少しだけ明るい黒）
    inner_shade: int = 24

    # 影色（プリセット）と強さ
    color_preset: str = "灰"   # "灰","赤","青","緑","紫"...
    color_strength: int = 0    # 0-255（0なら無彩色寄り）

    # グレイン　粒状ノイズ（紙・質感）
    add_grain: bool = True
    grain_strength: int = 18   # 0-64程度

    # 質感テクスチャ（任意画像）
    add_texture: bool = False
    texture_path: Optional[Path] = None  # Noneなら使わない

    # アウトライン（輪郭の濃い縁）
    add_outline: bool = True
    outline_thickness: int = 2  # 1-4程度

# ざっくりプリセットカラー（影色の“色味”）
# ※ ここは「色味」の方向だけを示し、最終的な暗さは inner_shade と合成します。
# 欲しい色があったらここに追加すると👍。
# ドロップダウンリストの表示順は dict の順序になるので、使用目的や使う人目線で並べるとより気持ちいいのです。
# Tkではttk.Combobox(state="readonly")で"読むだけのコンボボックスを作る"みたいな記述。
COLOR_PRESETS: Dict[str, Tuple[int, int, int]] = {
    "灰": (128, 128, 128),
    "赤": (170, 70, 70),
    "青": (70, 90, 170),
    "緑": (70, 160, 90),
    "紫": (150, 90, 170),
    "茶": (150, 110, 80),
    "ピンク": (200, 110, 150),
    "オレンジ": (200, 130, 80),
}

def clamp_int(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(v)))


def clamp_float(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def make_grain_l(size: Tuple[int, int], strength: int = 16) -> Image.Image:
    """
    指定サイズのグレイン（L画像）を生成し、乗算で重ねる用の素材を返します。

    速度と見た目のバランスのため、
    - ランダム点のムラ
    - 軽いぼかし
    を行っています。
    """
    w, h = size
    strength = clamp_int(strength, 0, 64)

    # ほぼ白のベース（strengthが大きいほど暗め寄り）
    base = Image.new("L", (w, h), 255 - strength)

    # ランダム点でムラを作る
    px = base.load()
    # 2%程度をムラ点として打つ（大きい画像だと時間がかかるので控えめ）
    dot_count = int(w * h * 0.02)
    for _ in range(dot_count):
        x = random.randrange(w)
        y = random.randrange(h)
        delta = random.randrange(-strength, strength + 1)
        val = clamp_int(px[x, y] + delta, 0, 255)
        px[x, y] = val

    # 少しぼかして馴染ませる
    return base.filter(ImageFilter.GaussianBlur(0.6))

def _mix_shadow_color(inner_shade: int, preset_rgb: Tuple[int, int, int], strength: int) -> Tuple[int, int, int]:
    """
    「影の基本色（inner_shadeのグレー）」と「プリセット色」を strength でブレンドして返します。
    strength=0   -> ほぼグレー
    strength=255 -> かなり色味が乗る（ただし影なので全体は暗めに留まる）
    """
    inner_shade = clamp_int(inner_shade, 0, 255)
    strength = clamp_int(strength, 0, 255)
    t = strength / 255.0

    base = (inner_shade, inner_shade, inner_shade)
    pr, pg, pb = preset_rgb

    # 線形補間（Lerp）
    r = int(base[0] * (1 - t) + pr * t)
    g = int(base[1] * (1 - t) + pg * t)
    b = int(base[2] * (1 - t) + pb * t)

    # 影として暗さを維持するため、上限を少し抑える（明るくなりすぎ防止）
    r = min(r, 200)
    g = min(g, 200)
    b = min(b, 200)
    return (r, g, b)


def _apply_alpha_scale(alpha: Image.Image, target_alpha: int) -> Image.Image:
    """
    アルファ画像（L）に対して、最終不透明度（target_alpha）を掛け算する。
    """
    target_alpha = clamp_int(target_alpha, 0, 255)
    if target_alpha >= 255:
        return alpha
    factor = target_alpha / 255.0
    # point で1ピクセルずつ係数をかける
    return alpha.point(lambda v: int(v * factor))


def generate_silhouette_rgba(img_rgba: Image.Image, params: SilhouetteParams) -> Image.Image:
    """
    入力 RGBA 画像（透過PNG想定）から、影絵（透け感 + 質感 + グレイン + アウトライン）を生成して返す。
    """
    # --- 安全のためRGBA化 ---
    img = img_rgba.convert("RGBA")
    w, h = img.size

    # --- αチャンネル抽出 ---
    a0 = img.getchannel("A")

    # --- 影の色（inner_shade + color preset） ---
    preset_rgb = COLOR_PRESETS.get(params.color_preset, COLOR_PRESETS["灰"])
    shadow_rgb = _mix_shadow_color(params.inner_shade, preset_rgb, params.color_strength)
    base_rgb_img = Image.new("RGB", (w, h), shadow_rgb)

    # --- フェザー（輪郭を柔らかくする） ---
    feather = clamp_float(params.feather_radius_outline, 0.0, 10.0)
    if feather > 0:
        a_soft = a0.filter(ImageFilter.GaussianBlur(feather))
    else:
        a_soft = a0

    # --- 最終透け感（TARGET_ALPHA）を反映したメインアルファ ---
    a_main = _apply_alpha_scale(a_soft, params.target_alpha)

    # --- メイン影絵（RGBA） ---
    silhouette_main = Image.merge("RGBA", (*base_rgb_img.split(), a_main))

    # --- アウトライン（輪郭に濃い縁を残す） ---
    # 方針：
    # 1) 元アルファを膨張（dilation） -> dilated
    # 2) outline = dilated - original（輪郭の外側だけ残す）
    # 3) 輪郭を濃い色で合成
    result = silhouette_main

    if params.add_outline and params.outline_thickness > 0:
        thickness = clamp_int(params.outline_thickness, 1, 8)  # 安全側に少し広げてもOKに
        # PILのMaxFilterはサイズが奇数指定（3,5,7...）なので thickness から変換
        # thickness=1 -> size=3, thickness=2 -> size=5, ...
        size = thickness * 2 + 1

        # 膨張アルファ
        dilated = a0.filter(ImageFilter.MaxFilter(size=size))

        # 輪郭だけ抜き出し（外側リング）
        outline_alpha_raw = ImageChops.subtract(dilated, a0)

        # 輪郭の“濃さ”は、ターゲットアルファより少し強めにして目立たせる
        outline_alpha = _apply_alpha_scale(outline_alpha_raw, min(255, params.target_alpha + 60))

        # アウトライン色は「より濃い影」（ほぼ黒寄り）
        outline_color = (0, 0, 0)
        outline_rgb = Image.new("RGB", (w, h), outline_color)
        outline_rgba = Image.merge("RGBA", (*outline_rgb.split(), outline_alpha))

        # 合成：アウトライン → メイン影絵の順
        # ※ alpha_composite は透明を考慮して合成できる
        tmp = Image.alpha_composite(outline_rgba, result)
        result = tmp

    # --- 質感テクスチャ（任意画像の乗算） ---
    if params.add_texture and params.texture_path and params.texture_path.exists():
        try:
            tex = Image.open(params.texture_path).convert("L").resize((w, h), Image.LANCZOS)
            rgb = Image.merge("RGB", result.split()[:3])
            rgb = ImageChops.multiply(rgb, Image.merge("RGB", (tex, tex, tex)))
            result = Image.merge("RGBA", (*rgb.split(), result.split()[3]))
        except Exception:
            # 質感は“任意”なので、失敗しても影絵自体は作れるようにスキップする
            pass

    # --- グレイン（乗算） ---
    if params.add_grain:
        grain_strength = clamp_int(params.grain_strength, 0, 64)
        if grain_strength > 0:
            grain = make_grain_l((w, h), strength=grain_strength)
            rgb = Image.merge("RGB", result.split()[:3])
            rgb = ImageChops.multiply(rgb, Image.merge("RGB", (grain, grain, grain)))
            result = Image.merge("RGBA", (*rgb.split(), result.split()[3]))

    return result


def process_file_to_file(input_path: Path, output_path: Path, params: SilhouetteParams) -> None:
    """
    入力ファイル -> 影絵生成 -> 出力ファイル 保存（例外は呼び出し側で扱う想定）
    """
    img = Image.open(input_path).convert("RGBA")
    out = generate_silhouette_rgba(img, params)
    # optimize は PNG のサイズ削減に効く場合が多い
    out.save(output_path, optimize=True)


def make_unique_output_path(out_dir: Path, base_stem: str) -> Path:
    """
    出力名：{元名}_silhouette.png
    重複時は {元名}_silhouette_001.png, _002... のように連番を付ける
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    candidate = out_dir / f"{base_stem}_silhouette.png"
    if not candidate.exists():
        return candidate

    # 連番
    for i in range(1, 10000):
        candidate = out_dir / f"{base_stem}_silhouette_{i:03d}.png"
        if not candidate.exists():
            return candidate

    # ここまで来ることは通常ほぼない
    raise RuntimeError("出力ファイルの連番が上限に達しました。フォルダ内のファイル数をご確認ください。")


def shorten_path(path: str, max_len: int = 30) -> str:
    """
    長いパスを末尾優先で短縮表示する（UI表示専用）。
    例: \\input\\kagee.png
    Tkって、パスで画面が大きくなったりするんですよね。
    """
    if not path:
        return "未選択"
    if len(path) <= max_len:
        return path
    return "…" + path[-(max_len - 1):]

# ============================================================
# GUI（Tkinter）
# ============================================================

class SukekageApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("透け影工房")
        self.geometry("1100x720")
        self.minsize(980, 650)

        # --- 画像パス（単発用） ---
        self.input_file: Optional[Path] = None
        self.output_file: Optional[Path] = None

        # --- 一括用 ---
        self.input_dir: Optional[Path] = None
        self.output_dir: Optional[Path] = None

        # --- プレビュー用のPIL画像キャッシュ ---
        self._preview_in_pil: Optional[Image.Image] = None
        self._preview_out_pil: Optional[Image.Image] = None

        # TkinterのPhotoImageは参照を保持しないと消えるので、インスタンス変数で保持
        self._preview_in_tk: Optional[ImageTk.PhotoImage] = None
        self._preview_out_tk: Optional[ImageTk.PhotoImage] = None

        # --- バッチ処理スレッド用 ---
        self._worker_thread: Optional[threading.Thread] = None
        self._cancel_event = threading.Event()

        # スレッド -> UI への通知は queue で安全に行う
        self._queue: "queue.Queue[tuple]" = queue.Queue()

        # --- GUI変数（パラメータ） ---
        self.var_target_alpha = tk.IntVar(value=200)
        self.var_feather = tk.DoubleVar(value=1.5)

        self.var_color_preset = tk.StringVar(value="灰")
        self.var_color_strength = tk.IntVar(value=0)

        # 「色味を付ける」ON/OFF（OFFなら黒影）
        self.var_use_tint = tk.BooleanVar(value=False)

        self.var_add_grain = tk.BooleanVar(value=True)
        self.var_grain_strength = tk.IntVar(value=18)

        self.var_add_texture = tk.BooleanVar(value=False)
        self.var_texture_path = tk.StringVar(value="")

        self.var_add_outline = tk.BooleanVar(value=True)
        self.var_outline_thickness = tk.IntVar(value=2)

        # inner_shade は元スクリプトにありましたが、要件に明示がないので「固定」にしています。
        # ここをGUI化したい場合は改良案で提案します。
        self._inner_shade_fixed = 24

        # --- 画面構築 ---
        self._build_ui()

        # --- queue を定期ポーリングしてUI反映 ---
        self.after(100, self._poll_queue)

    # ----------------------------
    # UI 構築
    # ----------------------------

    def _build_ui(self) -> None:
        # 全体を左右に分ける（左：操作、右：プレビュー）
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)

        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        left = ttk.Frame(root)
        right = ttk.Frame(root)

        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right.grid(row=0, column=1, sticky="nsew")

        left.rowconfigure(4, weight=1)   # ログ領域を伸ばす
        right.rowconfigure(1, weight=1)  # プレビュー領域を伸ばす

        # --- 単発 ---
        self._build_single_panel(left)

        # --- 一括 ---
        self._build_batch_panel(left)

        # --- パラメータ ---
        self._build_params_panel(left)

        # --- 実行/プレビュー/キャンセル ---
        self._build_action_panel(left)

        # --- ログ ---
        self._build_log_panel(left)

        # --- プレビュー ---
        self._build_preview_panel(right)

    def _build_single_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="単発（1枚）", padding=10)
        frame.grid(row=0, column=0, sticky="ew")
        frame.columnconfigure(1, weight=1)

        ttk.Button(frame, text="入力画像を選択", command=self.on_pick_input_file).grid(row=0, column=0, sticky="w")
        self.lbl_in_file = ttk.Label(frame, text="未選択")
        self.lbl_in_file.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        ttk.Button(frame, text="出力ファイルを選択", command=self.on_pick_output_file).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.lbl_out_file = ttk.Label(frame, text="未選択")
        self.lbl_out_file.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(8, 0))

    def _build_batch_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="一括（フォルダ）", padding=10)
        frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        frame.columnconfigure(1, weight=1)

        ttk.Button(frame, text="入力フォルダを選択", command=self.on_pick_input_dir).grid(row=0, column=0, sticky="w")
        self.lbl_in_dir = ttk.Label(frame, text="未選択")
        self.lbl_in_dir.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        ttk.Button(frame, text="出力フォルダを選択", command=self.on_pick_output_dir).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.lbl_out_dir = ttk.Label(frame, text="未選択")
        self.lbl_out_dir.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(8, 0))

        # 進捗
        prog = ttk.Frame(frame)
        prog.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        prog.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(prog, mode="determinate")
        self.progress.grid(row=0, column=0, sticky="ew")
        self.lbl_progress = ttk.Label(prog, text="0 / 0")
        self.lbl_progress.grid(row=0, column=1, padx=(10, 0))

    def _update_tint_ui_state(self) -> None:
        """
        「色味を付ける」ON/OFF に応じて、
        - 色味プリセット
        - 色味の強さ
        のUIを有効/無効化する。

        ※ レイアウトは変えず、状態だけ切り替えるので隙間問題が起きにくい。
        """
        use_tint = bool(self.var_use_tint.get())

        # Combobox は state を切り替え
        self.cmb_color.configure(state="readonly" if use_tint else "disabled")

        # Scale/Entry は state で切り替え（ttk.Scale は state 対応）
        self.scale_color_strength.configure(state="normal" if use_tint else "disabled")
        self.ent_color_strength.configure(state="normal" if use_tint else "disabled")

        if not use_tint:
            # --- OFFなら黒影（強さ0）へ寄せる ---
            self.var_color_strength.set(0)

            # entry表示も合わせる（disabledだと書き換えできないので一時的にnormal）
            self.ent_color_strength.configure(state="normal")
            self.ent_color_strength.delete(0, tk.END)
            self.ent_color_strength.insert(0, "0")
            self.ent_color_strength.configure(state="disabled")

        else:
            # --- ONにした瞬間、強さが0なら「見える既定値」へ引き上げる ---
            # なんか0のままだと効いてない？ように見えるためのデフォルト設定
            if self.var_color_strength.get() == 0:
                default_strength = 120  # 好みで 80～140 
                self.var_color_strength.set(default_strength)

                self.ent_color_strength.configure(state="normal")
                self.ent_color_strength.delete(0, tk.END)
                self.ent_color_strength.insert(0, str(default_strength))
                # ON中なのでこのまま normal のままでOK

    def _build_params_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="パラメータ", padding=10)
        frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        frame.columnconfigure(1, weight=1)

        # 透け感（TARGET_ALPHA）
        ttk.Label(frame, text="透け感（TARGET_ALPHA）").grid(row=0, column=0, sticky="w")
        s1 = ttk.Scale(
            frame, from_=0, to=255, orient=tk.HORIZONTAL,
            command=lambda _v: self._sync_int_scale(self.var_target_alpha, self.ent_target_alpha),
            variable=self.var_target_alpha
        )
        s1.grid(row=0, column=1, sticky="ew", padx=(10, 10))
        self.ent_target_alpha = ttk.Entry(frame, width=6)
        self.ent_target_alpha.grid(row=0, column=2, sticky="e")
        self._bind_entry_int(self.ent_target_alpha, self.var_target_alpha, 0, 255)
        self.ent_target_alpha.insert(0, str(self.var_target_alpha.get()))

        # フェザー
        ttk.Label(frame, text="輪郭フェザー（0-10）").grid(row=1, column=0, sticky="w", pady=(8, 0))
        s2 = ttk.Scale(
            frame, from_=0, to=10, orient=tk.HORIZONTAL,
            command=lambda _v: self._sync_float_scale(self.var_feather, self.ent_feather),
            variable=self.var_feather
        )
        s2.grid(row=1, column=1, sticky="ew", padx=(10, 10), pady=(8, 0))
        self.ent_feather = ttk.Entry(frame, width=6)
        self.ent_feather.grid(row=1, column=2, sticky="e", pady=(8, 0))
        self._bind_entry_float(self.ent_feather, self.var_feather, 0.0, 10.0)
        self.ent_feather.insert(0, f"{self.var_feather.get():.2f}")

        # ----------------------------------------
        # 色味（モノクロ/色味付き 切り替え）
        #  - チェックの右にプリセットComboboxを配置
        #  - 強さは次の行に置いて、被りにくくする
        # ----------------------------------------

        # 1行目： [✓ 色味を付ける]  [プリセット▼]
        row_tint = ttk.Frame(frame)
        row_tint.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        row_tint.columnconfigure(1, weight=1)  # Combobox側を伸ばせるように

        self.chk_use_tint = ttk.Checkbutton(
            row_tint,
            text="色味を付ける",
            variable=self.var_use_tint,
            command=self._update_tint_ui_state
        )
        self.chk_use_tint.grid(row=0, column=0, sticky="w")

        # チェックの右にドロップダウン
        self.cmb_color = ttk.Combobox(
            row_tint,
            values=list(COLOR_PRESETS.keys()),
            textvariable=self.var_color_preset,
            state="readonly",
            width=8
        )
        self.cmb_color.grid(row=0, column=1, sticky="w", padx=(12, 0))

        # 2行目：色味強さ（スライダー＋数値）
        ttk.Label(frame, text="色味の強さ（0-255）").grid(row=3, column=0, sticky="w", pady=(8, 0))

        s3 = ttk.Scale(
            frame,
            from_=0, to=255,
            orient=tk.HORIZONTAL,
            command=lambda _v: self._sync_int_scale(self.var_color_strength, self.ent_color_strength),
            variable=self.var_color_strength
        )
        s3.grid(row=3, column=1, sticky="ew", padx=(10, 10), pady=(8, 0))

        self.ent_color_strength = ttk.Entry(frame, width=6)
        self.ent_color_strength.grid(row=3, column=2, sticky="e", pady=(8, 0))

        self._bind_entry_int(self.ent_color_strength, self.var_color_strength, 0, 255)
        self.ent_color_strength.delete(0, tk.END)
        self.ent_color_strength.insert(0, str(self.var_color_strength.get()))

        # 参照保持（有効/無効切替に使う）
        self.scale_color_strength = s3

        # 起動直後の状態反映（チェックOFFならグレーアウト）
        self._update_tint_ui_state()

        # グレイン ON/OFF + 強さ
        self.chk_grain = ttk.Checkbutton(frame, text="粒状ノイズ（紙・質感）ON", variable=self.var_add_grain)
        self.chk_grain.grid(row=4, column=0, sticky="w", pady=(10, 0))

        ttk.Label(frame, text="強さ（0-64）").grid(row=4, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        s4 = ttk.Scale(
            frame, from_=0, to=64, orient=tk.HORIZONTAL,
            command=lambda _v: self._sync_int_scale(self.var_grain_strength, self.ent_grain_strength),
            variable=self.var_grain_strength
        )
        s4.grid(row=5, column=1, sticky="ew", padx=(10, 10))
        self.ent_grain_strength = ttk.Entry(frame, width=6)
        self.ent_grain_strength.grid(row=5, column=2, sticky="e")
        self._bind_entry_int(self.ent_grain_strength, self.var_grain_strength, 0, 64)
        self.ent_grain_strength.insert(0, str(self.var_grain_strength.get()))

        # 質感テクスチャ ON/OFF + ファイル
        self.chk_texture = ttk.Checkbutton(frame, text="質感テクスチャON", variable=self.var_add_texture)
        self.chk_texture.grid(row=6, column=0, sticky="w", pady=(10, 0))

        ttk.Button(frame, text="テクスチャ画像を選択", command=self.on_pick_texture).grid(row=6, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        self.lbl_texture = ttk.Label(frame, text="未選択")
        self.lbl_texture.grid(row=7, column=1, sticky="ew", padx=(10, 0))

        # アウトライン ON/OFF + 太さ
        self.chk_outline = ttk.Checkbutton(frame, text="アウトラインON（輪郭を濃く）", variable=self.var_add_outline)
        self.chk_outline.grid(row=8, column=0, sticky="w", pady=(10, 0))

        ttk.Label(frame, text="太さ（1-4）").grid(row=8, column=1, sticky="w", padx=(10, 0), pady=(10, 0))
        s5 = ttk.Scale(
            frame, from_=1, to=4, orient=tk.HORIZONTAL,
            command=lambda _v: self._sync_int_scale(self.var_outline_thickness, self.ent_outline_thick),
            variable=self.var_outline_thickness
        )
        s5.grid(row=9, column=1, sticky="ew", padx=(10, 10))
        self.ent_outline_thick = ttk.Entry(frame, width=6)
        self.ent_outline_thick.grid(row=9, column=2, sticky="e")
        self._bind_entry_int(self.ent_outline_thick, self.var_outline_thickness, 1, 4)
        self.ent_outline_thick.insert(0, str(self.var_outline_thickness.get()))

    def _build_action_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="操作", padding=10)
        frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)

        ttk.Button(frame, text="プレビュー更新", command=self.on_update_preview).grid(row=0, column=0, sticky="ew")
        ttk.Button(frame, text="単発 実行", command=self.on_run_single).grid(row=0, column=1, sticky="ew", padx=(10, 10))
        ttk.Button(frame, text="一括 実行", command=self.on_run_batch).grid(row=0, column=2, sticky="ew")

        self.btn_cancel = ttk.Button(frame, text="キャンセル", command=self.on_cancel, state=tk.DISABLED)
        self.btn_cancel.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0))

    def _build_log_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="ログ", padding=10)
        frame.grid(row=4, column=0, sticky="nsew", pady=(10, 0))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.txt_log = tk.Text(frame, height=10, wrap="word")
        self.txt_log.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.txt_log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.txt_log.configure(yscrollcommand=sb.set)


    def _build_preview_panel(self, parent: ttk.Frame) -> None:
        """
        上：入力、下：出力
        """
        frame = ttk.LabelFrame(parent, text="プレビュー（入力 / 出力）", padding=10)
        frame.grid(row=0, column=0, sticky="nsew")

        # 縦に 4段：入力ラベル、入力キャンバス、出力ラベル、出力キャンバス
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)  # 入力キャンバスを伸ばす
        frame.rowconfigure(3, weight=1)  # 出力キャンバスを伸ばす

        ttk.Label(frame, text="入力").grid(row=0, column=0, sticky="w")

        self.canvas_in = tk.Canvas(frame, bg="#222222", highlightthickness=0)
        self.canvas_in.grid(row=1, column=0, sticky="nsew", pady=(5, 12))

        ttk.Label(frame, text="出力").grid(row=2, column=0, sticky="w")

        self.canvas_out = tk.Canvas(frame, bg="#222222", highlightthickness=0)
        self.canvas_out.grid(row=3, column=0, sticky="nsew", pady=(5, 0))

        # リサイズ時に再描画
        self.canvas_in.bind("<Configure>", lambda _e: self._render_previews())
        self.canvas_out.bind("<Configure>", lambda _e: self._render_previews())

    # ----------------------------
    # 共通：ログ
    # ----------------------------

    def log(self, msg: str) -> None:
        """ログ欄に追記（UIスレッドから呼ぶ想定）"""
        ts = time.strftime("%H:%M:%S")
        self.txt_log.insert(tk.END, f"[{ts}] {msg}\n")
        self.txt_log.see(tk.END)

    # ----------------------------
    # パラメータ取得
    # ----------------------------

    def get_params(self) -> SilhouetteParams:
        """
        GUIの値を SilhouetteParams に集約する。
        ここで範囲補正も行うので、処理側は安全になります。
        """
        tex_path = self.var_texture_path.get().strip()
        tex = Path(tex_path) if tex_path else None

        use_tint = bool(self.var_use_tint.get())
        
        return SilhouetteParams(
            target_alpha=clamp_int(self.var_target_alpha.get(), 0, 255),
            feather_radius_outline=clamp_float(self.var_feather.get(), 0.0, 10.0),
            inner_shade=self._inner_shade_fixed,

            color_preset=self.var_color_preset.get(),
            # ★重要：チェックOFFなら強制0（=黒影）
            color_strength=clamp_int(self.var_color_strength.get(), 0, 255) if use_tint else 0,

            add_grain=bool(self.var_add_grain.get()),
            grain_strength=clamp_int(self.var_grain_strength.get(), 0, 64),

            add_texture=bool(self.var_add_texture.get()),
            texture_path=tex,

            add_outline=bool(self.var_add_outline.get()),
            outline_thickness=clamp_int(self.var_outline_thickness.get(), 1, 4),
        )

    # ----------------------------
    # ファイル/フォルダ選択
    # ----------------------------

    def on_pick_input_file(self) -> None:
        path = filedialog.askopenfilename(
            title="入力PNGを選択",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")]
        )
        if not path:
            return

        self.input_file = Path(path)

        # ★UI表示だけ短縮
        self.lbl_in_file.configure(text=shorten_path(path))

        # （ログはフルパスでOK）
        self.log(f"入力画像: {path}")

        # 入力を選んだら、出力ファイルのデフォルトも提案（同じフォルダ）
        default_out = self.input_file.with_name(f"{self.input_file.stem}_silhouette.png")
        self.output_file = default_out

        # 短縮表示にする
        self.lbl_out_file.configure(text=shorten_path(str(self.output_file)))
        # あるいは WindowsでもPath→strでOKなので：
        # self.lbl_out_file.configure(text=shorten_path(self.output_file.as_posix()))


    def on_pick_output_file(self) -> None:
        if self.input_file is None:
            messagebox.showwarning("注意", "先に入力画像を選択してください。")
            return

        path = filedialog.asksaveasfilename(
            title="出力PNGを保存",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png")]
        )
        if not path:
            return

        self.output_file = Path(path)
        self.lbl_out_file.configure(text=shorten_path(path))
        self.log(f"出力ファイル: {path}")

    def on_pick_input_dir(self) -> None:
        path = filedialog.askdirectory(title="入力フォルダを選択")
        if not path:
            return

        self.input_dir = Path(path)
        self.lbl_in_dir.configure(text=shorten_path(path))
        self.log(f"入力フォルダ: {path}")


    def on_pick_output_dir(self) -> None:
        path = filedialog.askdirectory(title="出力フォルダを選択")
        if not path:
            return

        self.output_dir = Path(path)
        self.lbl_out_dir.configure(text=shorten_path(path))
        self.log(f"出力フォルダ: {path}")


    def on_pick_texture(self) -> None:
        path = filedialog.askopenfilename(
            title="質感テクスチャ画像を選択（任意）",
            filetypes=[("Image", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"), ("All", "*.*")]
        )
        if not path:
            return

        self.var_texture_path.set(path)

        # 短縮表示
        self.lbl_texture.configure(text=shorten_path(path))

        self.log(f"テクスチャ: {path}")

    # ----------------------------
    # プレビュー
    # ----------------------------

    def on_update_preview(self) -> None:
        """
        プレビューは「自動更新しない」要件なので、ボタン押下で更新します。
        """
        if self.input_file is None or not self.input_file.exists():
            messagebox.showwarning("注意", "プレビューする入力画像が未選択です。")
            return

        try:
            # 入力読み込み
            self._preview_in_pil = Image.open(self.input_file).convert("RGBA")

            # 出力生成（メモリ内）
            params = self.get_params()
            self._preview_out_pil = generate_silhouette_rgba(self._preview_in_pil, params)

            self._render_previews()
            self.log("プレビュー更新しました。")
        except Exception as e:
            self.log(f"プレビュー失敗: {e}")
            messagebox.showerror("エラー", f"プレビューに失敗しました。\n\n{e}")

    def _render_previews(self) -> None:
        """
        Canvasサイズに合わせて縮小表示（大きい画像もOK）
        """
        # 入力
        if self._preview_in_pil is not None:
            self._preview_in_tk = self._pil_to_tk_thumbnail(self._preview_in_pil, self.canvas_in)
            self._draw_on_canvas(self.canvas_in, self._preview_in_tk)

        # 出力
        if self._preview_out_pil is not None:
            self._preview_out_tk = self._pil_to_tk_thumbnail(self._preview_out_pil, self.canvas_out)
            self._draw_on_canvas(self.canvas_out, self._preview_out_tk)

    def _pil_to_tk_thumbnail(self, img: Image.Image, canvas: tk.Canvas) -> ImageTk.PhotoImage:
        """
        PIL -> Canvas に収まるサイズへ縮小 -> PhotoImage化
        ※ アスペクト比維持
        """
        cw = max(10, canvas.winfo_width())
        ch = max(10, canvas.winfo_height())

        # 余白を考慮して少し小さめに
        max_w = int(cw * 0.95)
        max_h = int(ch * 0.95)

        w, h = img.size
        scale = min(max_w / w, max_h / h, 1.0)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))

        thumb = img.resize((new_w, new_h), Image.LANCZOS)

        # 透明が分かりやすいよう、暗い背景の上に描画する前提
        return ImageTk.PhotoImage(thumb)

    def _draw_on_canvas(self, canvas: tk.Canvas, photo: ImageTk.PhotoImage) -> None:
        canvas.delete("all")
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        # 中央配置
        canvas.create_image(cw // 2, ch // 2, image=photo, anchor="center")

    # ----------------------------
    # 単発 実行
    # ----------------------------

    def on_run_single(self) -> None:
        if self.input_file is None or not self.input_file.exists():
            messagebox.showwarning("注意", "入力画像が未選択です。")
            return
        if self.output_file is None:
            messagebox.showwarning("注意", "出力ファイルが未選択です。")
            return

        params = self.get_params()

        try:
            self.log(f"単発処理開始: {self.input_file.name}")
            process_file_to_file(self.input_file, self.output_file, params)
            self.log(f"保存しました: {self.output_file.name}")
            messagebox.showinfo("完了", f"保存しました。\n{self.output_file}")
        except Exception as e:
            self.log(f"単発処理エラー: {e}")
            messagebox.showerror("エラー", f"処理に失敗しました。\n\n{e}")

    # ----------------------------
    # 一括 実行（thread）
    # ----------------------------

    def on_run_batch(self) -> None:
        if self._worker_thread and self._worker_thread.is_alive():
            messagebox.showwarning("注意", "すでに一括処理が実行中です。")
            return

        if self.input_dir is None or not self.input_dir.exists():
            messagebox.showwarning("注意", "入力フォルダが未選択です。")
            return
        if self.output_dir is None:
            messagebox.showwarning("注意", "出力フォルダが未選択です。")
            return

        # 入力フォルダからPNGを列挙
        pngs = sorted(self.input_dir.glob("*.png"))
        if not pngs:
            messagebox.showinfo("情報", "入力フォルダ内に PNG が見つかりませんでした。")
            return

        self._cancel_event.clear()
        self.btn_cancel.configure(state=tk.NORMAL)

        # 進捗バー初期化
        self.progress.configure(value=0, maximum=len(pngs))
        self.lbl_progress.configure(text=f"0 / {len(pngs)}")

        # ワーカースレッド開始
        params = self.get_params()
        self._worker_thread = threading.Thread(
            target=self._batch_worker,
            args=(pngs, self.output_dir, params),
            daemon=True
        )
        self._worker_thread.start()
        self.log(f"一括処理開始: {len(pngs)}枚")

    def on_cancel(self) -> None:
        if self._worker_thread and self._worker_thread.is_alive():
            self._cancel_event.set()
            self.log("キャンセル要求を受け付けました（安全に停止します）。")

    def _batch_worker(self, files: List[Path], out_dir: Path, params: SilhouetteParams) -> None:
        """
        別スレッドで実行される一括処理。
        UI更新は queue 経由で行う（Tkinterはスレッドセーフではないため）。
        """
        total = len(files)
        processed = 0
        errors = 0

        for p in files:
            if self._cancel_event.is_set():
                self._queue.put(("done", processed, total, errors, True))
                return

            try:
                out_path = make_unique_output_path(out_dir, p.stem)
                process_file_to_file(p, out_path, params)
                processed += 1
                self._queue.put(("progress", processed, total, p.name, None))
            except Exception as e:
                processed += 1
                errors += 1
                self._queue.put(("progress", processed, total, p.name, str(e)))

        self._queue.put(("done", processed, total, errors, False))

    def _poll_queue(self) -> None:
        """
        queue に溜まった通知を処理してUIへ反映する（after で定期実行）
        """
        try:
            while True:
                item = self._queue.get_nowait()

                kind = item[0]
                if kind == "progress":
                    processed, total, filename, err = item[1], item[2], item[3], item[4]

                    # 進捗更新
                    self.progress.configure(value=processed)
                    self.lbl_progress.configure(text=f"{processed} / {total}")

                    # ログ
                    if err is None:
                        self.log(f"OK: {filename}")
                    else:
                        self.log(f"NG: {filename} / {err}")

                elif kind == "done":
                    processed, total, errors, canceled = item[1], item[2], item[3], item[4]
                    self.btn_cancel.configure(state=tk.DISABLED)

                    if canceled:
                        self.log(f"一括処理はキャンセルされました（{processed}/{total}、エラー{errors}件）")
                        messagebox.showinfo("キャンセル", f"キャンセルしました。\n{processed}/{total}（エラー{errors}件）")
                    else:
                        self.log(f"一括処理完了（{processed}/{total}、エラー{errors}件）")
                        messagebox.showinfo("完了", f"一括処理が完了しました。\n{processed}/{total}（エラー{errors}件）")

        except queue.Empty:
            pass

        # 次回ポーリング
        self.after(100, self._poll_queue)

    # ----------------------------
    # 入力欄とスライダーの同期
    # ----------------------------

    def _sync_int_scale(self, var: tk.IntVar, entry: ttk.Entry) -> None:
        """
        ttk.Scale は float を返すので、表示は int に整えて entry に反映する
        """
        v = int(float(var.get()))
        var.set(v)
        entry.delete(0, tk.END)
        entry.insert(0, str(v))

    def _sync_float_scale(self, var: tk.DoubleVar, entry: ttk.Entry) -> None:
        """
        float系（フェザー）は小数2桁表示にして entry に反映する
        """
        v = float(var.get())
        entry.delete(0, tk.END)
        entry.insert(0, f"{v:.2f}")

    def _bind_entry_int(self, entry: ttk.Entry, var: tk.IntVar, lo: int, hi: int) -> None:
        """
        entry の手入力値を var に反映（Enter またはフォーカスアウト）
        """

        def apply_value(_event=None) -> None:
            try:
                v = int(entry.get().strip())
                v = clamp_int(v, lo, hi)
                var.set(v)
                # 正規化した値を戻す
                entry.delete(0, tk.END)
                entry.insert(0, str(v))
            except Exception:
                # 入力が壊れていたら var の値を戻す
                entry.delete(0, tk.END)
                entry.insert(0, str(var.get()))

        entry.bind("<Return>", apply_value)
        entry.bind("<FocusOut>", apply_value)

    def _bind_entry_float(self, entry: ttk.Entry, var: tk.DoubleVar, lo: float, hi: float) -> None:
        """
        entry の手入力値を var に反映（Enter またはフォーカスアウト）
        """

        def apply_value(_event=None) -> None:
            try:
                v = float(entry.get().strip())
                v = clamp_float(v, lo, hi)
                var.set(v)
                entry.delete(0, tk.END)
                entry.insert(0, f"{v:.2f}")
            except Exception:
                entry.delete(0, tk.END)
                entry.insert(0, f"{var.get():.2f}")

        entry.bind("<Return>", apply_value)
        entry.bind("<FocusOut>", apply_value)


def main() -> None:
    # random を毎回同じにしたい場合は seed を固定してください（ここでは自然なムラを優先して未固定）
    app = SukekageApp()
    app.mainloop()


if __name__ == "__main__":
    main()
