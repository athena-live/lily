from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme

# Create your views here.


def index(request):
    return render(request, "home/index.html")


def root_domain(request):
    host = request.get_host().split(":")[0].strip(".")
    parts = [p for p in host.split(".") if p]
    if len(parts) < 2:
        target_host = host
    else:
        target_host = ".".join(parts[-2:])

    target_url = f"{request.scheme}://{target_host}"
    if not url_has_allowed_host_and_scheme(target_url, allowed_hosts={target_host}):
        return HttpResponseRedirect("/")
    return HttpResponseRedirect(target_url)
