from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .models import IngestedContent


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
