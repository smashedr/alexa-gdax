import logging
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

logger = logging.getLogger('app')


@require_http_methods(["GET"])
def home_view(request):
    """
    # View  /
    """
    log_req(request)
    return render(request, 'home.html')


def log_req(request):
    """
    DEBUGGING ONLY
    """
    data = ''
    if request.method == 'GET':
        data = 'GET: '
        for key, value in request.GET.items():
            data += '"%s": "%s", ' % (key, value)
    if request.method == 'POST':
        data = 'POST: '
        for key, value in request.POST.items():
            data += '"%s": "%s", ' % (key, value)
    if data:
        data = data.strip(', ')
        logger.info(data)
        json_string = '{%s}' % data
        return json_string
    else:
        return None
