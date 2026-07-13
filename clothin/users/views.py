from datetime import timedelta
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from .forms import LoginUserForm, RegisterUserForm, ProfileUserForm, UserPasswordChangeForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from axes.helpers import get_client_username, get_client_parameters, get_cool_off
from axes.models import AccessAttempt

# Create your views here.

def login_user(request):
    if request.method == 'POST':
        form = LoginUserForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(request, username=cd['username'], password=cd['password'])
            if user and user.is_active:
                login(request, user)
                next_url = request.POST.get('next') or request.GET.get('next')
                if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                    return redirect(next_url)
                return redirect('main:index')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginUserForm()
    return render(request, 'users/login.html', {'form' : form})

def axes_lockout_response(request, response=None, credentials=None):
    """AXES_LOCKOUT_CALLABLE: renders lockout.html with the real remaining cool-off time,
    read from AccessAttempt's stored expiration, so it doesn't reset to the full duration
    on page reload."""
    username = get_client_username(request, credentials)
    cool_off = get_cool_off(request)
    remaining = cool_off

    if cool_off is not None:
        filter_kwargs_list = get_client_parameters(
            username,
            getattr(request, 'axes_ip_address', None),
            getattr(request, 'axes_user_agent', None),
            request,
            credentials,
        )
        latest_expiry = None
        for filter_kwargs in filter_kwargs_list:
            expiry = (
                AccessAttempt.objects.filter(expiration__isnull=False, **filter_kwargs)
                .order_by('-expiration__expires_at')
                .values_list('expiration__expires_at', flat=True)
                .first()
            )
            if expiry and (latest_expiry is None or expiry > latest_expiry):
                latest_expiry = expiry

        if latest_expiry is not None:
            remaining = max(latest_expiry - timezone.now(), timedelta(seconds=0))

    context = {'cooloff_timedelta': remaining}
    return render(request, 'lockout.html', context, status=429)

@require_POST
def logout_user(request):
    logout(request)
    return redirect('users:login')

def register_user(request):
    if request.method == 'POST':
        form = RegisterUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            try:
                with transaction.atomic():
                    user.save()
            except IntegrityError:
                form.add_error('email', 'This email already exists')
            else:
                return render(request, 'users/register_done.html')
    else:
        form = RegisterUserForm()

    return render(request, 'users/register.html', {'form' : form})

@login_required
def profile_user(request):
    if request.method == "POST":
        form = ProfileUserForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect(request.path)
    else:
        form = ProfileUserForm(instance=request.user)

    return render(request, 'users/profile.html', {'form': form})

class UserPasswordChange(LoginRequiredMixin, PasswordChangeView):
    form_class = UserPasswordChangeForm
    success_url = reverse_lazy('users:password_change_done')
    template_name = 'users/password_change.html'

class UserPasswordChangeDone(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = 'users/password_change_done.html'
