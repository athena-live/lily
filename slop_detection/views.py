from django.http import Http404, JsonResponse
from django.shortcuts import render
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
    saved_report = SlopReport.objects.create(
        user=request.user if getattr(request.user, "is_authenticated", False) else None,
        content=item,
        report=report,
    )
    wants_json = request.GET.get("format") == "json" or request.headers.get(
        "x-requested-with"
    ) == "XMLHttpRequest"
    if wants_json:
        return JsonResponse(report)
    return render(request, "slop_detection/report_detail.html", {"report": saved_report})


@require_http_methods(["GET"])
def report_detail(request, report_id):
    report = SlopReport.objects.filter(id=report_id).first()
    if not report:
        raise Http404("Report not found.")
    if getattr(request.user, "is_authenticated", False) and report.user != request.user:
        raise Http404("Report not found.")
    if not getattr(request.user, "is_authenticated", False) and report.user is not None:
        raise Http404("Report not found.")
    return render(request, "slop_detection/report_detail.html", {"report": report})


@require_http_methods(["GET"])
def latest_report(request, content_id):
    item = _base_queryset(request).filter(id=content_id).first()
    if not item:
        raise Http404("Content not found.")
    report = item.slop_reports.order_by("-created_at").first()
    if not report:
        raise Http404("Report not found.")
    return render(request, "slop_detection/report_detail.html", {"report": report})

# Create your views here.
