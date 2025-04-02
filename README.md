---
title: Viser Gradio Embed
emoji: 🚀
colorFrom: blue
colorTo: pink
sdk: docker
app_port: 7860
pinned: false
---

# Viser + Gradio

Demo for integrating [viser](https://github.com/nerfstudio-project/viser) 3D
visualizations into a [Gradio](https://www.gradio.app/) application.

- Uses Gradio's session management to create isolated 3D visualization contexts.
- Exposes both Gradio and Viser over the same port.

## Deploying on HuggingFace Spaces

**[ [Live example](https://brentyi-viser-gradio-embed.hf.space/) ]**

This repository should work out-of-the-box with HF Spaces via Docker.

- Unlike a vanilla Gradio Space, this is unfortunately not supported by [ZeroGPU](https://huggingface.co/docs/hub/en/spaces-zerogpu).

## Local Demo

```bash
pip install -r requirements.txt
python app.py
```

https://github.com/user-attachments/assets/b94a117a-b9e5-4854-805a-8666941c7816
