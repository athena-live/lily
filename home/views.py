from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.decorators import login_required

# Create your views here.


def index(request):
    return render(request, "home/index.html")


@login_required
def profile(request):
    return render(request, "home/profile.html")


def root_domain(request):
    host = request.get_host().split(":")[0].strip(".")
    parts = [p for p in host.split(".") if p]
    if len(parts) < 2:
        target_host = host
    else:
        second_level_tlds = {
            "ac",
            "co",
            "com",
            "edu",
            "gov",
            "net",
            "org",
        }
        if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in second_level_tlds:
            target_host = ".".join(parts[-3:])
        else:
            target_host = ".".join(parts[-2:])

    target_url = f"{request.scheme}://{target_host}"
    if not url_has_allowed_host_and_scheme(target_url, allowed_hosts={target_host}):
        return HttpResponseRedirect("/")
    return HttpResponseRedirect(target_url)
