from django import forms
from captcha.fields import CaptchaField

class ContactForm(forms.Form):
    name = forms.CharField(label='Name', max_length=255)
    email = forms.EmailField(label='E-mail')
    content = forms.CharField(label='Message', widget=forms.Textarea())
    captcha = CaptchaField()