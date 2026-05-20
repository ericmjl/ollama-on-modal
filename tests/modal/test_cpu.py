import modal

image = modal.Image.debian_slim(python_version="3.12").pip_install("httpx", "fastapi")

app = modal.App(name="ollama-test-cpu", image=image)


@app.cls()
@modal.concurrent(max_inputs=100)
class OllamaPassthrough:
    @modal.asgi_app()
    def web_app(self):
        import fastapi
        from fastapi.responses import JSONResponse

        app_fastapi = fastapi.FastAPI()

        @app_fastapi.get("/")
        async def root():
            return JSONResponse(
                {
                    "status": "ok",
                    "message": "Ollama passthrough CPU endpoint is running",
                }
            )

        @app_fastapi.get("/health")
        async def health():
            return JSONResponse({"status": "healthy"})

        return app_fastapi
