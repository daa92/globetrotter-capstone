"""
app/routers/itineraries.py

Trip-planning CRUD, scoped to the authenticated user.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app import storage
from app.dependencies import get_current_user
from app.schemas import Itinerary, ItineraryCreate

router = APIRouter(prefix="/itineraries", tags=["itineraries"])


@router.post("", response_model=Itinerary, status_code=status.HTTP_201_CREATED)
def create_itinerary(payload: ItineraryCreate, user: dict = Depends(get_current_user)):
    itinerary = {
        "id": str(uuid.uuid4()),
        "username": user["username"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        **payload.model_dump(mode="json"),
    }
    storage.append(storage.ITINERARIES_FILE, itinerary)
    return Itinerary(**itinerary)


@router.get("", response_model=list[Itinerary])
def list_my_itineraries(user: dict = Depends(get_current_user)):
    itineraries = storage.read_all(storage.ITINERARIES_FILE)
    mine = [it for it in itineraries if it["username"] == user["username"]]
    return [Itinerary(**it) for it in mine]


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_itinerary(itinerary_id: str, user: dict = Depends(get_current_user)):
    itineraries = storage.read_all(storage.ITINERARIES_FILE)
    match = next((it for it in itineraries if it["id"] == itinerary_id), None)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Itinerary not found")
    if match["username"] != user["username"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your itinerary")
    storage.delete_one(storage.ITINERARIES_FILE, "id", itinerary_id)
    return None
