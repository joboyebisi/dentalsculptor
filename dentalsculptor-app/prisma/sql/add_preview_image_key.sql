-- Card preview PNG storage key (same-origin serve via /api/projects/{id}/preview-image)
ALTER TABLE "DentalModel"
ADD COLUMN IF NOT EXISTS "previewImageKey" TEXT;
