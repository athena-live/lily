import json
import os

from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_http_methods

from content_ingestion.models import IngestedContent

from .engine import analyze_content
from .finetune import (
    build_report_training_jsonl,
    build_training_jsonl,
    create_fine_tune_job,
    get_fine_tune_job,
    upload_training_file,
)
from .models import ContentCorrection, FineTuneJob, SiteModelConfig, SlopReport, SlopReportCorrection


def _base_queryset(request):
    if getattr(request.user, "is_authenticated", False):
        return IngestedContent.objects.filter(user=request.user)
    return IngestedContent.objects.filter(user__isnull=True)


def _is_admin(user):
    return getattr(user, "is_authenticated", False) and getattr(user, "is_staff", False)


def _get_active_model():
    config = SiteModelConfig.objects.order_by("-updated_at").first()
    if config and config.current_model:
        return config.current_model
    return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


@require_http_methods(["POST"])
def analyze(request, content_id):
    item = _base_queryset(request).filter(id=content_id).first()
    if not item:
        raise Http404("Content not found.")

    active_model = _get_active_model()
    report = analyze_content(item.raw_text, model_override=active_model)
    report["model_used"] = active_model
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


@user_passes_test(_is_admin)
@require_http_methods(["GET"])
def admin_ingestions(request):
    items = (
        IngestedContent.objects.select_related("user")
        .prefetch_related("corrections", "slop_reports")
        .order_by("-created_at")
    )
    return render(request, "slop_detection/admin_ingestions.html", {"items": items})


@user_passes_test(_is_admin)
@require_http_methods(["GET", "POST"])
def admin_correction(request, content_id):
    item = IngestedContent.objects.select_related("user").filter(id=content_id).first()
    if not item:
        raise Http404("Content not found.")

    if request.method == "POST":
        corrected_text = (request.POST.get("corrected_text") or "").strip()
        notes = (request.POST.get("notes") or "").strip()
        if corrected_text:
            ContentCorrection.objects.filter(content=item, is_current=True).update(is_current=False)
            ContentCorrection.objects.create(
                content=item,
                editor=request.user,
                original_text=item.raw_text,
                corrected_text=corrected_text,
                notes=notes,
                is_current=True,
            )

    corrections = item.corrections.order_by("-created_at")
    current = corrections.filter(is_current=True).first()
    return render(
        request,
        "slop_detection/admin_correction.html",
        {
            "item": item,
            "current_correction": current,
            "corrections": corrections,
        },
    )


@user_passes_test(_is_admin)
@require_http_methods(["GET", "POST"])
def admin_report_correction(request, report_id):
    report = SlopReport.objects.select_related("content", "user").filter(id=report_id).first()
    if not report:
        raise Http404("Report not found.")

    if request.method == "POST":
        corrected_text = (request.POST.get("corrected_report") or "").strip()
        notes = (request.POST.get("notes") or "").strip()
        if corrected_text:
            try:
                corrected_report = json.loads(corrected_text)
            except json.JSONDecodeError:
                corrected_report = None
            if corrected_report is not None:
                SlopReportCorrection.objects.filter(report=report, is_current=True).update(
                    is_current=False
                )
                SlopReportCorrection.objects.create(
                    report=report,
                    editor=request.user,
                    original_report=report.report,
                    corrected_report=corrected_report,
                    notes=notes,
                    is_current=True,
                )

    corrections = report.corrections.order_by("-created_at")
    current = corrections.filter(is_current=True).first()
    return render(
        request,
        "slop_detection/admin_report_correction.html",
        {
            "report": report,
            "current_correction": current,
            "corrections": corrections,
        },
    )


@user_passes_test(_is_admin)
@require_http_methods(["GET", "POST"])
def admin_training(request):
    message = ""
    error = ""
    jobs = FineTuneJob.objects.order_by("-created_at")
    config = SiteModelConfig.objects.order_by("-updated_at").first()
    active_model = config.current_model if config else os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    if request.method == "POST":
        action = request.POST.get("action")
        base_model = (request.POST.get("base_model") or "").strip() or active_model
        if action == "refresh":
            for job in jobs:
                try:
                    data = get_fine_tune_job(job.job_id)
                except Exception:
                    continue
                job.status = data.get("status", job.status)
                job.fine_tuned_model = data.get("fine_tuned_model") or job.fine_tuned_model
                job.metadata = data
                job.save(update_fields=["status", "fine_tuned_model", "metadata"])
            message = "Jobs refreshed."
        else:
            corrections = ContentCorrection.objects.filter(is_current=True)
            report_corrections = SlopReportCorrection.objects.filter(is_current=True).select_related(
                "report", "report__content"
            )
            if action == "train_report" or action == "export_report":
                jsonl_text = build_report_training_jsonl(report_corrections)
            else:
                jsonl_text = build_training_jsonl(corrections)
            if not jsonl_text.strip():
                error = "No corrected samples available."
            elif action == "export" or action == "export_report":
                response = HttpResponse(jsonl_text, content_type="application/jsonl")
                filename = (
                    "slop_report_corrections.jsonl"
                    if action == "export_report"
                    else "slop_corrections.jsonl"
                )
                response["Content-Disposition"] = f"attachment; filename={filename}"
                return response
            elif action == "train" or action == "train_report":
                try:
                    file_data = upload_training_file(jsonl_text)
                    training_file_id = file_data.get("id", "")
                    job_data = create_fine_tune_job(training_file_id, base_model)
                    FineTuneJob.objects.create(
                        created_by=request.user,
                        training_file_id=training_file_id,
                        job_id=job_data.get("id", ""),
                        base_model=base_model,
                        status=job_data.get("status", "queued"),
                        fine_tuned_model=job_data.get("fine_tuned_model", ""),
                        metadata=job_data,
                    )
                    message = "Fine-tune job created."
                except Exception as exc:
                    error = f"Failed to create fine-tune job: {exc}"

    jobs = FineTuneJob.objects.order_by("-created_at")
    return render(
        request,
        "slop_detection/admin_training.html",
        {
            "jobs": jobs,
            "message": message,
            "error": error,
            "active_model": active_model,
        },
    )


@user_passes_test(_is_admin)
@require_http_methods(["POST"])
def admin_set_model(request):
    model_name = (request.POST.get("model_name") or "").strip()
    if not model_name:
        return HttpResponse("Model name required", status=400)
    SiteModelConfig.objects.create(current_model=model_name, updated_by=request.user)
    return HttpResponseRedirect(reverse("slop_detection:admin_training"))
