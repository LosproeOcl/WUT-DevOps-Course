# -*- coding: utf-8 -*-
"""FastAPI pages and API routes for the Cars CRUD app."""
import os

from fastapi import Depends, FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import database
from .schemas import CarInput

DB_ENV = "CARS_DB_PATH"
DEFAULT_DB = "cars.db"

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(title="Cars CRUD")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


def get_db_path() -> str:
    return os.environ.get(DB_ENV, DEFAULT_DB)


def get_db() -> str:
    path = get_db_path()
    database.initialize(path)
    return path


# --------------------------------------------------------------------------
# HTML pages
# --------------------------------------------------------------------------
def _page(body: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Cars CRUD</title>"
        "<link rel='stylesheet' href='/static/style.css'></head>"
        f"<body>{body}</body></html>"
    )


def _list_page(db) -> str:
    cars = database.list_cars(db)
    rows = "".join(
        f"<li><a href='/cars/{c.id}'>{c.make} {c.model}</a>"
        f" ({c.year}) — <a href='/cars/{c.id}/edit'>Edit car</a></li>"
        for c in cars
    )
    return _page(
        "<h1>Cars</h1>"
        f"<a href='/cars/new'>Create car</a>"
        f"<ul>{rows or '<li>No cars yet.</li>'}</ul>"
    )


def _new_page() -> str:
    body = """
    <h1>Create car</h1>
    <form id="create-form">
      <label for="make">Make</label>
      <input id="make" name="make" required>
      <label for="model">Model</label>
      <input id="model" name="model" required>
      <label for="year">Year</label>
      <input id="year" name="year" type="number" required>
      <label for="color">Color</label>
      <input id="color" name="color" required>
      <button type="submit">Create car</button>
    </form>
    <script>
    document.getElementById('create-form').addEventListener('submit', async function (e) {
      e.preventDefault();
      const fd = new FormData(e.target);
      const payload = {
        make: fd.get('make'),
        model: fd.get('model'),
        year: Number(fd.get('year')),
        color: fd.get('color'),
      };
      const res = await fetch('/api/cars', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      if (!res.ok) { alert('Failed to create car'); return; }
      const car = await res.json();
      window.location.href = '/cars/' + car.id;
    });
    </script>
    """
    return _page(body)


def _detail_page(car) -> str:
    return _page(
        f"<h1>{car.make} {car.model}</h1>"
        f"<p>Make: <span id='car-make'>{car.make}</span></p>"
        f"<p>Model: <span id='car-model'>{car.model}</span></p>"
        f"<p>Year: <span id='car-year'>{car.year}</span></p>"
        f"<p>Color: <span id='car-color'>{car.color}</span></p>"
        f"<p><a href='/cars/{car.id}/edit'>Edit car</a></p>"
        "<p><a href='/cars'>Back to list</a></p>"
    )


def _edit_page(car) -> str:
    return _page(
        f"<h1>Edit car</h1>"
        f"<form method='post' action='/cars/{car.id}/edit'>"
        f"<label for='make'>Make</label>"
        f"<input id='make' name='make' value='{car.make}'>"
        f"<label for='model'>Model</label>"
        f"<input id='model' name='model' value='{car.model}'>"
        f"<label for='year'>Year</label>"
        f"<input id='year' name='year' type='number' value='{car.year}'>"
        f"<label for='color'>Color</label>"
        f"<input id='color' name='color' value='{car.color}'>"
        f"<button type='submit'>Save changes</button>"
        f"</form>"
    )


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse("/cars")


@app.get("/cars", response_class=HTMLResponse)
def list_page(db: str = Depends(get_db)):
    return HTMLResponse(_list_page(db))


@app.get("/cars/new", response_class=HTMLResponse)
def new_page():
    return HTMLResponse(_new_page())


@app.get("/cars/{car_id}", response_class=HTMLResponse)
def detail_page(car_id: int, db: str = Depends(get_db)):
    car = database.get_car(db, car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    return HTMLResponse(_detail_page(car))


@app.get("/cars/{car_id}/edit", response_class=HTMLResponse)
def edit_page(car_id: int, db: str = Depends(get_db)):
    car = database.get_car(db, car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    return HTMLResponse(_edit_page(car))


@app.post("/cars/{car_id}/edit")
def edit_car(
    car_id: int,
    make: str = Form(...),
    model: str = Form(...),
    year: int = Form(...),
    color: str = Form(...),
    db: str = Depends(get_db),
):
    if database.get_car(db, car_id) is None:
        raise HTTPException(status_code=404, detail="Car not found")
    car_input = CarInput(make=make, model=model, year=year, color=color)
    database.update_car(db, car_id, car_input)
    return RedirectResponse(f"/cars/{car_id}", status_code=303)


# --------------------------------------------------------------------------
# JSON API
# --------------------------------------------------------------------------
@app.post("/api/cars", status_code=201)
def create_car_api(payload: CarInput, db: str = Depends(get_db)):
    car = database.create_car(db, payload)
    return JSONResponse(
        status_code=201,
        content=car.model_dump(),
        headers={"Location": f"/api/cars/{car.id}"},
    )


@app.get("/api/cars")
def list_cars_api(db: str = Depends(get_db)):
    return [c.model_dump() for c in database.list_cars(db)]


@app.get("/api/cars/{car_id}")
def get_car_api(car_id: int, db: str = Depends(get_db)):
    car = database.get_car(db, car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="Car not found")
    return car.model_dump()


@app.put("/api/cars/{car_id}")
def update_car_api(car_id: int, payload: CarInput, db: str = Depends(get_db)):
    if database.get_car(db, car_id) is None:
        raise HTTPException(status_code=404, detail="Car not found")
    return database.update_car(db, car_id, payload).model_dump()


@app.delete("/api/cars/{car_id}")
def delete_car_api(car_id: int, db: str = Depends(get_db)):
    database.delete_car(db, car_id)
    return {"deleted": car_id}
