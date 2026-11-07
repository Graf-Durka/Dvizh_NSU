from django import forms
from .models import Application


class ApplyForm(forms.ModelForm):
    comment = forms.CharField(
        label='Короткий комментарий о себе и мотивации',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Расскажите в двух словах о своём интересе, релевантном опыте или готовности помочь...'
        }),
        max_length=500,
        required=True
    )

    class Meta:
        model = Application
        fields = ['comment']
