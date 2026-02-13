from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .models import IngestedContent


def _base_queryset(request):
    if getattr(request.user, "is_authenticated", False):
        return IngestedContent.objects.filter(user=request.user)
    return IngestedContent.objects.filter(user__isnull=True)


@require_http_methods(["GET"])
def ingest_list(request):
    items = _base_queryset(request).order_by("-created_at")
    return render(
        request,
        "content_ingestion/list.html",
        {
            "items": items,
            "can_create": True,
        },
    )


@require_http_methods(["GET"])
def ingest_detail(request, content_id):
    item = _base_queryset(request).filter(id=content_id).first()
    if not item:
        raise Http404("Content not found.")
    return render(request, "content_ingestion/detail.html", {"item": item})


@require_http_methods(["GET", "POST"])
def ingest(request):
    context = {
        "name": "",
        "content": "",
        "error": "",
        "saved": request.GET.get("saved") == "1",
    }

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        content = (request.POST.get("content") or "").strip()

        context["name"] = name
        context["content"] = content

        if not name:
            context["error"] = "Please give this content a name."
        elif not content:
            context["error"] = "Please paste some content to ingest."
        else:
            IngestedContent.objects.create(
                user=request.user if getattr(request.user, "is_authenticated", False) else None,
                name=name,
                raw_text=content,
            )
            return HttpResponseRedirect(f"{reverse('content_ingestion:ingest')}?saved=1")

    return render(request, "content_ingestion/ingest.html", context)


@require_http_methods(["GET", "POST"])
def ingest_edit(request, content_id):
    item = _base_queryset(request).filter(id=content_id).first()
    if not item:
        raise Http404("Content not found.")

    context = {
        "name": item.name,
        "content": item.raw_text,
        "error": "",
        "item": item,
    }

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        content = (request.POST.get("content") or "").strip()

        context["name"] = name
        context["content"] = content

        if not name:
            context["error"] = "Please give this content a name."
        elif not content:
            context["error"] = "Please paste some content to ingest."
        else:
            item.name = name
            item.raw_text = content
            item.save(update_fields=["name", "raw_text"])
            return HttpResponseRedirect(reverse("content_ingestion:detail", args=[item.id]))

    return render(request, "content_ingestion/edit.html", context)


@require_http_methods(["POST"])
def ingest_delete(request, content_id):
    item = _base_queryset(request).filter(id=content_id).first()
    if not item:
        raise Http404("Content not found.")
    item.delete()
    return HttpResponseRedirect(reverse("content_ingestion:list"))
