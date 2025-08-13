import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from PIL import Image
import mss
import screeninfo

import win32gui

from settings import Settings


app = FastAPI(title="MultiScreenCapt Web")


# Serve the frontend from /web
web_dir = Path(__file__).parent / "web"
web_dir.mkdir(parents=True, exist_ok=True)
app.mount("/web", StaticFiles(directory=str(web_dir), html=True), name="web")


def get_save_directory() -> Path:
    settings = Settings()
    return Path(settings.get_save_directory())


def get_default_save_directory() -> Path:
    settings = Settings()
    return Path(settings.get_default_save_directory())


def sanitize_filename_component(name: str) -> str:
    safe = "".join(c for c in (name or "") if c.isalnum() or c in (" ", "-", "_")).strip()
    return safe.replace(" ", "_") or "Screen"


def detect_screens() -> List[Dict[str, Any]]:
    """Detect screens and apply custom names from settings."""
    monitors = screeninfo.get_monitors()
    settings = Settings()
    custom = settings.get_custom_screen_names() or {}
    screens: List[Dict[str, Any]] = []
    for idx, m in enumerate(monitors):
        left = int(m.x)
        top = int(m.y)
        width = int(m.width)
        height = int(m.height)
        key = f"{width}x{height}_{left}_{top}"
        default_name = getattr(m, "name", f"Screen {idx+1}") or f"Screen {idx+1}"
        name = custom.get(key, default_name)
        screens.append({
            "index": idx,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "key": key,
            "name": name,
        })
    return screens


def list_captures(limit: int = 100) -> List[Dict[str, Any]]:
    save_dir = get_save_directory()
    save_dir.mkdir(parents=True, exist_ok=True)
    images: List[Path] = []
    for p in save_dir.glob("*.png"):
        images.append(p)
    images.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    items: List[Dict[str, Any]] = []
    for p in images[:limit]:
        items.append({
            "filename": p.name,
            "size_bytes": p.stat().st_size,
            "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
            "url": f"/captures/{p.name}",
        })
    return items


def clip_to_any_screen(left: int, top: int, width: int, height: int) -> Dict[str, int] | None:
    screens = detect_screens()
    best = None
    best_overlap = 0
    rect_right = left + width
    rect_bottom = top + height
    for s in screens:
        s_left, s_top = s["left"], s["top"]
        s_right, s_bottom = s_left + s["width"], s_top + s["height"]
        inter_left = max(left, s_left)
        inter_top = max(top, s_top)
        inter_right = min(rect_right, s_right)
        inter_bottom = min(rect_bottom, s_bottom)
        if inter_left < inter_right and inter_top < inter_bottom:
            overlap = (inter_right - inter_left) * (inter_bottom - inter_top)
            if overlap > best_overlap:
                best_overlap = overlap
                best = {
                    "left": inter_left,
                    "top": inter_top,
                    "width": inter_right - inter_left,
                    "height": inter_bottom - inter_top,
                }
    return best


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/web/")


@app.get("/api/screens")
def api_get_screens() -> List[Dict[str, Any]]:
    return detect_screens()


@app.post("/api/capture/screen")
def api_capture_screen(index: int) -> Dict[str, Any]:
    screens = detect_screens()
    if index < 0 or index >= len(screens):
        raise HTTPException(status_code=400, detail="Invalid screen index")
    s = screens[index]

    monitor = {
        "left": int(s["left"]),
        "top": int(s["top"]),
        "width": int(s["width"]),
        "height": int(s["height"]),
    }

    with mss.mss() as sct:
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    save_dir = get_save_directory()
    save_dir.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename_component(s["name"] or f"Screen_{index+1}")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"WebCapture_{safe_name}_{timestamp}.png"
    path = save_dir / filename
    img.save(str(path), "PNG")
    return {"ok": True, "file": filename, "url": f"/captures/{filename}"}


@app.get("/api/windows")
def api_get_windows() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    def enum_cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title or not title.strip():
            return True
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            if width < 200 or height < 150:
                return True
            class_name = win32gui.GetClassName(hwnd)
            items.append({
                "hwnd": int(hwnd),
                "title": title,
                "class_name": class_name,
                "left": int(left),
                "top": int(top),
                "width": int(width),
                "height": int(height),
            })
        except Exception:
            pass
        return True

    win32gui.EnumWindows(enum_cb, None)
    items.sort(key=lambda w: w["title"].lower())
    return items


@app.post("/api/capture/window")
def api_capture_window(hwnd: int) -> Dict[str, Any]:
    if not win32gui.IsWindowVisible(hwnd):
        raise HTTPException(status_code=400, detail="Window is not visible")
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top
    clipped = clip_to_any_screen(left, top, width, height)
    if not clipped:
        raise HTTPException(status_code=400, detail="Window is off-screen")

    with mss.mss() as sct:
        shot = sct.grab({
            "left": clipped["left"],
            "top": clipped["top"],
            "width": clipped["width"],
            "height": clipped["height"],
        })
        img = Image.frombytes("RGB", shot.size, shot.rgb)

    save_dir = get_save_directory()
    save_dir.mkdir(parents=True, exist_ok=True)
    title = (win32gui.GetWindowText(hwnd) or f"window_{hwnd}")
    safe = sanitize_filename_component(title)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"WebCapture_{safe}_{timestamp}.png"
    path = save_dir / filename
    img.save(str(path), "PNG")
    return {"ok": True, "file": filename, "url": f"/captures/{filename}"}


@app.post("/api/capture/all")
def api_capture_all() -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    screens = detect_screens()
    for s in screens:
        try:
            monitor = {
                "left": int(s["left"]),
                "top": int(s["top"]),
                "width": int(s["width"]),
                "height": int(s["height"]),
            }
            with mss.mss() as sct:
                shot = sct.grab(monitor)
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            save_dir = get_save_directory()
            save_dir.mkdir(parents=True, exist_ok=True)
            safe_name = sanitize_filename_component(s["name"]) or f"Screen_{s['index']+1}"
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"WebCapture_{safe_name}_{timestamp}.png"
            path = save_dir / filename
            img.save(str(path), "PNG")
            results.append({"index": s["index"], "ok": True, "file": filename, "url": f"/captures/{filename}"})
        except Exception as e:
            results.append({"index": s["index"], "ok": False, "error": str(e)})
    return {"ok": True, "results": results}


@app.get("/api/captures")
def api_list_captures() -> List[Dict[str, Any]]:
    return list_captures()


@app.get("/captures/{filename}")
def api_get_capture(filename: str) -> FileResponse:
    path = get_save_directory() / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(str(path), media_type="image/png")


# Settings endpoints
@app.get("/api/settings")
def api_get_settings() -> Dict[str, Any]:
    settings = Settings()
    return {
        "save_directory": settings.get_save_directory(),
        "default_save_directory": settings.get_default_save_directory(),
        "custom_screen_names": settings.get_custom_screen_names(),
        "screens": detect_screens(),
    }


@app.post("/api/settings/save_directory")
def api_set_save_directory(path: str) -> Dict[str, Any]:
    if not path or not os.path.isabs(path):
        raise HTTPException(status_code=400, detail="Provide an absolute path")
    try:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        settings = Settings()
        settings.set_save_directory(str(p))
        return {"ok": True, "save_directory": str(p)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/settings/save_directory_reset")
def api_reset_save_directory() -> Dict[str, Any]:
    settings = Settings()
    default_path = get_default_save_directory()
    default_path.mkdir(parents=True, exist_ok=True)
    settings.set_save_directory(str(default_path))
    return {"ok": True, "save_directory": str(default_path)}


@app.post("/api/open_save_directory")
def api_open_save_directory() -> Dict[str, Any]:
    path = get_save_directory()
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class ScreenNameUpdate(BaseModel):
    index: int
    name: str


@app.post("/api/screen_names")
def api_set_screen_names(names: List[ScreenNameUpdate]) -> Dict[str, Any]:
    """Set custom names by screen index: [{"index":0,"name":"LG"}, ...]."""
    screens = detect_screens()
    by_index = {s["index"]: s for s in screens}
    settings = Settings()
    current = settings.get_custom_screen_names() or {}
    updated = dict(current)
    for item in names:
        idx = int(item.index)
        new_name = (item.name or "").strip()
        if idx in by_index and new_name:
            s = by_index[idx]
            key = s["key"]
            updated[key] = new_name
    settings.set_custom_screen_names(updated)
    return {"ok": True, "custom_screen_names": updated, "screens": detect_screens()}


@app.post("/api/screen_names/reset")
def api_reset_screen_names() -> Dict[str, Any]:
    settings = Settings()
    settings.reset_custom_screen_names()
    return {"ok": True, "custom_screen_names": {}, "screens": detect_screens()}


