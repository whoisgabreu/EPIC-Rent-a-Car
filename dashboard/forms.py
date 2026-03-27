from django import forms
from django.contrib.auth.models import User
from .models import Investor, Vehicle


# ─── User Forms ───────────────────────────────────────────────────────────────

class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={'placeholder': 'Mínimo 8 caracteres'}),
        min_length=8
    )
    confirm_password = forms.CharField(
        label="Confirmar Senha",
        widget=forms.PasswordInput(attrs={'placeholder': 'Repita a senha'})
    )
    is_staff = forms.BooleanField(label="Perfil Administrador", required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'is_staff']
        labels = {'username': 'Nome de usuário', 'email': 'E-mail'}

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get('password')
        cpw = cleaned.get('confirm_password')
        if pw and cpw and pw != cpw:
            self.add_error('confirm_password', 'As senhas não coincidem.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    new_password = forms.CharField(
        label="Nova Senha (opcional)",
        widget=forms.PasswordInput(attrs={'placeholder': 'Deixe em branco para manter'}),
        required=False
    )
    is_staff = forms.BooleanField(label="Perfil Administrador", required=False)
    is_active = forms.BooleanField(label="Usuário Ativo", required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'is_staff', 'is_active']
        labels = {'username': 'Nome de usuário', 'email': 'E-mail'}

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
        label="Usuário vinculado",
        required=False,
        empty_label="— Nenhum usuário —"
    )
    STATUS_CHOICES = [('Active', 'Ativo'), ('Inactive', 'Inativo')]
    status = forms.ChoiceField(choices=STATUS_CHOICES, label="Status")

    class Meta:
        model = Investor
        fields = ['name', 'status', 'user']
        labels = {
            'name': 'Nome do Investidor',
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
    STATUS_CHOICES = [('Active', 'Ativo'), ('Inactive', 'Inativo'), ('Maintenance', 'Manutenção')]
    status = forms.ChoiceField(choices=STATUS_CHOICES, label="Status")

    class Meta:
        model = Vehicle
        fields = ['vin', 'plate', 'year_make_model', 'investor', 'status', 'acquisition_date']
        labels = {
            'vin': 'VIN',
            'plate': 'Placa',
            'year_make_model': 'Ano / Marca / Modelo',
            'investor': 'Investidor',
            'acquisition_date': 'Data de Aquisição',
        }
        widgets = {
            'acquisition_date': forms.DateInput(attrs={'type': 'date'}),
        }
