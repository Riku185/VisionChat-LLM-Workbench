# Vision Chat: LLM Performance Workbench 🚀

Vision Chat is a dynamic, multi-model desktop environment engineered for interacting with local Large Language Models (LLMs) and Vision Models via [Ollama](https://ollama.com/). Built from the ground up with a highly responsive **PyQt6** interface, it transcends typical chat clients by serving as a full-fledged **Performance Workbench**. It integrates advanced UI features, session management, and production-grade real-time hardware telemetry to offer an unparalleled local AI experience.

## ✨ Comprehensive Feature Guide

Here is a detailed breakdown of what Vision Chat has to offer:

### 1. Multi-Model Engine & Vision Integration
- **Dynamic Model Selector:** Automatically fetches and categorizes locally available models from your Ollama instance.
- **Seamless Switching:** Switch instantly between text-only and vision-capable local models without restarting the application.
- **Image Upload Area:** Intuitive drag-and-drop or click-to-upload interface for providing visual context to multi-modal networks.

### 2. Real-Time Hardware Telemetry (Stats Panel)
Monitor your system's health live with highly accurate, gradient-filled graphs:
- **Granular Tracking:** Features 1 MB granularity tracking for CPU, RAM, GPU, and VRAM.
- **High-Frequency Polling:** Match Windows Task Manager refresh rates for near real-time accuracy.
- **Advanced GPU Metrics:** Native `nvidia-smi` integration tracks **Live GPU Temperature** and **Power Consumption**.

### 3. High-Fidelity Inference Analytics
Deep dive into your local model's performance on a per-response basis:
- **Tokens Per Second (TPS):** Track exact generation speed with a dedicated live gauge.
- **Latency Tracking:** Measures critical metrics like Time-to-First-Token (TTFT) and total response duration.
- **State Indicators:** Real-time feedback on model state (Idle, Loading, Running).

### 4. Floating Performance Overlay
- **Global Monitoring:** A detachable, frameless, and draggable "FPS-counter style" overlay.
- **Always on Top:** Keeps critical LLM inference stats (TPS, Latency, VRAM) visible on your desktop while you work in other IDEs or applications.

### 5. Dynamic Context Window Visualizer
- **Context Bar:** A visual tracker that helps you monitor exactly how much of the LLM's context window is currently being consumed by the conversation, preventing out-of-memory errors and context truncation.

### 6. Advanced UI & Chat Experience
- **Rich Text & Code Rendering:** Full Markdown support with code block syntax highlighting.
- **Pinch-to-Zoom:** Easily scale text size dynamically with touchpad gestures for accessibility and comfort.
- **Session Management:** Robust tools to organize, import, export, and persist your chat sessions securely.

### 7. Integrated Developer Tools
- **Terminal Panel:** A built-in terminal logging interface that surfaces system warnings, inference state changes, and Ollama server logs right inside the application.

---

## 🛠️ Prerequisites

Before you begin, ensure you have met the following requirements:
* **Operating System:** Windows (Required for accurate `nvidia-smi` telemetry and memory polling)
* **Python Version:** Python 3.10 or higher
* **Local LLM Engine:** [Ollama](https://ollama.com/) must be installed and running in the background.
* **NVIDIA GPU:** Required for full hardware telemetry (VRAM, Temperature, Power).

## 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YourUsername/VisionChat-LLM-Workbench.git
   cd VisionChat-LLM-Workbench
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   # Activate on Windows:
   venv\Scripts\activate
   ```

3. **Install the required dependencies:**
   ```bash
   pip install PyQt6 pyqtgraph psutil GPUtil numpy
   ```

## 🚀 Usage

1. Make sure **Ollama** is running on your machine.
2. Launch the application:
   ```bash
   python -m app.main
   ```
3. The app will automatically fetch available models. Select a model from the right-hand menu panel and click **Load Model** to begin chatting.
4. Toggle the **Performance Overlay** from the menu to keep an eye on hardware stats while you work in other applications!

## 📸 Screenshots

Screenshots of the app are available in the assets folder, Kindly check 'em out for as to how the app looks

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
