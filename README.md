# Viser + Gradio

Demo for integrating [viser](https://github.com/nerfstudio-project/viser) 3D
visualizations into a [Gradio](https://www.gradio.app/) application.

- Uses Gradio's session management to create isolated 3D visualization contexts.
- Exposes both Gradio and Viser over the same port.

## Demo

```bash
pip install gradio viser
python demo.py
```

## Usage

```python
import gradio as gr
import fastapi
from viser_proxy_manager import ViserProxyManager

# Create FastAPI app and Viser manager
app = fastapi.FastAPI()
viser_manager = ViserProxyManager(app)

# Create Gradio interface with embedded Viser visualization
with gr.Blocks(title="Viser Viewer") as demo:
    gr.Markdown("# 3D Visualization")
    iframe_html = gr.HTML("")

    @demo.load(outputs=[iframe_html])
    def start_server(request: gr.Request):
        # Start a Viser server for this session
        viser_manager.start_server(request.session_hash)
        host = request.headers["host"]
        return f"""<iframe src="http://{host}/viser/{request.session_hash}/"
                 width="100%" height="500px"></iframe>"""

    # Clean up when session ends
    @demo.unload
    def stop(request: gr.Request):
        viser_manager.stop_server(request.session_hash)

# Mount and run
app = gr.mount_gradio_app(app, demo, path="/")
```
