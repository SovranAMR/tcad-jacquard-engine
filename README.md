<div align="center">

# 🌐 TCAD: Professional Jacquard Weaving CAD 

![Version](https://img.shields.io/badge/Version-5.0.0-blue.svg)
![Build](https://img.shields.io/badge/Build-Passing-brightgreen.svg)
![Python](https://img.shields.io/badge/Python-3.12-yellow.svg)
![Qt](https://img.shields.io/badge/PySide6-GUI-orange.svg)
![License](https://img.shields.io/badge/License-Proprietary-red.svg)

```text
             ______                                                                                               
          .-'      `-.                                                                                            
         /            \                                                                                           
        |              |                                                                                          
        |,  .-.  .-.  ,|       ___________  ______           ___       ________  
        | )(__/  \__)( |      ("     _   ")/" _  "\         /   \     |"      "\ 
        |/     /\     \|       )__/  \\__/(: ( \___)       /  ^  \    (.  ___  :)
        (_     ^^     _)          \\_ /    \/ \           /  /_\  \   |: \   ) ||
         \__|IIIIII|__/           |.  |    //  \ _       /  _____  \  (| (___\ ||
          | \IIIIII/ |            \:  |   (:   _) \     /  /     \  \ |:       :)
          \          /             \__|    \_______)   /__/       \__\(________/ 
           `--------`                                                             

========================================================================================================
    T E X T I L E   C O M P U T E R - A I D E D   D E S I G N   &   I N D U S T R I A L   E N G I N E
========================================================================================================
```

*An industrial-grade, ultra-high-performance Textile Design & CAM export engine for electronic Jacquard looms.*

</div>

<p align="center">
  <b>Meta Tags:</b> <code>#JacquardCAD</code> <code>#TextileEngineering</code> <code>#WeavingCAM</code> <code>#StaubliJC5</code> <code>#FabricSimulation</code>
</p>

---

<details>
<summary><b>🤖 LLM / AI / SEO Context (Click to Expand)</b></summary>

```xml
<tcad-meta-data>
  <seo>
    <keywords>jacquard weave, textile design software, CAD/CAM textile, Staubli JC5 export, weave density calculator, 3d fabric rendering, python PySide6 textile</keywords>
    <description>Open-source architecture for professional textile CAD software targeting heavy-duty Jacquard looms with up to 20,000 hooks.</description>
    <geo>Global, Textile Hubs (Turkey, Italy, China, India, Germany)</geo>
  </seo>
  <llm-context>
    <architecture>Python 3.12, PySide6, NumPy, Vectorized Operations</architecture>
    <core-features>Zero-Copy UI rendering, Sparse Delta History (Undo/Redo), hardware-level JC5 binary packing, Weft Selector signal generation, 3D ambient occlusion bump mapping for textiles.</core-features>
    <agent-role>Industrial CAD System Architecture</agent-role>
  </llm-context>
</tcad-meta-data>
```
</details>

---

## 🚀 Overview

TCAD is a highly optimized, professional-grade computer-aided design (CAD) and manufacturing (CAM) software built specifically for **Electronic Jacquard Weaving**. It bridges the gap between artistic textile pattern design and raw industrial loom hardware. 

Gone are the days of sluggish, gigabyte-consuming legacy textile software. Powered by **NumPy Vectorization** and **PySide6 Zero-Copy rendering**, TCAD allows real-time manipulation of massive `5120x10000` hook matrices without breaking a sweat.

```text
          [     J A C Q U A R D   M A C H I N E   H E A D     ]
          =====================================================
          | . . . . . . . . . . . . . . . . . . . . . . . . . | <--- (JC5 / EPJ Input Data)
          |  [1]   [0]   [1]   [1]   [0]   [0]   [1]   [1]    | <--- Electromagnets
          |===|=====|=====|=====|=====|=====|=====|=====|=====|
              |     |     |     |     |     |     |     |   
              v     |     v     v     |     |     v     v   <--- Knives Lifting Hooks
             _^_   _|_   _^_   _^_   _|_   _|_   _^_   _^_  
            ( O ) (   ) ( O ) ( O ) (   ) (   ) ( O ) ( O ) <--- Lifting Hooks
             | |   | |   | |   | |   | |   | |   | |   | |  
             | |   | |   | |   | |   | |   | |   | |   | |  
~~~~~~~~~~~~~|~|~~~|~|~~~|~|~~~|~|~~~|~|~~~|~|~~~|~|~~~|~|~~~~ <--- Harness Cords
             \ /   \ /   \ /   \ /   \ /   \ /   \ /   \ /  
              V     V     V     V     V     V     V     V   
              |     |     |     |     |     |     |     |   
             [ ]   [ ]   [ ]   [ ]   [ ]   [ ]   [ ]   [ ]  <--- Heddles (Mails)
             /_\   /_\   /_\   /_\   /_\   /_\   /_\   /_\  
Warp Thread   |     |     |     |     |     |     |     |   
===========- -+- - -+- - -+- - -+- - -+- - -+- - -+- - -+- -===========
 Weft Pick --->================================================----->
===========- -+- - -+- - -+- - -+- - -+- - -+- - -+- - -+- -===========
              |     |     |     |     |     |     |     |   
             (O)   (O)   (O)   (O)   (O)   (O)   (O)   (O)  <--- Return Springs (Lingoes)
             ===   ===   ===   ===   ===   ===   ===   ===  
```

## 🔥 Core Engine Capabilities

### 1. 🏎️ Sparse-Delta Undo/Redo Engine
Drawing on a `10,000 x 5,120` pixel canvas is computationally expensive. Traditional software crashes due to Out-Of-Memory (OOM) errors. TCAD utilizes an **O(1) Sparse Numpy Delta** architecture. Instead of cloning 50MB canvases on every pencil stroke, the `PatchCommand` extracts only the modified non-zero coordinates (`x, y, old, new`), dropping the RAM consumption per stroke from megabytes to literal **bytes**.

### 2. 🦾 Staubli JC5 Hardware Compiler
It doesn't just export graphics; it exports **Machine Signals**. 
The `StaubliJC5Adapter` translates high-level textile elements into reverse-engineered `4800-hook` constraints. Furthermore, it strictly engineers **Weft Selector Channels** (Hooks `5112-5119`) converting physical yarn choices into binary control picks perfectly synced for the loom's mechanical shuttles.

### 3. 🕸️ 3D Fabric Physical Simulation (Bump Mapping)
Switch to the **3D Weave View (Örgü Görünümü)** to witness your point-paper translate into reality in real-time.
- **Physical Scaling:** Employs precise Aspect Ratio transformation via `QTransform`, dynamically scaling the view based on physical *Ends per cm (Warp)* and *Picks per cm (Weft)*.
- **Micro-Shadowing:** A vectorized shader computes Ambient Occlusion natively based on thread intersections, giving you a 3D specular highlight view of the fabric *without* any OpenGL dependencies.

### 4. 🪢 Auto-Float Fixer with Aesthetic Saten Ties
Long floats (atlamalar) destroy weaves. The built-in `ValidationEngine` automatically hunts down structurally weak warp/weft loops.
Instead of dropping random visual dots (defects) to tie down floats, the **Red-Team Algorithm** mathematically interpolates a `1/7 Twill or Saten step` `(x + y*3) % 7 == 0`. It ties down long floats beautifully, hiding the structural corrections inside invisible geometric patterns.

---

## 🛠️ Installation & Execution

### Prerequisites
- Operating System: **Linux (Native/X11/Wayland)**, macOS, or Windows.
- Runtime: **Python 3.12+**
- Memory: Minimum **4GB RAM** (8GB+ recommended for 10,000+ hook patterns).

```bash
# Clone the Repository
git clone https://github.com/sovranamr/tcad-jacquard-engine.git

# Enter the directory & activate Virtual Environment 
cd tcad-jacquard-engine && source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Launch the Application
python3 run.py
```

<div align="center">

```text
       _________________________________________________________________________________
      /                                                                                 \
     |    _________________________________________________________________________      |
     |   |                                                                         |     |
     |   |  root@tcad-engine:~/jacquard-workspace# ./tcad_compile --target=jc5     |     |
     |   |  > [INFO] Initializing Zero-Copy Canvas Engine... [OK]                  |     |
     |   |  > [INFO] Allocated 5120 Hooks. Matrix Base: 0x7FFA2B4C...              |     |
     |   |  > [PROCESS] Analyzing Weave Structures in Document (10000x5120)        |     |
     |   |                                                                         |     |
     |   |  [===---------] Scanning Floats (Atlama)... 25%                         |     |
     |   |  [=====-------] Applying Satin/Twill Bounds... 50%                      |     |
     |   |  [==========--] Injecting Weft Selector Signals (5112-5119)... 85%      |     |
     |   |  [============] Packing Binary Payload Header... 100%                   |     |
     |   |                                                                         |     |
     |   |  > [SUCCESS] Export Complete: `production_R12.jc5` (2.4 MB)             |     |
     |   |  > [WARN] Max hook density utilized: 97.4%                              |     |
     |   |  root@tcad-engine:~/jacquard-workspace# _                               |     |
     |   |_________________________________________________________________________|     |
     |                                                                                   |
      \_________________________________________________________________________________/
             \___________________________________________________________________/
           _________________________________________________________________________
          /|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||\
         /|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||\
```

</div>

---

## 🏗️ Architecture & Data Flow

TCAD strictly follows a unidirectional data pipeline separating the artistic frontend from the hardware CAM compiler.

```text
  [ CanvasView (PySide6) ] <----( Zero-Copy Read )----
             |                                       |
    ( User Input / Strokes )                         |
             v                                       |
  [ QUndoStack (PatchCommand) ]                      |
             |                                       |
    ( O(1) Sparse Deltas )                           |
             v                                       |
  [  Document (Central State) ] ----------------------
             |
    ( 1. Weave Expansion (Twills/Satins) )
    ( 2. ValidationEngine (Float Fixing) )
             v
  [ Hardware AdapterRegistry ]
             |
             +---> [ StaubliJC5Adapter ] -> .jc5 Binary
             +---> [ BonasEPJAdapter ]   -> .epj Binary (WIP)
             +---> [ GrosseAdapter ]     -> .wea Binary (WIP)
```

| Core Module | Purpose |
| ----------- | ------- |
| `domain.py` | State Management. Holds `Document`, `Yarn`, `Sparse Deltas` |
| `canvas.py` | PySide6 Zero-Copy rendering pipeline for 2D Canvas & 3D Shaders |
| `weaves.py` | Mathematical generation of foundational patterns (Plain, Twill, Satin) |
| `mapping.py` | Machine Hook Mapping arrays and Cast-Out (Boş Bırakma) logic |
| `validation.py` | Structural intelligence: Float-fixing, weak point tracking |
| `tech_sheet.py` | Production estimates, Yarn density, Cost calculation (Tex/gsm) |
| `adapters.py` | Physical hardware transpilers (Bit-packing, Selector injections) |
| `fileio.py` | `.tcad` zipped binary archive and Red Team shape validation guards |

---

## 📖 Quick Start Workflow

1. **New Project:** Define your canvas size (e.g., `5120 x 4000`).
2. **Technical Layout:** Assign your physical Ends-per-cm (Çözgü Sıklığı) and Picks-per-cm (Atkı Sıklığı).
3. **Color Blocking:** Use the Pencil or Flood Fill tool to sketch the macro artwork.
4. **Apply Weaves:** Select regions and apply industrial weaves (Plain, Satin 5/2, Twill 1/3) onto the underlying colors.
5. **3D Verification:** Switch to **Fabric Mode** to observe physical scaling and ambient-occlusion thread layering.
6. **Compile & Export:** Click `Export JC5`. The constraint engine will split hooks, map threads, calculate physical machine bounds, insert Weft Selectors, and output the proprietary binary payload ready for Staubli USB drives.

---

## 🧪 Industrial Testing Pipeline

Equipped with 130 hardcore unit tests evaluating everything from simple UI inputs to 500-cycle *Torture Runs* manipulating gigabytes of data and corrupted malformed `data.npy` structural spoofing.

```bash
python3 -m pytest tests/ --tb=short
```
*Current Verdict: 130/130 PASSED. Production Ready.*

---

<p align="center">
<b>Developed rigorously for the modern Textile Industry. From Pixels to Jacquard Hooks.</b>
</p>
