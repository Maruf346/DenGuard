from allauth.account.forms import SignupForm
from django import forms
from django.contrib.auth.models import User
from users.models import UserProfile  # if you want to include extra fields


class CustomSignupForm(SignupForm):
    location = forms.CharField(max_length=100, required=False)

    def save(self, request):
        user = super().save(request)
        profile = user.userprofile
        profile.location = self.cleaned_data['location']
        profile.save()
        return user

class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data