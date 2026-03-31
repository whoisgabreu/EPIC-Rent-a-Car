from django import forms
from django.contrib.auth.models import User
from .models import Investor, Vehicle


# ─── User Forms ───────────────────────────────────────────────────────────────

class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Minimum 8 characters'}),
        min_length=8
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Repeat the password'})
    )
    is_staff = forms.BooleanField(label="Administrator Profile", required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'is_staff']
        labels = {'username': 'Username', 'email': 'Email'}

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        cpw = cleaned.get('confirm_password')
        if pw and cpw and pw != cpw:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    new_password = forms.CharField(
        label="New Password (optional)",
        widget=forms.PasswordInput(attrs={'placeholder': 'Leave blank to keep current'}),
        required=False
    )
    is_staff = forms.BooleanField(label="Administrator Profile", required=False)
    is_active = forms.BooleanField(label="Active User", required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'is_staff', 'is_active']
        labels = {'username': 'Username', 'email': 'Email'}

    def save(self, commit=True):
        user = super().save(commit=False)
        pw = self.cleaned_data.get('new_password')
        if pw:
            user.set_password(pw)
        if commit:
            user.save()
        return user


# ─── Investor Forms ────────────────────────────────────────────────────────────

class InvestorForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(investor_profile__isnull=True) | User.objects.none(),
        label="Linked User",
        required=False,
        empty_label="— No user —"
    )
    STATUS_CHOICES = [('Active', 'Active'), ('Inactive', 'Inactive')]
    status = forms.ChoiceField(choices=STATUS_CHOICES, label="Status")

    class Meta:
        model = Investor
        fields = ['name', 'status', 'user']
        labels = {
            'name': 'Investor Name',
        }


    def __init__(self, *args, **kwargs):
        # Accept the current investor instance so we include its own user in the queryset
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance and instance.user:
            # Allow the investor's own user and users without a profile
            self.fields['user'].queryset = (
                User.objects.filter(investor_profile__isnull=True) |
                User.objects.filter(pk=instance.user.pk)
            )
        else:
            self.fields['user'].queryset = User.objects.filter(investor_profile__isnull=True)


# ─── Vehicle Forms ─────────────────────────────────────────────────────────────

class VehicleForm(forms.ModelForm):
    STATUS_CHOICES = [('Active', 'Active'), ('Inactive', 'Inactive'), ('Maintenance', 'Maintenance')]
    status = forms.ChoiceField(choices=STATUS_CHOICES, label="Status")

    class Meta:
        model = Vehicle
        fields = ['vin', 'plate', 'year_make_model', 'investor', 'status', 'acquisition_date']
        labels = {
            'vin': 'VIN',
            'plate': 'License Plate',
            'year_make_model': 'Year / Make / Model',
            'investor': 'Investor',
            'acquisition_date': 'Acquisition Date',
        }
        widgets = {
            'acquisition_date': forms.DateInput(attrs={'type': 'date'}),
        }
