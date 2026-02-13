from django.http import Http404, JsonResponse
from django.views.decorators.http import require_http_methods

from content_ingestion.models import IngestedContent

from .engine import analyze_content
from .models import SlopReport


def _base_queryset(request):
    if getattr(request.user, "is_authenticated", False):
        return IngestedContent.objects.filter(user=request.user)
    return IngestedContent.objects.filter(user__isnull=True)


@require_http_methods(["POST"])
def analyze(request, content_id):
    item = _base_queryset(request).filter(id=content_id).first()
    if not item:
        raise Http404("Content not found.")

    report = analyze_content(item.raw_text)
    SlopReport.objects.create(
        user=request.user if getattr(request.user, "is_authenticated", False) else None,
        content=item,
        report=report,
    )
    return JsonResponse(report)

# Create your views here.
