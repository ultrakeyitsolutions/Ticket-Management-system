#!/usr/bin/env python
"""
Create sample FAQ data for testing
"""
import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

try:
    from dashboards.models import Faq
    
    # Sample FAQ data
    sample_faqs = [
        {
            'question': 'How do I create a new ticket?',
            'answer': 'To create a new ticket, click on the "New Ticket" button in your dashboard. Fill in the required fields including title, description, priority, and category. You can also attach files if needed. Once submitted, your ticket will be assigned to an available support agent.',
            'category': 'getting-started',
            'order': 1
        },
        {
            'question': 'What are the different ticket priorities?',
            'answer': 'Tickets can have four priority levels: Critical (urgent issues affecting business operations), High (important issues affecting work), Medium (standard issues), and Low (minor issues or improvements). Higher priority tickets are handled first by our support team.',
            'category': 'tickets',
            'order': 2
        },
        {
            'question': 'How can I track my ticket status?',
            'answer': 'You can track your ticket status in real-time from your dashboard. Tickets go through these statuses: Open (newly created), In Progress (being worked on), Resolved (solution provided), and Closed (completed). You\'ll receive notifications when your ticket status changes.',
            'category': 'tickets',
            'order': 3
        },
        {
            'question': 'What payment methods do you accept?',
            'answer': 'We accept all major credit cards (Visa, MasterCard, American Express), PayPal, and bank transfers for annual subscriptions. All payments are processed securely through our payment partners.',
            'category': 'billing',
            'order': 4
        },
        {
            'question': 'How do I update my account information?',
            'answer': 'Navigate to the Profile section in your dashboard to update your personal information, email address, phone number, and password. You can also manage your notification preferences and security settings from the Settings page.',
            'category': 'account',
            'order': 5
        },
        {
            'question': 'I forgot my password. How do I reset it?',
            'answer': 'Click on the "Forgot Password" link on the login page. Enter your registered email address, and we\'ll send you a password reset link. Follow the instructions in the email to create a new password.',
            'category': 'troubleshooting',
            'order': 6
        },
        {
            'question': 'Can I communicate with support agents?',
            'answer': 'Yes! Each ticket has a built-in chat system where you can communicate directly with the assigned support agent. You can ask questions, provide additional information, and receive real-time updates on your ticket.',
            'category': 'tickets',
            'order': 7
        },
        {
            'question': 'How do I download my invoices?',
            'answer': 'Go to the Billing section in your dashboard to view and download all your invoices. Invoices are available in PDF format and include detailed breakdown of charges and payment history.',
            'category': 'billing',
            'order': 8
        },
        {
            'question': 'Is my data secure?',
            'answer': 'Absolutely! We use industry-standard encryption and security measures to protect your data. All data transmissions are encrypted using SSL/TLS, and we comply with data protection regulations including GDPR.',
            'category': 'account',
            'order': 9
        },
        {
            'question': 'How do I enable two-factor authentication?',
            'answer': 'Go to Settings > Security in your dashboard and click on "Enable 2FA". Follow the setup instructions to configure an authenticator app on your phone. This adds an extra layer of security to your account.',
            'category': 'account',
            'order': 10
        },
        {
            'question': 'What are your business hours?',
            'answer': 'Our support team is available 24/7 for critical issues. Standard support is available Monday through Friday, 9 AM to 5 PM EST. Response times may vary based on ticket priority and current workload.',
            'category': 'general',
            'order': 11
        },
        {
            'question': 'Can I upgrade or downgrade my plan?',
            'answer': 'Yes, you can change your subscription plan at any time. Go to the Billing section and select "Change Plan". Upgrades take effect immediately, while downgrades take effect at the next billing cycle.',
            'category': 'billing',
            'order': 12
        }
    ]
    
    # Clear existing FAQs
    Faq.objects.all().delete()
    print("Cleared existing FAQs")
    
    # Create sample FAQs
    created_count = 0
    for faq_data in sample_faqs:
        faq = Faq.objects.create(
            question=faq_data['question'],
            answer=faq_data['answer'],
            category=faq_data['category'],
            order=faq_data['order'],
            is_published=True
        )
        created_count += 1
        print(f"Created FAQ: {faq.question[:50]}...")
    
    print(f"\nSuccessfully created {created_count} sample FAQs!")
    print(f"Total FAQs in database: {Faq.objects.count()}")
    
except Exception as e:
    print(f"Error creating sample FAQs: {e}")
    
    # Try alternative import
    try:
        from apps.dashboards.models import Faq
        
        # Sample FAQ data (same as above)
        sample_faqs = [
            {
                'question': 'How do I create a new ticket?',
                'answer': 'To create a new ticket, click on the "New Ticket" button in your dashboard. Fill in the required fields including title, description, priority, and category. You can also attach files if needed. Once submitted, your ticket will be assigned to an available support agent.',
                'category': 'getting-started',
                'order': 1
            },
            {
                'question': 'What are the different ticket priorities?',
                'answer': 'Tickets can have four priority levels: Critical (urgent issues affecting business operations), High (important issues affecting work), Medium (standard issues), and Low (minor issues or improvements). Higher priority tickets are handled first by our support team.',
                'category': 'tickets',
                'order': 2
            },
            {
                'question': 'How can I track my ticket status?',
                'answer': 'You can track your ticket status in real-time from your dashboard. Tickets go through these statuses: Open (newly created), In Progress (being worked on), Resolved (solution provided), and Closed (completed). You\'ll receive notifications when your ticket status changes.',
                'category': 'tickets',
                'order': 3
            },
            {
                'question': 'What payment methods do you accept?',
                'answer': 'We accept all major credit cards (Visa, MasterCard, American Express), PayPal, and bank transfers for annual subscriptions. All payments are processed securely through our payment partners.',
                'category': 'billing',
                'order': 4
            },
            {
                'question': 'How do I update my account information?',
                'answer': 'Navigate to the Profile section in your dashboard to update your personal information, email address, phone number, and password. You can also manage your notification preferences and security settings from the Settings page.',
                'category': 'account',
                'order': 5
            },
            {
                'question': 'I forgot my password. How do I reset it?',
                'answer': 'Click on the "Forgot Password" link on the login page. Enter your registered email address, and we\'ll send you a password reset link. Follow the instructions in the email to create a new password.',
                'category': 'troubleshooting',
                'order': 6
            }
        ]
        
        # Clear existing FAQs
        Faq.objects.all().delete()
        print("Cleared existing FAQs")
        
        # Create sample FAQs
        created_count = 0
        for faq_data in sample_faqs:
            faq = Faq.objects.create(
                question=faq_data['question'],
                answer=faq_data['answer'],
                category=faq_data['category'],
                order=faq_data['order'],
                is_published=True
            )
            created_count += 1
            print(f"Created FAQ: {faq.question[:50]}...")
        
        print(f"\nSuccessfully created {created_count} sample FAQs!")
        print(f"Total FAQs in database: {Faq.objects.count()}")
        
    except Exception as e2:
        print(f"Alternative import also failed: {e2}")
