from django import forms

PRODUCT_QUANTITY_CHOICES = [(i, str(i)) for i in range(1, 11)]

class CartAddProductForm(forms.Form):
    action = forms.ChoiceField(
        choices = [('increment', 'Increment'), ('decrement', 'Decrement')],
        widget=forms.HiddenInput
    )

class CartUpdateForm(forms.Form):
    quantity = forms.TypedChoiceField(
        choices=PRODUCT_QUANTITY_CHOICES,
        coerce=int,
        initial=1
    )

