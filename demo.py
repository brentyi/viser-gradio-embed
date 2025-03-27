import random

import fastapi
import gradio as gr
import uvicorn

from viser_proxy_manager import ViserProxyManager


def main() -> None:
    app = fastapi.FastAPI()
    viser_manager = ViserProxyManager(app)

    # Create a Gradio interface with title, iframe, and buttons
    with gr.Blocks(title="Viser Viewer") as demo:
        # Add a title and description
        gr.Markdown("# 🌐 Viser Interactive Viewer")

        # Add the iframe with a border
        add_sphere_btn = gr.Button("Add Random Sphere")
        iframe_html = gr.HTML("")

        @demo.load(outputs=[iframe_html])
        def start_server(request: gr.Request):
            assert request.session_hash is not None
            viser_manager.start_server(request.session_hash)

            # Use the request's base URL if available
            host = request.headers["host"]

            return f"""
            <div style="border: 2px solid #ccc; padding: 10px;">
                <iframe src="http://{host}/viser/{request.session_hash}/" width="100%" height="500px" frameborder="0"></iframe>
            </div>
            """

        @add_sphere_btn.click
        def add_random_sphere(request: gr.Request):
            assert request.session_hash is not None
            server = viser_manager.get_server(request.session_hash)

            # Add icosphere with random properties
            server.scene.add_icosphere(
                name=f"sphere_{random.randint(1, 10000)}",
                position=(
                    random.uniform(-1, 1),
                    random.uniform(-1, 1),
                    random.uniform(-1, 1),
                ),
                radius=random.uniform(0.05, 0.2),
                color=(random.random(), random.random(), random.random()),
            )

        @demo.unload
        def stop(request: gr.Request):
            assert request.session_hash is not None
            viser_manager.stop_server(request.session_hash)

    app = gr.mount_gradio_app(app, demo, path="/")
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
