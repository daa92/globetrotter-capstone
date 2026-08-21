import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus, X, Upload, Loader2 } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { submitPlace, editPlace, uploadPlaceMedia, ApiError } from "../../api/client";

const ALL_TAGS = [
  "beach", "hiking", "culture", "history", "wildlife", "nightlife", "waterfall", "city",
  "nature", "relaxation", "adventure", "mountain", "photography", "scenery", "art",
  "museum", "rainforest", "eco-tourism", "food", "shopping",
];

const MAX_MEDIA_BYTES = 10 * 1024 * 1024;

/**
 * One form, two modes: `place` prop absent = create, present = edit
 * (pre-filled, PATCH on submit). Handles media selection + the 10MB
 * combined-size check client-side (fast feedback) — the backend
 * re-checks this too (never trust client-side validation alone), see
 * POST /places/upload-media.
 */
export default function PlaceForm({ place, onDone, onCancel }) {
  const { t } = useTranslation();
  const { accessToken, user } = useAuth();
  const isEdit = Boolean(place);

  const [name, setName] = useState(place?.name ?? "");
  const [region, setRegion] = useState(place?.region ?? "");
  const [description, setDescription] = useState(place?.description ?? "");
  const [latitude, setLatitude] = useState(place?.latitude ?? "");
  const [longitude, setLongitude] = useState(place?.longitude ?? "");
  const [avgCost, setAvgCost] = useState(place?.avg_cost_fcfa ?? "");
  const [tags, setTags] = useState(place?.tags ?? []);
  const [priceList, setPriceList] = useState(place?.price_list ?? []);
  const [existingImages, setExistingImages] = useState(place?.images ?? []);
  const [existingVideo, setExistingVideo] = useState(place?.video_url ?? null);
  const [newFiles, setNewFiles] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | uploading | saving | error
  const [error, setError] = useState(null);

  const toggleTag = (tag) => setTags((prev) => (prev.includes(tag) ? prev.filter((x) => x !== tag) : [...prev, tag]));

  const addPriceItem = () => setPriceList((prev) => [...prev, { item: "", price_fcfa: 0 }]);
  const updatePriceItem = (i, field, value) =>
    setPriceList((prev) => prev.map((p, idx) => (idx === i ? { ...p, [field]: value } : p)));
  const removePriceItem = (i) => setPriceList((prev) => prev.filter((_, idx) => idx !== i));

  const newFilesSize = newFiles.reduce((sum, f) => sum + f.size, 0);
  const overSizeLimit = newFilesSize > MAX_MEDIA_BYTES;

  const handleFileChange = (e) => setNewFiles(Array.from(e.target.files || []));
  const removeExistingImage = (url) => setExistingImages((prev) => prev.filter((u) => u !== url));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (overSizeLimit) return;
    setError(null);

    let images = existingImages;
    let videoUrl = existingVideo;

    if (newFiles.length > 0) {
      setStatus("uploading");
      try {
        const result = await uploadPlaceMedia(accessToken, newFiles);
        images = [...existingImages, ...result.images];
        videoUrl = result.video_url || existingVideo;
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : t("auth.genericError"));
        setStatus("error");
        return;
      }
    }

    setStatus("saving");
    const payload = {
      name,
      region,
      description,
      latitude: parseFloat(latitude),
      longitude: parseFloat(longitude),
      avg_cost_fcfa: avgCost === "" ? null : parseInt(avgCost, 10),
      tags,
      price_list: priceList.filter((p) => p.item.trim() !== ""),
      images,
      video_url: videoUrl,
    };

    try {
      const result = isEdit ? await editPlace(accessToken, place.id, payload) : await submitPlace(accessToken, payload);
      onDone?.(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("auth.genericError"));
      setStatus("error");
    }
  };

  const busy = status === "uploading" || status === "saving";

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {!isEdit && user?.is_admin && (
        <p className="rounded-lg bg-teal-50 dark:bg-teal-950/40 px-3 py-2 text-xs text-teal-700 dark:text-teal-300">
          {t("places.adminAutoPublish", "As an admin, this publishes immediately — no approval needed.")}
        </p>
      )}
      {isEdit && place.status === "approved" && !user?.is_admin && (
        <p className="rounded-lg bg-amber-50 dark:bg-amber-950/40 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
          {t("places.editRevertsToPending", "Editing a live place sends it back for admin re-approval.")}
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">{t("places.name", "Name")}</label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">{t("places.region", "Region")}</label>
          <input
            required
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            placeholder="e.g. Southwest"
            className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 text-sm"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">{t("places.description", "Description")}</label>
        <textarea
          required
          minLength={20}
          maxLength={2000}
          rows={4}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={t("places.descriptionPlaceholder", "What's it about, what can you do there...")}
          className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 text-sm"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div>
          <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">{t("places.latitude", "Latitude")}</label>
          <input
            required
            type="number"
            step="any"
            min={1.5}
            max={13.5}
            value={latitude}
            onChange={(e) => setLatitude(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">{t("places.longitude", "Longitude")}</label>
          <input
            required
            type="number"
            step="any"
            min={8.0}
            max={16.5}
            value={longitude}
            onChange={(e) => setLongitude(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">{t("places.avgCost", "Avg cost (FCFA)")}</label>
          <input
            type="number"
            min={0}
            value={avgCost}
            onChange={(e) => setAvgCost(e.target.value)}
            className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-2 text-sm"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">{t("places.tags", "Tags")}</label>
        <div className="flex flex-wrap gap-1.5">
          {ALL_TAGS.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => toggleTag(tag)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                tags.includes(tag)
                  ? "bg-teal-600 text-white"
                  : "bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300"
              }`}
            >
              {t(`tags.${tag}`, tag)}
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400">
            {t("places.priceList", "Prices (optional)")}
          </label>
          <button type="button" onClick={addPriceItem} className="text-xs text-teal-700 dark:text-teal-400 inline-flex items-center gap-0.5">
            <Plus size={12} />{t("places.addPriceItem", "Add item")}
          </button>
        </div>
        {priceList.map((p, i) => (
          <div key={i} className="flex items-center gap-2 mb-1.5">
            <input
              value={p.item}
              onChange={(e) => updatePriceItem(i, "item", e.target.value)}
              placeholder={t("places.itemName", "Item / product")}
              className="flex-1 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-1.5 text-sm"
            />
            <input
              type="number"
              min={0}
              value={p.price_fcfa}
              onChange={(e) => updatePriceItem(i, "price_fcfa", parseInt(e.target.value || "0", 10))}
              placeholder="FCFA"
              className="w-28 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-transparent px-3 py-1.5 text-sm"
            />
            <button type="button" onClick={() => removePriceItem(i)} className="text-neutral-400 hover:text-red-500">
              <X size={16} />
            </button>
          </div>
        ))}
      </div>

      <div>
        <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">
          {t("places.media", "Photos / video (optional, 10MB combined max)")}
        </label>

        {existingImages.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {existingImages.map((url) => (
              <div key={url} className="relative">
                <img src={url} alt="" className="h-16 w-16 rounded-lg object-cover" />
                <button
                  type="button"
                  onClick={() => removeExistingImage(url)}
                  className="absolute -top-1.5 -right-1.5 rounded-full bg-black/70 text-white p-0.5"
                >
                  <X size={11} />
                </button>
              </div>
            ))}
          </div>
        )}
        {existingVideo && <p className="text-xs text-neutral-500 mb-2">{t("places.hasExistingVideo", "Video attached")}</p>}

        <label className="flex items-center gap-2 rounded-lg border border-dashed border-neutral-300 dark:border-neutral-700 px-3 py-2 text-sm cursor-pointer text-neutral-500 hover:border-teal-500">
          <Upload size={15} />
          {newFiles.length > 0 ? `${newFiles.length} file(s) selected` : t("places.chooseFiles", "Choose photos or a video")}
          <input type="file" accept="image/*,video/*" multiple onChange={handleFileChange} className="hidden" />
        </label>
        {newFiles.length > 0 && (
          <p className={`mt-1 text-xs ${overSizeLimit ? "text-red-500" : "text-neutral-400"}`}>
            {(newFilesSize / 1_000_000).toFixed(1)}MB / 10MB {overSizeLimit && `— ${t("places.overSizeLimit", "over the limit, remove a file")}`}
          </p>
        )}
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      <div className="flex gap-2 pt-2">
        <button
          type="submit"
          disabled={busy || overSizeLimit}
          className="inline-flex items-center gap-2 rounded-lg bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white px-4 py-2 text-sm font-medium"
        >
          {busy && <Loader2 size={14} className="animate-spin" />}
          {status === "uploading" ? t("places.uploading", "Uploading…") : isEdit ? t("places.saveChanges", "Save changes") : t("places.submit", "Submit place")}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} className="rounded-lg bg-neutral-100 dark:bg-neutral-800 px-4 py-2 text-sm font-medium">
            {t("places.cancel", "Cancel")}
          </button>
        )}
      </div>
    </form>
  );
}
