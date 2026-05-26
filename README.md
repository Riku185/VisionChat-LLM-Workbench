# Vision Chat: LLM Performance Workbench 🚀

Vision Chat is a dynamic, multi-model desktop environment designed for interacting with local Large Language Models (LLMs) and Vision Models via [Ollama](https://ollama.com/). Built with a sleek **PyQt6** interface, it serves not only as a chat client but as a full-fledged **Performance Workbench**, offering real-time hardware telemetry and inference analytics.

## ✨ Features

- **Multi-Model Support:** Seamlessly switch between text-only and vision-capable local models available on your Ollama server.
- **Real-Time Telemetry Sidebar:** Monitor your system's health live with gradient-filled graphs tracking:
  - CPU & RAM usage
  - GPU & VRAM usage (Absolute and Percentage)
  - **Live GPU Temperature & Power Consumption** (via `nvidia-smi`)
- **Live Inference Stats:** Track your model's performance with a dedicated **Tokens Per Second (TPS)** gauge and state indicator (Idle, Loading, Running).
- **Floating Performance Overlay:** A detachable, frameless, and draggable "FPS-counter style" overlay showing critical metrics (TPS, Latency, VRAM) on top of other windows.
- **Session Analytics & Management:** Export/import chat sessions and view peak memory/VRAM usage during inference.

## 🛠️ Prerequisites

Before you begin, ensure you have met the following requirements:
* **Operating System:** Windows (for accurate `nvidia-smi` and memory polling)
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

Screenshots is available in the assets folder, Kindly check 'em out over there

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
