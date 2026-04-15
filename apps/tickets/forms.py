from django import forms
from .models import Ticket
from django.contrib.auth import get_user_model

User = get_user_model()

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'priority', 'category']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 100}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Override the category field to accept any text (not just predefined choices)
        self.fields['category'] = forms.CharField(
            widget=forms.TextInput(
                attrs={'class': 'form-control', 'id': 'id_category', 'placeholder': 'Select category or type custom...'}
            ),
            required=True,
            label='Category'
        )
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not title:
            raise forms.ValidationError("Ticket title is required.")
        if len(title) < 5:
            raise forms.ValidationError("Ticket title must be at least 5 characters.")
        if len(title) > 100:
            raise forms.ValidationError("Ticket title must be less than 100 characters.")
        return title
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description:
            raise forms.ValidationError("Description is required.")
        if len(description) < 10:
            raise forms.ValidationError("Description must be at least 10 characters.")
        return description
    
    def clean_category(self):
        category = self.cleaned_data.get('category')
        if not category or not category.strip():
            raise forms.ValidationError("Category is required.")
        return category

class AdminTicketForm(forms.ModelForm):
    """Form for admin ticket editing that includes assignment field"""
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'priority', 'category', 'assigned_to']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 100}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(
                choices=Ticket.CATEGORY_CHOICES,
                attrs={'class': 'form-select', 'id': 'ticket_category'}
            ),
            'assigned_to': forms.Select(attrs={'class': 'form-select', 'id': 'assigned_to'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get the ticket instance if editing
        ticket_instance = kwargs.get('instance')
        
        # Initialize with all agents first
        agents_queryset = User.objects.filter(
            userprofile__role__name='Agent', 
            is_active=True
        ).select_related('userprofile').order_by('username')
        
        self.fields['assigned_to'].queryset = agents_queryset
        self.fields['assigned_to'].required = False
        self.fields['assigned_to'].empty_label = "Unassigned"
        
        # Customize the label to include department information
        self.fields['assigned_to'].label_from_instance = lambda obj: f"{obj.username} ({obj.userprofile.department or 'No Department'})"
        
        # If we have a ticket instance, filter agents by department based on ticket category
        if ticket_instance and ticket_instance.category:
            self._filter_agents_by_category(ticket_instance.category)
    
    def _filter_agents_by_category(self, category):
        """Filter agents based on ticket category/department mapping"""
        # Map ticket categories to departments
        category_department_mapping = {
            'Technical': 'Technical Support',
            'Billing': 'Billing Support', 
            'General': 'General Support',
            'Support': 'Support',
            'Others': 'General Support'
        }
        
        # Get the department for this category
        department = category_department_mapping.get(category, 'General Support')
        
        # Filter agents by department
        department_agents = User.objects.filter(
            userprofile__role__name='Agent',
            userprofile__department=department,
            is_active=True
        ).order_by('username')
        
        # Update the queryset
        self.fields['assigned_to'].queryset = department_agents