from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from .forms import LoginUserForm, RegisterUserForm, ProfileUserForm, UserPasswordChangeForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.contrib.auth.mixins import LoginRequiredMixin

# Create your views here.

def login_user(request):
    if request.method == 'POST':
        form = LoginUserForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(request, username=cd['username'], password=cd['password'])
            if user and user.is_active:
                login(request, user)
                return redirect('main:index')
    else:
        form = LoginUserForm()
    return render(request, 'users/login.html', {'form' : form})

def logout_user(request):
    logout(request)
    return redirect('users:login')

def register_user(request):
    if request.method == 'POST':
        form = RegisterUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
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

class UserPasswordChange(PasswordChangeView, LoginRequiredMixin):
    form_class = UserPasswordChangeForm
    success_url = reverse_lazy('users:password_change_done')
    template_name = 'users/password_change.html'

class UserPasswordChangeDone(PasswordChangeDoneView, LoginRequiredMixin):
    template_name = 'users/password_change_done.html'