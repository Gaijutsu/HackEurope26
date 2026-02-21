import os
import uuid
import shutil
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pinterest_dl import PinterestDL

app = FastAPI()
PORT = 8000

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public", "pinterest")
os.makedirs(PUBLIC_DIR, exist_ok=True)

app.mount("/public", StaticFiles(directory="public"), name="public")


@app.get("/pinterest")
async def pinterest_images(
    city: str = Query(..., description="City name"),
    country: str = Query(..., description="Country name"),
):
    if city == "Mock" and country == "United States":
        batch_id = "mock"
        download_dir = os.path.join(PUBLIC_DIR, batch_id)
        image_files = sorted(os.listdir(download_dir))

        links = [f"/public/pinterest/{batch_id}/{fname}" for fname in image_files]

        return links


    query = f"photos of {city} {country}"
    batch_id = uuid.uuid4().hex[:8]
    download_dir = os.path.join(PUBLIC_DIR, batch_id)
    os.makedirs(download_dir, exist_ok=True)
    try:
        images = PinterestDL.with_api().search_and_download(
            query=query,
            output_dir=download_dir,
            num=20,
        )

        image_files = sorted(os.listdir(download_dir))

        links = [f"/public/pinterest/{batch_id}/{fname}" for fname in image_files]

        return links

    except Exception as e:
        shutil.rmtree(download_dir, ignore_errors=True)
        return {"error": str(e), "query": query, "images": []}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
