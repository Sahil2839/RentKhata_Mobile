from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser, OfflineTenants, TenantDocument
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm



class CustomUserCreationForm(UserCreationForm):
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        label='Phone Number',
        strip=True
    )
    
    username = forms.CharField(
        max_length=30,
        required=True,
        label="Create Username",
        strip=True
    )       

    class Meta:
        model = CustomUser
        fields = (
            'first_name',
            'last_name',
            'username',
            'phone_number',
            'password1',
            'password2'
        )
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'password1': 'Create Password',
            'password2': 'Confirm Password'
        }

    def clean(self):
        phone_number = self.cleaned_data.get('phone_number')                 

        if phone_number and not phone_number.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        if phone_number and CustomUser.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("Phone number already exists. Please use a different one.")

        return self.cleaned_data


class CustomLogin(AuthenticationForm):
    username = forms.CharField(
        max_length=150,
        required=True,
        label='Username or Phone Number'
    )

    def clean(self):
        username_input = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if not username_input or not password:
            raise forms.ValidationError("Please enter both username/phone and password.")

        # Try to find user by username
        user_obj = CustomUser.objects.filter(username=username_input).first()
        if not user_obj:
            # Try by phone number
            user_obj = CustomUser.objects.filter(phone_number=username_input).first()

        if not user_obj:
            raise forms.ValidationError("Invalid username or phone number.")

        # Authenticate with the actual username
        self.user_cache = authenticate(
            self.request,
            username=user_obj.username,
            password=password
        )

        if self.user_cache is None:
            raise forms.ValidationError("Invalid login credentials.")

        return self.cleaned_data

    def get_user(self):
        return self.user_cache



class OfflineTenantForm(forms.ModelForm):
    name = forms.CharField(
        label="Name", 
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        label="Phone Number",
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    property_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    rent = forms.IntegerField(
        required=True, 
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    due_amount = forms.IntegerField(
        required=True, 
        widget=forms.NumberInput(attrs={'class': 'form-control',
                                        'placeholder': 'Enter negative value if advance payment'})
    )
    meter_rate = forms.IntegerField(
        required=True, 
        initial=10,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    starting_meter_reading = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        required=True, 
        widget=forms.DateInput(attrs={'type': 'date','required': True, 'class': 'form-control'})
    )
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control notes-input', 'rows': 2}),
        label="Notes"
    )

    class Meta:
        model = OfflineTenants
        fields = ['name', 'phone_number', 'property_name', 'rent', 'due_amount',
                  'meter_rate', 'starting_meter_reading', 'start_date', 'note']



class InviteTenantForm(forms.Form):
    username_or_phone = forms.CharField(
        label="Tenant Username or Phone Number", 
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    property_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    rent = forms.IntegerField(
        required=True, 
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    due_amount = forms.IntegerField(
        required=True, 
        widget=forms.NumberInput(attrs={'class': 'form-control',
        'placeholder': 'Enter negative value if advance payment'})
    )
    meter_rate = forms.IntegerField(
        required=True, 
        initial=10,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    starting_meter_reading = forms.IntegerField(
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        required=True, 
        widget=forms.DateInput(attrs={'type': 'date','required': True, 'class': 'form-control'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control notes-input', 'rows': 2}),
        label="Notes"
    )


class OnlineTenantForm(forms.ModelForm):
    class Meta:
        model = OfflineTenants
        fields = [ 'property_name', 'rent', 'due_amount','meter_rate', 'starting_meter_reading', 'start_date', 'note']
        widgets = {
            'property_name': forms.TextInput(attrs={'class': 'form-control'}),
            'rent': forms.NumberInput(attrs={'class': 'form-control'}),
            'due_amount': forms.NumberInput(attrs={'class':'form-control', 'placeholder': 'Enter negative value if advance payment'}),
            'meter_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'starting_meter_reading': forms.NumberInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type':'date','required': True, 'class':'form-control'}),
            'note': forms.Textarea(attrs={'class':'form-control notes-input','rows':2})
        }


class TenantDocumentForm(forms.ModelForm):
    class Meta:
        model = TenantDocument
        fields = ['document_name', 'file']
        widgets = {
            'document_name': forms.TextInput(attrs={'class':'form-control', 'placeholder':'Document Name'}),
            'file': forms.FileInput(attrs={'class':'form-control'})
        }


User = get_user_model()

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'username', 'phone_number', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }
