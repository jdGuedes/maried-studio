from pathlib import Path

from django.http import FileResponse, Http404
from django.urls import reverse


IMAGE_EXTENSIONS_BY_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def build_private_media_url(
    request,
    view_name,
    *,
    pk,
):
    url = reverse(
        view_name,
        kwargs={
            "pk": pk,
        },
    )

    if request:
        return request.build_absolute_uri(
            url
        )

    return url


def build_private_image_response(
    file_field,
    *,
    mime_type,
    filename_prefix,
):
    if not file_field:
        raise Http404(
            "Arquivo não encontrado."
        )

    content_type = (
        mime_type
        if mime_type in IMAGE_EXTENSIONS_BY_MIME
        else "application/octet-stream"
    )

    extension = (
        IMAGE_EXTENSIONS_BY_MIME.get(
            content_type
        )
        or Path(file_field.name).suffix.lower()
        or ".bin"
    )

    if extension not in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }:
        extension = ".bin"

    try:
        opened_file = file_field.open(
            "rb"
        )

    except Exception as exc:
        raise Http404(
            "Arquivo não encontrado."
        ) from exc

    response = FileResponse(
        opened_file,
        as_attachment=True,
        filename=(
            f"{filename_prefix}"
            f"{extension}"
        ),
        content_type=content_type,
    )

    response[
        "Cache-Control"
    ] = "private, no-store"

    return response
