from allauth.account.forms import SignupForm
from django import forms

class CustomSignupForm(SignupForm):
    location = forms.CharField(max_length=100, required=False)

    def save(self, request):
        user = super().save(request)
        profile = user.userprofile
        profile.location = self.cleaned_data['location']
        profile.save()
        return user
